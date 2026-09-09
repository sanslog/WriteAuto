# """Tests for MCP integration - models, service manager, and graph nodes."""

# from __future__ import annotations

# import json
# import tempfile
# from pathlib import Path

# import pytest
# import yaml

# from backend.mcp.models import MCPService, MCPTool, MCPServerConfig
# from backend.mcp.service import (
#     list_services,
#     get_service,
#     save_service,
#     delete_service,
# )


# class TestMCPServiceModels:
#     """Test MCP model validation and serialization."""

#     def test_mcp_tool_defaults(self):
#         tool = MCPTool(name="test_tool")
#         assert tool.name == "test_tool"
#         assert tool.description == ""
#         assert tool.input_schema == {}

#     def test_mcp_tool_full(self):
#         tool = MCPTool(
#             name="search",
#             description="Search the web",
#             input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
#         )
#         data = tool.model_dump()
#         assert data["name"] == "search"

#     def test_mcp_server_config(self):
#         config = MCPServerConfig(url="https://mcp.example.com/mcp")
#         assert config.url == "https://mcp.example.com/mcp"

#     def test_mcp_service_create(self):
#         service = MCPService(
#             name="Test Service",
#             server=MCPServerConfig(url="https://mcp.example.com/mcp"),
#             tools=[MCPTool(name="tool1", description="First tool")],
#         )
#         assert len(service.tools) == 1

#     def test_mcp_service_serialize_deserialize(self):
#         service = MCPService(
#             name="Serialize Test",
#             server=MCPServerConfig(url="https://mcp.example.com/mcp"),
#             tools=[MCPTool(name="greet")],
#         )
#         data = json.loads(service.model_dump_json())
#         restored = MCPService(**data)
#         assert restored.name == "Serialize Test"


# @pytest.mark.asyncio
# class TestMCPServicePersistence:
#     """Test YAML-based persistence of MCP services."""

#     @pytest.fixture(autouse=True)
#     def _patch_config_dir(self, monkeypatch):
#         self.tmp_dir = Path(tempfile.mkdtemp())
#         monkeypatch.setattr("backend.mcp.service.MCP_CONFIGS_DIR", self.tmp_dir)
#         yield
#         import shutil
#         shutil.rmtree(self.tmp_dir, ignore_errors=True)

#     async def test_save_and_list_service(self):
#         service = MCPService(
#             name="Save Test",
#             server=MCPServerConfig(url="https://mcp.example.com/mcp"),
#             tools=[MCPTool(name="ping")],
#         )
#         saved = save_service(service)
#         assert saved["name"] == "Save Test"
#         services = list_services()
#         assert len(services) == 1

#     async def test_get_service_by_id(self):
#         service = MCPService(name="Get Test", server=MCPServerConfig(url="https://mcp.example.com/mcp"))
#         saved = save_service(service)
#         assert get_service(saved["id"]) is not None

#     async def test_delete_service(self):
#         service = MCPService(name="Delete Test", server=MCPServerConfig(url="https://mcp.example.com/mcp"))
#         saved = save_service(service)
#         assert delete_service(saved["id"]) is True
#         assert delete_service(saved["id"]) is False

#     async def test_list_empty_dir(self):
#         assert list_services() == []


# @pytest.mark.asyncio
# class TestMCPToolNode:
#     """Test the single MCP tool node (LLM decision + execution)."""

#     async def test_skips_without_text(self, monkeypatch):
#         from backend.mcp.node import mcp_tool_node

#         monkeypatch.setattr("backend.mcp.node.list_services", lambda: [])
#         result = await mcp_tool_node({"generated_text": "", "_cancelled": False, "chapter_titles": [], "context": ""})
#         assert result == {"mcp_results": [], "mcp_context": ""}

#     async def test_skips_when_cancelled(self, monkeypatch):
#         from backend.mcp.node import mcp_tool_node

#         monkeypatch.setattr("backend.mcp.node.list_services", lambda: [])
#         result = await mcp_tool_node({"generated_text": "text", "_cancelled": True})
#         assert result == {"mcp_results": [], "mcp_context": ""}

#     async def test_skips_with_no_services(self, monkeypatch):
#         from backend.mcp.node import mcp_tool_node

#         monkeypatch.setattr("backend.mcp.node.list_services", lambda: [])
#         result = await mcp_tool_node({"generated_text": "Hello", "_cancelled": False, "chapter_titles": [], "context": ""})
#         assert result == {"mcp_results": [], "mcp_context": ""}


# class TestMCPGraphIntegration:
#     """Test that the graph correctly includes the single MCP tool node."""

#     def test_graph_has_mcp_tool_node(self):
#         from backend.agent.graph import continue_writing_graph

#         nodes = list(continue_writing_graph.nodes.keys())
#         assert "mcp_tool" in nodes, "mcp_tool node missing from graph"
#         assert "mcp_decision" not in nodes, "mcp_decision should not exist"
#         assert "mcp_execution" not in nodes, "mcp_execution should not exist"
#         assert "content_generation" in nodes
#         assert "content_judge" in nodes

#     def test_node_ordering(self):
#         from backend.agent.graph import continue_writing_graph

#         graph = continue_writing_graph.get_graph(xray=False)
#         node_ids = [str(n) for n in graph.nodes]
#         gen_idx = node_ids.index("content_generation")
#         mcp_idx = node_ids.index("mcp_tool")
#         jdg_idx = node_ids.index("content_judge")
#         assert gen_idx < mcp_idx < jdg_idx, "expected generation → mcp_tool → judgment"


# class TestMCPYamlSerialization:
#     """Test YAML round-trip serialization of MCP services."""

#     def test_yaml_roundtrip(self):
#         service = MCPService(
#             name="YAML Test",
#             description="测试YAML",
#             server=MCPServerConfig(url="https://mcp.example.com/mcp"),
#             tools=[MCPTool(name="search"), MCPTool(name="analyze")],
#         )
#         data = service.model_dump()
#         data.pop("id", None)
#         yaml_str = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
#         restored = MCPService(**yaml.safe_load(yaml_str))
#         assert restored.name == "YAML Test"
#         assert len(restored.tools) == 2




