"""Pydantic models for MCP service configuration (Streamable HTTP transport).

MCP services are defined as YAML files stored in data/mcp_configs/.
Each file represents one MCP server with its tools.
The service id is derived from the filename, not stored in the YAML content.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field


class MCPTool(BaseModel):
    """Definition of a single tool exposed by an MCP server."""

    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)


class MCPServerConfig(BaseModel):
    """Streamable HTTP MCP endpoint connection details."""

    url: str = ""


class MCPCreateRequest(BaseModel):
    """Request body for creating a new MCP service."""

    name: str
    description: str = ""
    enabled: bool = True
    server: MCPServerConfig


class MCPUpdateRequest(BaseModel):
    """Request body for updating an existing MCP service."""

    name: str
    description: str = ""
    enabled: bool = True
    server: MCPServerConfig


class MCPService(BaseModel):
    """A complete MCP service entry, as returned by the API.

    id is populated by the backend from the YAML filename.
    """

    id: str = ""
    name: str
    description: str = ""
    enabled: bool = True
    server: MCPServerConfig
    tools: list[MCPTool] = Field(default_factory=list)

    def model_dump(self, **kwargs) -> dict[str, Any]:
        data = super().model_dump(**kwargs)
        data["tools"] = [json.loads(t.model_dump_json()) for t in self.tools]
        return data
