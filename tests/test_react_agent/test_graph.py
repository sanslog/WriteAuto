import json

import pytest

from backend.config import DB_PATH
from backend.db.database import Database
from backend.db.repos import ChapterRepo, NovelRepo, PlotNodeRepo
from backend.llm.provider import LLMProvider
from backend.react_agent.graph import build_react_graph
from backend.react_agent.prompts import build_react_system_prompt
from backend.react_agent.state import ReactAgentState


class ScriptedProvider(LLMProvider):
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests: list[list[dict]] = []
        self.call_count = 0

    async def chat(self, messages, temperature=0.8, max_tokens=8192):
        raise AssertionError("ReAct graph should use chat_with_tools")

    async def chat_json(self, messages, temperature=0.3, max_tokens=4096):
        raise AssertionError("ReAct graph should use chat_with_tools")

    async def chat_with_tools(self, messages, tools=None, temperature=0.3, max_tokens=4096):
        self.requests.append(messages)
        if not self.responses:
            return {"type": "text", "content": "已完成"}
        return self.responses.pop(0)


def _tool_call(call_id: str, name: str, arguments: dict):
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }


def _latest_tool_payload(messages):
    payload = next(
        message["content"]
        for message in reversed(messages)
        if message.get("role") == "tool"
    )
    return json.loads(payload)


@pytest.mark.asyncio
async def test_react_graph_creates_novel_and_saves_chapter(temp_db):
    provider = ScriptedProvider(
        [
            {
                "type": "tool_calls",
                "calls": [
                    _tool_call(
                        "call_create_novel",
                        "create_novel",
                        {
                            "title": "低语之书",
                            "base_prompt": "一个青年能听见残稿说话",
                        },
                    )
                ],
            }
        ]
    )

    async def respond_with_chapter(messages, **_kwargs):
        provider.call_count += 1
        if provider.call_count == 1:
            return provider.responses.pop(0)
        if provider.call_count == 2:
            novel_id = _latest_tool_payload(messages)["data"]["id"]
            return {
                "type": "tool_calls",
                "calls": [
                    _tool_call(
                        "call_create_plot_node",
                        "create_plot_node",
                        {
                            "novel_id": novel_id,
                            "title": "听见残稿",
                            "summary": "主角首次听见残稿",
                            "detailed_outline": "闭馆后残稿开口，主角试图回应。",
                        },
                    )
                ],
            }
        if provider.call_count == 3:
            novel_id = _latest_tool_payload(messages)["data"]["novel_id"]
            return {
                "type": "tool_calls",
                "calls": [
                    _tool_call(
                        "call_create_chapter",
                        "create_chapter",
                        {
                            "novel_id": novel_id,
                            "title": "第一章 低语",
                            "content": "沈临在闭馆后的书架深处听见一页残稿开口说话。",
                        },
                    )
                ],
            }
        provider.responses.append(
            {"type": "text", "content": "小说已创建并保存第一章。"}
        )
        return {"type": "text", "content": "小说已创建并保存第一章。"}

    provider.chat_with_tools = respond_with_chapter  # type: ignore[method-assign]
    graph = build_react_graph(provider)
    result = await graph.ainvoke(
        {
            "session_id": "react-success",
            "user_request": "一个青年能听见残稿说话",
            "max_iterations": 4,
        },
        config={"configurable": {"thread_id": "react-success"}},
    )

    assert result["status"] == "partial"
    assert result["task_saved"] is True
    assert result["result"]["chapter_ids"]
    assert result["result"]["text"].startswith("沈临")

    db = Database(DB_PATH)
    await db.init()
    try:
        chapters = await ChapterRepo(db).get_by_novel(result["novel_id"])
    finally:
        await db.close()
    assert len(chapters) == 1
    assert chapters[0]["title"] == "第一章 低语"


@pytest.mark.asyncio
async def test_react_graph_stops_at_max_iterations(temp_db):
    provider = ScriptedProvider(
        [
            {
                "type": "tool_calls",
                "calls": [_tool_call("call_list", "list_novels", {})],
            }
        ]
    )
    graph = build_react_graph(provider)
    result = await graph.ainvoke(
        {
            "session_id": "react-max-rounds",
            "user_request": "写一个长篇故事",
            "max_iterations": 1,
        },
        config={"configurable": {"thread_id": "react-max-rounds"}},
    )

    assert result["iteration"] == 1
    assert result["status"] == "failed"
    assert "最大循环轮次" in result["error"]
    assert result["result"]["chapters"] == []


@pytest.mark.asyncio
async def test_react_graph_rejects_empty_request():
    graph = build_react_graph(ScriptedProvider([]))
    result = await graph.ainvoke(
        {"session_id": "react-empty", "user_request": "   "},
        config={"configurable": {"thread_id": "react-empty"}},
    )

    assert result["status"] == "failed"
    assert result["error"] == "用户请求不能为空"
    assert "agent" not in result["result"]["tools_used"]


def test_react_system_prompt_requires_persistence_and_safe_tools():
    prompt = build_react_system_prompt()
    assert "create_novel" in prompt
    assert "create_chapter" in prompt
    assert "get_writing_context" in prompt
    assert "complete_current_plot_node" in prompt
    assert "剧情游标" in prompt
    assert "不得编造工具返回值" in prompt
    assert "不更新模型配置" in prompt


@pytest.mark.asyncio
async def test_react_graph_completes_outline_node_and_advances_cursor(temp_db):
    provider = ScriptedProvider([])

    async def scripted_flow(messages, **_kwargs):
        provider.call_count += 1
        payload = _latest_tool_payload(messages) if provider.call_count > 1 else {}
        if provider.call_count == 1:
            return {
                "type": "tool_calls",
                "calls": [
                    _tool_call(
                        "call_create_novel",
                        "create_novel",
                        {"title": "铃与剑", "base_prompt": "少女用铜铃唤醒断剑"},
                    )
                ],
            }
        if provider.call_count == 2:
            return {
                "type": "tool_calls",
                "calls": [
                    _tool_call(
                        "call_create_plot_node",
                        "create_plot_node",
                        {
                            "novel_id": payload["data"]["id"],
                            "title": "唤醒断剑",
                            "summary": "铜铃第一次回应",
                            "detailed_outline": "少女在旧庙中摇铃，断剑有了呼吸。",
                        },
                    )
                ],
            }
        if provider.call_count == 3:
            return {
                "type": "tool_calls",
                "calls": [
                    _tool_call(
                        "call_get_context",
                        "get_writing_context",
                        {"novel_id": payload["data"]["novel_id"]},
                    )
                ],
            }
        if provider.call_count == 4:
            return {
                "type": "tool_calls",
                "calls": [
                    _tool_call(
                        "call_create_chapter",
                        "create_chapter",
                        {
                            "novel_id": payload["data"]["novel"]["id"],
                            "title": "第一章 铜铃",
                            "content": "少女摇动铜铃，庙里的断剑轻轻震了一下。",
                        },
                    )
                ],
            }
        return {
            "type": "tool_calls",
            "calls": [
                _tool_call(
                    "call_complete_node",
                    "complete_current_plot_node",
                    {
                        "novel_id": payload["data"]["novel_id"],
                        "chapter_id": payload["data"]["id"],
                        "character_states": [
                            {
                                "name": "少女",
                                "state": "获得断剑回应",
                                "location": "旧庙",
                                "status_condition": "正常",
                            }
                        ],
                        "resolved_foreshadow_ids": [],
                    },
                )
            ],
        }

    provider.chat_with_tools = scripted_flow  # type: ignore[method-assign]
    graph = build_react_graph(provider)
    result = await graph.ainvoke(
        {
            "session_id": "react-outline-complete",
            "user_request": "少女用铜铃唤醒断剑",
            "max_iterations": 8,
        },
        config={"configurable": {"thread_id": "react-outline-complete"}},
    )

    assert result["status"] == "completed"
    assert result["outline_complete"] is True
    assert result["cursor_position"] == 0
    assert result["result"]["chapter_ids"]

    db = Database(DB_PATH)
    await db.init()
    try:
        novel = await NovelRepo(db).get(result["novel_id"])
        nodes = await PlotNodeRepo(db).get_by_novel(result["novel_id"])
    finally:
        await db.close()
    assert novel["is_done"] == 1
    assert nodes[0]["status"] == "written"
    assert nodes[0]["chapter_id"] == result["result"]["chapter_ids"][0]
