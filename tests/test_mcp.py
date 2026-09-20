"""Tests for the Streamable HTTP MCP host and service layer."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from mcp.types import TextContent

from backend.mcp import service
from backend.mcp.host import tool_result_text
from backend.mcp.models import MCPService, MCPServerConfig, MCPTool


def _write_test_service(tmp_path, monkeypatch) -> str:
    monkeypatch.setattr(service, "MCP_CONFIGS_DIR", tmp_path)
    stored = service.save_service(
        MCPService(
            name="Test Service",
            server=MCPServerConfig(url="https://mcp.example.test/mcp"),
        )
    )
    return stored["id"]


@pytest.mark.asyncio
async def test_discover_tools_uses_initialized_mcp_session(tmp_path, monkeypatch):
    service_id = _write_test_service(tmp_path, monkeypatch)
    calls = []

    async def list_tools():
        calls.append("list_tools")
        return SimpleNamespace(
            tools=[
                SimpleNamespace(
                    name="search",
                    description="Search documents",
                    input_schema={"type": "object", "properties": {}},
                )
            ]
        )

    fake_session = SimpleNamespace(list_tools=list_tools)

    @asynccontextmanager
    async def fake_connect(url, timeout=30):
        calls.append(("connect", url, timeout))
        yield fake_session

    monkeypatch.setattr(service, "connect_mcp_session", fake_connect)

    tools = await service.discover_tools(service_id)

    assert [(tool.name, tool.description) for tool in tools] == [
        ("search", "Search documents")
    ]
    assert tools[0].input_schema == {"type": "object", "properties": {}}
    assert calls == [
        ("connect", "https://mcp.example.test/mcp", 30),
        "list_tools",
    ]


@pytest.mark.asyncio
async def test_execute_tool_sends_arguments_and_extracts_text(tmp_path, monkeypatch):
    service_id = _write_test_service(tmp_path, monkeypatch)
    calls = []

    async def call_tool(name, arguments):
        calls.append(("call_tool", name, arguments))
        return SimpleNamespace(
            content=[TextContent(type="text", text="hello world")],
            is_error=False,
        )

    fake_session = SimpleNamespace(call_tool=call_tool)

    @asynccontextmanager
    async def fake_connect(url, timeout=30):
        calls.append(("connect", url, timeout))
        yield fake_session

    monkeypatch.setattr(service, "connect_mcp_session", fake_connect)

    result = await service.execute_tool(service_id, "search", {"query": "novel"})

    assert result == "hello world"
    assert calls == [
        ("connect", "https://mcp.example.test/mcp", 60),
        ("call_tool", "search", {"query": "novel"}),
    ]


@pytest.mark.asyncio
async def test_execute_tool_raises_for_mcp_error_result(tmp_path, monkeypatch):
    service_id = _write_test_service(tmp_path, monkeypatch)

    async def call_tool(name, arguments):
        return SimpleNamespace(
            content=[TextContent(type="text", text="not found")],
            is_error=True,
        )

    fake_session = SimpleNamespace(call_tool=call_tool)

    @asynccontextmanager
    async def fake_connect(url, timeout=30):
        yield fake_session

    monkeypatch.setattr(service, "connect_mcp_session", fake_connect)

    with pytest.raises(RuntimeError, match="not found"):
        await service.execute_tool(service_id, "search", {})


@pytest.mark.asyncio
async def test_transient_transport_error_reconnects(monkeypatch):
    monkeypatch.setattr(service, "_BASE_DELAY_SEC", 0)
    monkeypatch.setattr(service, "_MAX_DELAY_SEC", 0)
    attempts = []

    @asynccontextmanager
    async def fake_connect(url, timeout=30):
        attempts.append(url)
        if len(attempts) == 1:
            raise TimeoutError("connection timed out")
        yield SimpleNamespace()

    async def action(session):
        return "ok"

    monkeypatch.setattr(service, "connect_mcp_session", fake_connect)

    result = await service._run_with_reconnect(
        "https://mcp.example.test/mcp", action, "tools/list"
    )

    assert result == "ok"
    assert len(attempts) == 2


@pytest.mark.asyncio
async def test_non_transport_error_is_not_retried(monkeypatch):
    attempts = []

    @asynccontextmanager
    async def fake_connect(url, timeout=30):
        attempts.append(url)
        yield SimpleNamespace()

    async def action(session):
        raise ValueError("invalid arguments")

    monkeypatch.setattr(service, "connect_mcp_session", fake_connect)

    with pytest.raises(ValueError, match="invalid arguments"):
        await service._run_with_reconnect(
            "https://mcp.example.test/mcp", action, "tools/call"
        )

    assert len(attempts) == 1


def test_tool_result_text_formats_text_and_raises_on_error():
    success = SimpleNamespace(
        content=[TextContent(type="text", text="a"), TextContent(type="text", text="b")],
        is_error=False,
    )
    failure = SimpleNamespace(
        content=[TextContent(type="text", text="failed")],
        is_error=True,
    )

    assert tool_result_text(success) == "a\nb"
    with pytest.raises(RuntimeError, match="failed"):
        tool_result_text(failure)
