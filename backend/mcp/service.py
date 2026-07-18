"""MCP service manager with SSE transport.

Connects to MCP servers via HTTP SSE endpoints using the standard MCP
JSON-RPC protocol over JSON-RPC/SSE transport.

Each MCP service has:
- url: SSE endpoint (e.g. http://localhost:3001/mcp)
- Tools are discovered via POST to the endpoint with JSON-RPC body
  {"jsonrpc":"2.0","id":"1","method":"tools/list"}
- Tools are executed via POST with
  {"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"...","arguments":{...}}}
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

import httpx
import yaml

from backend.config import DATA_DIR
from backend.mcp.models import MCPService, MCPTool

logger = logging.getLogger(__name__)

MCP_CONFIGS_DIR = DATA_DIR / "mcp_configs"
_MCP_REQUEST_TIMEOUT = 30


def _ensure_config_dir():
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


# ── SSE Transport ────────────────────────────────────────────────


async def _json_rpc_call(
    url: str,
    method: str,
    params: dict[str, Any] | None = None,
    timeout: int = _MCP_REQUEST_TIMEOUT,
) -> dict[str, Any]:
    """Make a JSON-RPC call to an MCP SSE endpoint via HTTP POST.

    The MCP SSE transport uses a regular HTTP POST endpoint for
    sending JSON-RPC requests. The endpoint URL is the same as the
    SSE stream URL.
    """
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4())[:8],
        "method": method,
    }
    if params is not None:
        payload["params"] = params

    logger.debug("JSON-RPC POST %s: %s", url, method)

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    if "error" in data and data["error"] is not None:
        err_msg = data["error"].get("message", str(data["error"]))
        raise RuntimeError(f"MCP server error: {err_msg}")

    return data


async def discover_tools(service_id: str) -> list[MCPTool]:
    """Discover tools from an MCP server via JSON-RPC tools/list."""
    service_data = get_service(service_id)
    if not service_data:
        raise ValueError(f"MCP service {service_id} not found")

    url = service_data.get("server", {}).get("url", "")
    if not url:
        raise ValueError(f"MCP service {service_id} has no URL configured")

    logger.info("Discovering tools from MCP server %s at %s", service_id, url)

    data = await _json_rpc_call(url, "tools/list")
    result = data.get("result", {})
    tools_data = result.get("tools", [])
    tools = [MCPTool(**t) for t in tools_data]
    logger.info("Discovered %d tools from %s", len(tools), url)
    return tools


async def execute_tool(
    service_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    timeout: int = 60,
) -> str:
    """Execute a tool on an MCP server via JSON-RPC tools/call."""
    service_data = get_service(service_id)
    if not service_data:
        raise ValueError(f"MCP service {service_id} not found")

    url = service_data.get("server", {}).get("url", "")
    if not url:
        raise ValueError(f"MCP service {service_id} has no URL configured")

    logger.info("Executing tool %s/%s at %s", service_id, tool_name, url)

    data = await _json_rpc_call(
        url,
        "tools/call",
        params={"name": tool_name, "arguments": arguments},
        timeout=timeout,
    )
    result = data.get("result", {})
    content = result.get("content", [])
    text_parts = []
    for part in content:
        if isinstance(part, dict) and part.get("type") == "text":
            text_parts.append(part.get("text", ""))
        elif isinstance(part, str):
            text_parts.append(part)
    return "\n".join(text_parts)
