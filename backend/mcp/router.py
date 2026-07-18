"""FastAPI router for MCP service management.

Provides endpoints to:
- List/get/create/update/delete MCP services (YAML-backed)
- Discover tools from an MCP server
- Execute a specific tool
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from backend.mcp.models import MCPService, MCPCreateRequest, MCPUpdateRequest, MCPTool
from backend.mcp.service import (
    list_services,
    get_service,
    save_service,
    delete_service,
    discover_tools,
    execute_tool,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


@router.get("/services")
async def api_list_services():
    """List all registered MCP services."""
    try:
        services = list_services()
        return {"success": True, "data": services}
    except Exception as exc:
        logger.exception("Failed to list MCP services")
        return {"success": False, "error": str(exc)}


@router.get("/services/{service_id}")
async def api_get_service(service_id: str):
    """Get a single MCP service by id."""
    try:
        service = get_service(service_id)
        if not service:
            return {"success": False, "error": "MCP service not found"}
        return {"success": True, "data": service}
    except Exception as exc:
        logger.exception("Failed to get MCP service %s", service_id)
        return {"success": False, "error": str(exc)}


@router.post("/services")
async def api_create_service(body: MCPCreateRequest):
    """Create a new MCP service. Backend auto-generates the id."""
    try:
        service = MCPService(
            name=body.name,
            description=body.description,
            enabled=body.enabled,
            server=body.server,
        )
        data = save_service(service)
        return {"success": True, "data": data}
    except Exception as exc:
        logger.exception("Failed to create MCP service")
        return {"success": False, "error": str(exc)}


@router.put("/services/{service_id}")
async def api_update_service(service_id: str, body: MCPUpdateRequest):
    """Update an existing MCP service. id is taken from URL, not body."""
    try:
        existing = get_service(service_id)
        if not existing:
            return {"success": False, "error": "MCP service not found"}
        # Preserve existing tools from the stored YAML
        tools_data = existing.get("tools", [])
        tools = [MCPTool(**t) if isinstance(t, dict) else t for t in tools_data]
        service = MCPService(
            id=service_id,
            name=body.name,
            description=body.description,
            enabled=body.enabled,
            server=body.server,
            tools=tools,
        )
        data = save_service(service)
        return {"success": True, "data": data}
    except Exception as exc:
        logger.exception("Failed to update MCP service %s", service_id)
        return {"success": False, "error": str(exc)}


@router.delete("/services/{service_id}")
async def api_delete_service(service_id: str):
    """Delete an MCP service by id."""
    try:
        deleted = delete_service(service_id)
        if not deleted:
            return {"success": False, "error": "MCP service not found"}
        return {"success": True}
    except Exception as exc:
        logger.exception("Failed to delete MCP service %s", service_id)
        return {"success": False, "error": str(exc)}


@router.post("/services/{service_id}/discover")
async def api_discover_tools(service_id: str):
    """Discover tools from an MCP server. Does NOT auto-save.

    Returns the discovered tools to the frontend.
    The frontend can then optionally save them via PUT.
    """
    try:
        tools = await discover_tools(service_id)
        return {
            "success": True,
            "tools": [t.model_dump() for t in tools],
        }
    except Exception as exc:
        logger.exception("Failed to discover tools for MCP service %s", service_id)
        return {"success": False, "error": str(exc)}


@router.post("/services/{service_id}/execute")
async def api_execute_tool(service_id: str, body: dict[str, Any]):
    """Execute a specific tool on an MCP service."""
    try:
        tool_name = body.get("tool_name", "")
        arguments = body.get("arguments", {})
        if not tool_name:
            return {"success": False, "error": "tool_name is required"}
        result = await execute_tool(service_id, tool_name, arguments)
        return {"success": True, "data": {"tool_name": tool_name, "result": result}}
    except Exception as exc:
        logger.exception(
            "Failed to execute tool %s on %s", body.get("tool_name"), service_id
        )
        return {"success": False, "error": str(exc)}



