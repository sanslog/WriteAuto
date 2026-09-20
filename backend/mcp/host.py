"""MCP host client for the Streamable HTTP transport.

This module owns the MCP SDK client lifecycle. The upper service layer only
deals with configured service IDs and plain text tool results.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import Implementation, TextContent

logger = logging.getLogger(__name__)

CLIENT_INFO = Implementation(name="WriteAuto", version="2.0.0")


@asynccontextmanager
async def connect_mcp_session(
    url: str,
    timeout: int = 30,
) -> AsyncIterator[ClientSession]:
    """Open and initialize a Streamable HTTP MCP session."""
    logger.debug("Connecting MCP host to Streamable HTTP endpoint: %s", url)
    async with streamable_http_client(url) as (read_stream, write_stream, _session_id):
        async with ClientSession(
            read_stream,
            write_stream,
            read_timeout_seconds=timeout,
            client_info=CLIENT_INFO,
        ) as session:
            await session.initialize()
            logger.debug("Initialized MCP session for %s", url)
            yield session


def tool_result_text(result: Any) -> str:
    """Convert an MCP tool result into text understood by the rest of the app."""
    parts: list[str] = []
    for item in result.content:
        if isinstance(item, TextContent):
            parts.append(item.text)
        else:
            parts.append(str(item))

    text = "\n".join(part for part in parts if part)
    if getattr(result, "is_error", False):
        raise RuntimeError(f"MCP tool failed: {text or 'unknown error'}")
    return text
