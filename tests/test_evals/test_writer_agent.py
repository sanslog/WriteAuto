import pytest
from langgraph.types import Command

from backend.agent.graph import build_graph
from backend.db.database import Database
from backend.db.repos import (
    ChapterRepo,
    CharacterRepo,
    ForeshadowRepo,
    NovelRepo,
    PlotNodeRepo,
)
from backend.evals import EvalReport, assert_report
from backend.llm.provider import LLMProvider


GENERATED_TEXT = "第一章 起点\n\n林晚听见青铜铃响起，残稿的第一页开口说话。"


class StaticLLM(LLMProvider):
    async def chat(self, messages, temperature=0.8, max_tokens=8192):
        raise AssertionError("Writer graph should not use raw chat")

    async def chat_json(self, messages, temperature=0.3, max_tokens=4096):
        return {"states": [{"name": "林晚", "state": "听见铃声", "location": "旧宅", "status_condition": "正常"}]}


class ExplodingLLM(LLMProvider):
    async def chat(self, messages, temperature=0.8, max_tokens=8192):
        raise AssertionError("Writer graph should not use raw chat")

    async def chat_json(self, messages, temperature=0.3, max_tokens=4096):
        raise RuntimeError("state extractor unavailable")

@pytest.mark.asyncio
async def test_writer_graph_plans_with_context_and_persists_approval(temp_db, monkeypatch):
    db = Database(temp_db)
    await db.init()
    try:
        novel = await NovelRepo(db).create(
            {
                "title": "青铜与残稿",
                "base_prompt": "少女能听见残稿说话",
                "style_of_writing": "克制的第三人称",
                "world_outlook": "残稿持有记忆",
            }
        )
        novel_id = novel["id"]
        node = await PlotNodeRepo(db).create(
            {
                "novel_id": novel_id,
                "title": "旧宅闻铃",
                "summary": "林晚第一次听见青铜铃",
                "detailed_outline": "林晚在旧宅深处听见残稿开口，青铜铃突然响起。",
            }
        )
        character = await CharacterRepo(db).create(
            {
                "novel_id": novel_id,
                "name": "林晚",
                "description": "沉默寡言的旧宅继承人",
                "role": "主角",
            }
        )
        await PlotNodeRepo(db).create(
            {
                "novel_id": novel_id,
                "title": "残稿之争",
                "summary": "外人也盯上了残稿",
                "detailed_outline": "神秘书商到访，林晚必须交出残稿或查明来历。",
            }
        )
        await ForeshadowRepo(db).create(
            {
                "novel_id": novel_id,
                "title": "缺页残稿",
                "description": "缺页指向林晚父亲失踪的真相",
            }
        )
        await db.conn.commit()
    finally:
        await db.close()

    monkeypatch.setattr("backend.llm.factory.create_llm_provider", lambda: StaticLLM())
    graph = build_graph()
    config = {"configurable": {"thread_id": "writer-eval-success"}}
    state = {
        "base_prompt": "",
        "style_of_writing": "",
        "world_outlook": "",
        "outline": "",
        "detailed_outline": "",
        "cursor_position": 0,
        "plot_nodes_count": 0,
        "next_node_title": "",
        "main_character_design": "",
        "foreshadow": "",
        "context": "",
        "chapter_ids": [],
        "foreshadow_ids": [],
        "generated_text": "",
        "chapter_titles": [],
        "character_states_json": "[]",
        "mcp_results": [],
        "mcp_context": "",
        "enter_loop": False,
        "should_end": False,
        "modification_count": 0,
        "modification_opinion": "",
        "unlawful": False,
        "unlaw_reason": "",
        "novel_id": novel_id,
        "generation_id": "writer-eval-generation",
        "_saved_chapters": [],
        "_cancelled": False,
    }

    generation_prompt_state = await graph.ainvoke(state, config=config)
    interrupt = generation_prompt_state["__interrupt__"][0].value

    report = EvalReport("backend.agent.workflow")
    report.check("compiles", {"init_check", "character_fetch", "content_generation", "content_judge"} <= set(graph.nodes))
    report.check("stops_for_generation", interrupt["type"] == "generation_request")
    prompt = interrupt["system"] + "\n" + interrupt["user"]
    report.check(
        "injects_planning_context",
        all(marker in prompt for marker in ("残稿持有记忆", "旧宅闻铃", "林晚", "缺页残稿")),
    )
    assert_report(report)

    judgment_state = await graph.ainvoke(
        Command(resume={"generated_text": GENERATED_TEXT}), config=config
    )
    judgment = judgment_state["__interrupt__"][0].value
    assert judgment["type"] == "judgment"
    assert judgment["generated_text"] == GENERATED_TEXT

    final_state = await graph.ainvoke(Command(resume={"action": "approve"}), config=config)

    report = EvalReport("backend.agent.persistence")
    report.check("approval_ends_graph", final_state.get("should_end") is True)
    report.check("one_chapter_saved", len(final_state["_saved_chapters"]) == 1)

    db = Database(temp_db)
    await db.init()
    try:
        chapters = await ChapterRepo(db).get_by_novel(novel_id)
        nodes = await PlotNodeRepo(db).get_by_novel(novel_id)
        novel_data = await NovelRepo(db).get(novel_id)
        states = await CharacterRepo(db).get_states(character["id"])
    finally:
        await db.close()

    report.check("chapter_approved", chapters[0]["status"] == "approved")
    report.check("plot_node_written", nodes[0]["status"] == "written")
    report.check("cursor_advanced", novel_data["cursor_position"] == 1)
    report.check("character_state_saved", states[0]["chapter_id"] == chapters[0]["id"])
    assert_report(report)


@pytest.mark.asyncio
async def test_writer_graph_survives_llm_state_extraction_failure(temp_db, monkeypatch):
    db = Database(temp_db)
    await db.init()
    try:
        novel = await NovelRepo(db).create({"title": "failure eval"})
        await PlotNodeRepo(db).create(
            {"novel_id": novel["id"], "title": "起点", "detailed_outline": "写一段失败恢复场景。"}
        )
        await db.conn.commit()
        novel_id = novel["id"]
    finally:
        await db.close()

    monkeypatch.setattr("backend.llm.factory.create_llm_provider", lambda: ExplodingLLM())
    graph = build_graph()
    config = {"configurable": {"thread_id": "writer-eval-llm-failure"}}
    await graph.ainvoke(
        {
            "novel_id": novel_id,
            "generation_id": "writer-eval-llm-failure-generation",
            "chapter_ids": [],
            "foreshadow_ids": [],
            "_saved_chapters": [],
            "_cancelled": False,
        },
        config=config,
    )
    final_state = await graph.ainvoke(
        Command(resume={"generated_text": GENERATED_TEXT}), config=config
    )

    report = EvalReport("backend.agent.exception_handling")
    report.check("generation_interrupt_reached", final_state.get("__interrupt__") is not None)
    report.check("empty_state_json_fallback", final_state.get("character_states_json") == "[]")
    report.check("saved_chapter_still_present", len(final_state.get("_saved_chapters", [])) == 1)
    assert_report(report)


@pytest.mark.asyncio
async def test_mcp_tool_node_plans_tools_and_recovers_from_errors(monkeypatch):
    from backend.mcp.node import mcp_tool_node

    requests: list[list[dict]] = []

    async def scripted_llm(messages, tools):
        requests.append(messages)
        if len(requests) == 1:
            return {
                "type": "tool_calls",
                "calls": [
                    {
                        "id": "bad_name",
                        "function": {"name": "malformed", "arguments": {}},
                    },
                    {
                        "id": "failing_tool",
                        "function": {
                            "name": "history__explode",
                            "arguments": {"query": "1920s Shanghai"},
                        },
                    },
                    {
                        "id": "working_tool",
                        "function": {
                            "name": "history__query",
                            "arguments": {"query": "1920s Shanghai"},
                        },
                    },
                ],
            }
        return {"type": "text", "content": "资料已足够"}

    async def fake_execute(service_id, tool_name, arguments, timeout=60):
        if tool_name == "explode":
            raise RuntimeError("remote MCP unavailable")
        return f"{arguments['query']} 资料"

    monkeypatch.setattr("backend.mcp.node.list_services", lambda: [
        {
            "id": "history",
            "name": "history",
            "enabled": True,
            "tools": [{"name": "query", "description": "query history", "input_schema": {"type": "object"}}],
        }
    ])
    monkeypatch.setattr("backend.mcp.node._call_llm_with_tools", scripted_llm)
    monkeypatch.setattr("backend.mcp.node.execute_tool", fake_execute)

    result = await mcp_tool_node(
        {
            "base_prompt": "旧上海",
            "outline": "1. 旧宅闻铃",
            "mcp_results": [],
            "mcp_context": "",
            "_cancelled": False,
        }
    )

    report = EvalReport("backend.agent.mcp_tools")
    report.check("uses_llm_planning_rounds", len(requests) == 2)
    report.check("executes_three_calls", len(result["mcp_results"]) == 3)
    report.check("marks_unknown_tool_failed", result["mcp_results"][0]["success"] is False)
    report.check("marks_remote_failure", result["mcp_results"][1]["success"] is False)
    report.check("keeps_successful_result", result["mcp_results"][2]["success"] is True)
    report.check("includes_ok_and_failed_context", "[OK]" in result["mcp_context"] and "[FAILED]" in result["mcp_context"])
    assert_report(report)


async def _resume_until_generation_request(graph, config, resume_value):
    """Resume the graph, answering MCP planning rounds, until text generation."""
    result = await graph.ainvoke(Command(resume=resume_value), config=config)
    interrupts = result.get("__interrupt__") or []
    while interrupts and interrupts[0].value.get("type") == "mcp_tool_call":
        result = await graph.ainvoke(
            Command(resume={"result_json": '{"type": "text", "content": ""}'}),
            config=config,
        )
        interrupts = result.get("__interrupt__") or []
    return result


@pytest.mark.asyncio
async def test_writer_graph_modify_round_promotes_opinion_without_history(
    temp_db, monkeypatch
):
    """A modify round carries the opinion in state and accumulates no history."""
    db = Database(temp_db)
    await db.init()
    try:
        novel = await NovelRepo(db).create(
            {
                "title": "修改回路",
                "base_prompt": "少年与青铜铃",
                "style_of_writing": "克制的第三人称",
                "world_outlook": "残稿持有记忆",
            }
        )
        novel_id = novel["id"]
        await PlotNodeRepo(db).create(
            {
                "novel_id": novel_id,
                "title": "旧宅闻铃",
                "summary": "林晚第一次听见青铜铃",
                "detailed_outline": "林晚在旧宅深处听见残稿开口。",
            }
        )
        await CharacterRepo(db).create(
            {
                "novel_id": novel_id,
                "name": "林晚",
                "description": "沉默寡言的旧宅继承人",
                "role": "主角",
            }
        )
        await db.conn.commit()
    finally:
        await db.close()

    monkeypatch.setattr("backend.llm.factory.create_llm_provider", lambda: StaticLLM())
    graph = build_graph()
    config = {"configurable": {"thread_id": "writer-eval-modify-round"}}

    await graph.ainvoke(
        {
            "novel_id": novel_id,
            "generation_id": "writer-eval-modify-generation",
            "chapter_ids": [],
            "foreshadow_ids": [],
            "_saved_chapters": [],
            "_cancelled": False,
        },
        config=config,
    )
    judgment_state = await graph.ainvoke(
        Command(resume={"generated_text": GENERATED_TEXT}), config=config
    )
    assert judgment_state["__interrupt__"][0].value["type"] == "judgment"

    opinion = "把结尾改得更有冲击力"
    result = await _resume_until_generation_request(
        graph, config, {"action": "modify", "text": opinion}
    )
    interrupt = result["__interrupt__"][0].value
    checkpointed = graph.get_state(config).values

    report = EvalReport("backend.agent.modify_loop")
    report.check("regenerates_after_modify", interrupt["type"] == "generation_request")
    report.check("opinion_injected_into_prompt", opinion in interrupt["user"])
    report.check("round_counted", result.get("modification_count") == 1)
    report.check("opinion_kept_in_state", result.get("modification_opinion") == opinion)
    report.check("state_has_no_history_channel", "messages" not in checkpointed)
    report.check("state_has_no_legacy_field", "user_input_text" not in checkpointed)

    # Finish this round, then submit a blank "modify" request: the loop must
    # end instead of regenerating with nothing to act on.
    await graph.ainvoke(Command(resume={"generated_text": GENERATED_TEXT}), config=config)
    ended = await graph.ainvoke(
        Command(resume={"action": "modify", "text": "   "}), config=config
    )
    report.check("blank_opinion_ends_run", ended.get("should_end") is True)
    report.check("blank_opinion_stops_looping", ended.get("enter_loop") is False)
    report.check("blank_opinion_keeps_round_count", ended.get("modification_count") == 1)
    assert_report(report)
