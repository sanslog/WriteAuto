"""MCP (Model Context Protocol) integration for WriteAuto.

Provides MCP tool registration, YAML-based configuration storage,
LLM-powered tool decision, and tool execution within the generation graph.
"""

from backend.mcp.models import MCPService, MCPServerConfig
from backend.mcp.service import list_services, get_service, save_service, delete_service, execute_tool, discover_tools
from backend.mcp.node import mcp_tool_node

__all__ = [
    "MCPService",
    "MCPConfig",
    "MCPServerConfig",
    "list_services",
    "get_service",
    "save_service",
    "delete_service",
    "execute_tool",
    "discover_tools",
    "mcp_tool_node",
]

