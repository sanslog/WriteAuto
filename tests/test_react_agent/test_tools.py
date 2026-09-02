"""Tests for the ReAct agent's backend tool catalog."""

import logging

import pytest

from backend.react_agent.tools import (
    AgentTool,
    ToolCategory,
    execute_tool_calls,
    find_tool,
    get_agent_tools,
    get_all_tools,
    get_tools_by_category,
)
from backend.react_agent.tools.character import create_character
from backend.react_agent.tools.chapter import (
    create_chapter,
    delete_chapter,
    get_chapter,
)
from backend.react_agent.tools.foreshadow import (
    create_foreshadow,
    update_foreshadow,
)
from backend.react_agent.tools.novel import create_novel, delete_novel, get_novel
from backend.react_agent.tools.outline import (
    create_plot_node,
    delete_plot_node,
    move_plot_cursor,
)
from backend.react_agent.tools.settings import get_settings, update_settings


def test_tool_catalog_is_typed_and_routed():
    tools = get_all_tools()
    assert len(tools) >= 20
    assert len({tool.name for tool in tools}) == len(tools)
    assert all(isinstance(tool, AgentTool) for tool in tools)
    assert all(tool.description for tool in tools)

    expected_categories = {
        ToolCategory.NOVEL,
        ToolCategory.OUTLINE,
        ToolCategory.CHAPTER,
        ToolCategory.CHARACTER,
        ToolCategory.FORESHADOW,
        ToolCategory.SETTINGS,
    }
    assert {tool.category for tool in tools} == expected_categories

    agent_tools = get_agent_tools()
    agent_names = {tool.name for tool in agent_tools}
    assert "create_novel" in agent_names
    assert "create_chapter" in agent_names
    assert "delete_novel" not in agent_names
    assert "update_settings" not in agent_names

    outline_names = {tool.name for tool in get_tools_by_category(ToolCategory.OUTLINE)}
    assert {"list_plot_nodes", "create_plot_node", "move_plot_cursor"} <= outline_names


def test_openai_tool_schema_contains_domain_description():
    tool = find_tool("create_chapter")
    assert tool is not None

    schema = tool.to_openai_tool()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "create_chapter"
    assert "章节正文" in schema["function"]["description"]
    properties = schema["function"]["parameters"]["properties"]
    assert {"novel_id", "title", "content"} <= set(properties)


@pytest.mark.asyncio
async def test_execute_tool_calls_parses_and_routes_openai_format(temp_db):
    observations = await execute_tool_calls(
        [
            {
                "id": "call_create",
                "type": "function",
                "function": {
                    "name": "create_novel",
                    "arguments": '{"title":"路由测试","base_prompt":"一句一句话写小说"}',
                },
            },
            {
                "id": "call_unknown",
                "type": "function",
                "function": {"name": "not_a_tool", "arguments": "{}"},
            },
        ]
    )

    assert len(observations) == 2
    assert observations[0]["tool_call_id"] == "call_create"
    assert observations[0]["result"]["success"] is True
    assert observations[0]["result"]["data"]["title"] == "路由测试"
    assert observations[1]["result"]["error_type"] == "unknown_tool"


@pytest.mark.asyncio
async def test_novel_writing_flow_is_persisted(temp_db):
    created = await create_novel(
        title="一句书香",
        base_prompt="一个年轻修士发现自己能听见文字的声音",
        style_of_writing="第三人称，节奏偏快",
        world_outlook="修行与图书馆共存的古代世界",
    )
    assert created["success"] is True
    novel_id = created["data"]["id"]

    node_a = await create_plot_node(
        novel_id=novel_id,
        title="听见文字",
        summary="主角第一次获得异能",
        detailed_outline="主角深夜整理书架，突然听见一页残稿在低语。",
    )
    node_b = await create_plot_node(
        novel_id=novel_id,
        title="残稿之争",
        summary="外人盯上了残稿",
        detailed_outline="神秘书商到访，主角必须在交出残稿和追查来历之间选择。",
    )
    assert [node_a["data"]["sort_order"], node_b["data"]["sort_order"]] == [0, 1]

    cursor = await move_plot_cursor(novel_id=novel_id, cursor_position=99)
    assert cursor["data"]["cursor_position"] == 1

    character = await create_character(
        novel_id=novel_id,
        name="沈临",
        description="沉默寡言的图书馆学徒，能听见文字情绪",
        role="主角",
    )
    assert character["success"] is True

    foreshadow = await create_foreshadow(
        novel_id=novel_id,
        title="缺页残稿",
        description="残稿缺的一页指向主角父亲失踪的真相",
    )
    assert foreshadow["success"] is True

    chapter = await create_chapter(
        novel_id=novel_id,
        title="第一章 低语",
        content="沈临在闭馆后听见书架深处传来一句不成句的话。",
    )
    assert chapter["data"]["word_count"] == len(chapter["data"]["content"])

    chapter_id = chapter["data"]["id"]
    fetched = await get_chapter(chapter_id)
    assert fetched["data"]["title"] == "第一章 低语"

    novel = await get_novel(novel_id)
    assert novel["data"]["cursor_position"] == 1
    assert novel["data"]["base_prompt"].startswith("一个年轻修士")


@pytest.mark.asyncio
async def test_delete_plot_node_corrects_cursor(temp_db):
    novel = await create_novel(title="光标修正测试")
    novel_id = novel["data"]["id"]
    for index in range(3):
        await create_plot_node(novel_id=novel_id, title=f"节点{index}")

    await move_plot_cursor(novel_id=novel_id, cursor_position=2)
    nodes = (await find_tool("list_plot_nodes").run({"novel_id": novel_id}))["data"]
    deleted = await delete_plot_node(node_id=nodes[1]["id"])

    assert deleted["success"] is True
    assert deleted["data"]["cursor_position"] == 1


@pytest.mark.asyncio
async def test_update_and_delete_tools_return_tool_observations(temp_db):
    novel = await create_novel(title="旧题")
    novel_id = novel["data"]["id"]
    chapter = await create_chapter(
        novel_id=novel_id,
        title="草稿",
        content="第一版内容",
    )
    foreshadow = await create_foreshadow(novel_id=novel_id, title="铜铃")

    updated_chapter = await find_tool("update_chapter").run(
        {
            "chapter_id": chapter["data"]["id"],
            "content": "修改后的内容更长一些",
            "status": "approved",
        }
    )
    assert updated_chapter["success"] is True
    assert updated_chapter["data"]["word_count"] == len("修改后的内容更长一些")

    updated_foreshadow = await update_foreshadow(
        foreshadow["data"]["id"], status="resolved"
    )
    assert updated_foreshadow["data"]["status"] == "resolved"

    removed_chapter = await delete_chapter(chapter["data"]["id"])
    removed_novel = await delete_novel(novel_id)
    assert removed_chapter["data"]["deleted"] is True
    assert removed_novel["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_missing_parent_and_unknown_tool_fail_gracefully(temp_db):
    missing_novel = await find_tool("create_character").run(
        {"novel_id": "does-not-exist", "name": "孤儿角色"}
    )
    assert missing_novel["success"] is False
    assert "not found" in missing_novel["error"]

    unknown = find_tool("not_a_tool")
    assert unknown is None


@pytest.mark.asyncio
async def test_settings_tool_and_sensitive_argument_logging(temp_db, caplog):
    settings = await get_settings()
    assert settings["success"] is True

    update_tool = find_tool("update_settings")
    assert update_tool is not None
    assert update_tool.safe_for_agent is False

    with caplog.at_level(logging.INFO, logger="backend.react_agent.tools.base"):
        result = await update_tool.run(
            {"fields": {"custom_api_key": "sk-do-not-log", "theme": "dark"}}
        )

    assert result["success"] is True
    assert result["data"]["theme"] == "dark"
    assert "sk-do-not-log" not in caplog.text
    assert "***" in caplog.text
