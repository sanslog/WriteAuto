"""MCP service manager backed by a Streamable HTTP host client.

Configuration files store a Streamable HTTP endpoint URL. Tool discovery and
execution are delegated to the MCP SDK so initialization and session lifecycle
are handled by the official Streamable HTTP client.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable, TypeVar

from mcp import ClientSession
import yaml

from backend.config import DATA_DIR
from backend.mcp.host import connect_mcp_session, tool_result_text
from backend.mcp.models import MCPService, MCPTool

logger = logging.getLogger(__name__)

MCP_CONFIGS_DIR = DATA_DIR / "mcp_configs"
_MCP_REQUEST_TIMEOUT = 30

# Retry only reconnects. A failed session is never reused for another request.
_MAX_RETRIES = 3
_BASE_DELAY_SEC = 1.0
_MAX_DELAY_SEC = 10.0

_T = TypeVar("_T")


def _ensure_config_dir() -> None:
    MCP_CONFIGS_DIR.mkdir(parents=True, exist_ok=True)


def _service_path(service_id: str) -> Path:
    return MCP_CONFIGS_DIR / f"{service_id}.yaml"


# ── Persistence ──────────────────────────────────────────────────


def list_services() -> list[dict[str, Any]]:
    _ensure_config_dir()
    services = []
    for fpath in sorted(MCP_CONFIGS_DIR.glob("*.yaml")):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                data["id"] = fpath.stem
                services.append(data)
        except Exception as exc:
            logger.warning("Failed to load MCP config %s: %s", fpath, exc)
    return services


def get_service(service_id: str) -> dict[str, Any] | None:
    path = _service_path(service_id)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
        data["id"] = path.stem
        return data


def save_service(service: MCPService) -> dict[str, Any]:
    _ensure_config_dir()
    if not service.id:
        service.id = str(uuid.uuid4())[:8]
    path = _service_path(service.id)
    data = service.model_dump()
    data.pop("id", None)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    logger.info("Saved MCP service %s -> %s", service.id, path)
    return get_service(service.id)


def delete_service(service_id: str) -> bool:
    path = _service_path(service_id)
    if not path.exists():
        return False
    path.unlink()
    logger.info("Deleted MCP service %s", service_id)
    return True


def _service_url(service_data: dict[str, Any], service_id: str) -> str:
    url = service_data.get("server", {}).get("url", "")
    if not url:
        logger.warning("MCP service %s has no URL configured", service_id)
        raise ValueError(f"MCP service {service_id} has no URL configured")
    return url


# ── Streamable HTTP calls ────────────────────────────────────────


def _is_retryable(exc: Exception) -> bool:
    """Identify transient transport errors across SDK/AnyIO exception wrappers."""
    if isinstance(exc, ExceptionGroup):
        return any(
            _is_retryable(item)
            for item in exc.exceptions
            if isinstance(item, Exception)
        )
    return isinstance(exc, (TimeoutError, ConnectionError, BrokenPipeError))


async def _run_with_reconnect(
    url: str,
    action: Callable[[ClientSession], Awaitable[_T]],
    description: str,
    timeout: int = _MCP_REQUEST_TIMEOUT,
) -> _T:
    """Run an MCP operation with a fresh Streamable HTTP session per attempt."""
    last_error: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            async with connect_mcp_session(url, timeout=timeout) as session:
                result = await action(session)
            if attempt > 1:
                logger.info(
                    "MCP operation %s on %s succeeded on retry %d",
                    description, url, attempt,
                )
            return result
        except Exception as exc:
            last_error = exc
            logger.warning(
                "MCP operation failed (attempt %d/%d): operation=%s url=%s "
                "error_type=%s detail=%s",
                attempt, _MAX_RETRIES, description, url,
                type(exc).__name__, exc,
            )
            if not _is_retryable(exc):
                logger.info(
                    "MCP operation %s is non-retryable; stopping attempts",
                    description,
                )
                break
            if attempt < _MAX_RETRIES:
                delay = min(_BASE_DELAY_SEC * (2 ** (attempt - 1)), _MAX_DELAY_SEC)
                logger.info(
                    "Retrying MCP operation %s on %s in %.1fs",
                    description, url, delay,
                )
                await asyncio.sleep(delay)

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"MCP operation {description} did not run")


# ── Tool discovery & execution ──────────────────────────────────


async def discover_tools(service_id: str) -> list[MCPTool]:
    """Discover tools from an MCP server via the initialized MCP session."""
    service_data = get_service(service_id)
    if not service_data:
        raise ValueError(f"MCP service {service_id} not found")

    url = _service_url(service_data, service_id)
    logger.info("Discovering tools from MCP server %s at %s", service_id, url)

    async def _discover(session: ClientSession) -> list[MCPTool]:
        result = await session.list_tools()
        return [
            MCPTool(
                name=tool.name,
                description=tool.description or "",
                input_schema=tool.input_schema,
            )
            for tool in result.tools
        ]

    tools = await _run_with_reconnect(url, _discover, "tools/list")
    logger.info("Discovered %d tools from %s", len(tools), url)
    return tools


async def execute_tool(
    service_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    timeout: int = 60,
) -> str:
    """Execute a tool through the configured Streamable HTTP MCP server.

    Args:
        service_id: MCP service identifier.
        tool_name: Name of the tool exposed by the MCP server.
        arguments: Tool arguments dict.
        timeout: Per-request timeout in seconds.

    Returns:
        Tool result text.

    Raises:
        ValueError: If service or URL is not found.
        RuntimeError: If the MCP server returns an error result.
    """
    service_data = get_service(service_id)
    if not service_data:
        raise ValueError(f"MCP service {service_id} not found")

    url = _service_url(service_data, service_id)
    logger.info("Executing tool %s/%s at %s", service_id, tool_name, url)

    async def _call(session: ClientSession) -> str:
        result = await session.call_tool(tool_name, arguments)
        return tool_result_text(result)

    return await _run_with_reconnect(
        url, _call, f"tools/call:{tool_name}", timeout=timeout
    )
