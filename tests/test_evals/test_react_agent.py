import pytest

from backend.agent import cancellation
from backend.evals import EvalReport, ScriptedToolProvider, ToolCallSandbox, assert_report
from backend.react_agent.graph import build_react_graph


def _tool_call(call_id: str, name: str, arguments: dict | str):
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }


def _writing_tool_handler(name: str, arguments: dict, store: dict) -> dict:
    if name == "create_novel":
        novel_id = f"novel-{len(store) + 1}"
        store["novel_id"] = novel_id
        return {"id": novel_id}
    if name == "create_plot_node":
        novel_id = arguments["novel_id"]
        store.setdefault("plot_nodes", []).append(novel_id)
        return {"id": "plot-1", "novel_id": novel_id}
    if name == "get_writing_context":
        return {
            "novel": {"id": arguments["novel_id"]},
            "cursor_position": 0,
            "outline_nodes_count": 1,
            "outline_complete": False,
            "current_node": {"title": "旧宅闻铃"},
        }
    if name == "create_chapter":
        chapter_id = "chapter-1"
        store["chapter_id"] = chapter_id
        return {
            "id": chapter_id,
            "novel_id": arguments["novel_id"],
            "title": arguments["title"],
            "content": arguments["content"],
        }
    if name == "complete_current_plot_node":
        return {
            "novel_id": arguments["novel_id"],
            "cursor_position": 1,
            "outline_nodes_count": 1,
            "outline_complete": True,
        }
    return {"success": False, "error": f"Unexpected tool: {name}"}


@pytest.mark.asyncio
async def test_react_agent_plans_persists_and_completes_outline(monkeypatch):
    sandbox = ToolCallSandbox(_writing_tool_handler)
    provider = ScriptedToolProvider()

    def resolve(messages, tools):
        novel_id = sandbox.store.get("novel_id", "")
        if provider.call_count == 1:
            return {
                "type": "tool_calls",
                "calls": [_tool_call("create-novel", "create_novel", {"title": "青铜与残稿"})],
            }
        if provider.call_count == 2:
            return {
                "type": "tool_calls",
                "calls": [
                    _tool_call(
                        "create-plot",
                        "create_plot_node",
                        {
                            "novel_id": novel_id,
                            "title": "旧宅闻铃",
                            "summary": "林晚听见青铜铃",
                            "detailed_outline": "林晚在旧宅听见残稿说话。",
                        },
                    )
                ],
            }
        if provider.call_count == 3:
            return {
                "type": "tool_calls",
                "calls": [_tool_call("get-context", "get_writing_context", {"novel_id": novel_id})],
            }
        if provider.call_count == 4:
            return {
                "type": "tool_calls",
                "calls": [
                    _tool_call(
                        "create-chapter",
                        "create_chapter",
                        {
                            "novel_id": novel_id,
                            "title": "第一章 旧宅闻铃",
                            "content": "林晚听见青铜铃响起，残稿的第一页开口说话。",
                        },
                    )
                ],
            }
        return {
            "type": "tool_calls",
            "calls": [
                _tool_call(
                    "complete-plot",
                    "complete_current_plot_node",
                    {
                        "novel_id": novel_id,
                        "chapter_id": sandbox.store.get("chapter_id", ""),
                        "character_states": [],
                        "resolved_foreshadow_ids": [],
                    },
                )
            ],
        }

    provider.resolver = resolve
    monkeypatch.setattr(
        "backend.react_agent.nodes.tool_execution.execute_tool_calls",
        sandbox,
    )
    graph = build_react_graph(provider)
    result = await graph.ainvoke(
        {
            "session_id": "react-eval-success",
            "user_request": "写一个少女听见残稿说话的短篇开头",
            "max_iterations": 8,
        },
        config={"configurable": {"thread_id": "react-eval-success"}},
    )

    report = EvalReport("backend.react_agent.planning")
    report.check("outline_planned", result["result"]["outline_planned"] is True)
    report.check("uses_create_plot_node", "create_plot_node" in result["result"]["tools_used"])
    report.check("keeps_tool_sequence", sandbox.tool_names[0:3] == ["create_novel", "create_plot_node", "get_writing_context"])
    report.check("novel_id_propagates", result["novel_id"] == sandbox.store["novel_id"])
    report.check("chapter_saved", result["task_saved"] is True and result["result"]["chapter_ids"] == ["chapter-1"])
    report.check("outline_completed", result["result"]["outline_complete"] is True)
    report.check("status_completed", result["status"] == "completed")
    assert_report(report)


@pytest.mark.asyncio
async def test_react_agent_recovers_from_bad_tool_calls(monkeypatch):
    sandbox = ToolCallSandbox(_writing_tool_handler)
    provider = ScriptedToolProvider()

    def resolve(messages, tools):
        novel_id = sandbox.store.get("novel_id", "")
        if provider.call_count == 1:
            return {
                "type": "tool_calls",
                "calls": [
                    _tool_call("unknown", "not_a_tool", {}),
                    _tool_call("malformed", "create_plot_node", "{not-json"),
                ],
            }
        if provider.call_count == 2:
            return {
                "type": "tool_calls",
                "calls": [_tool_call("create-novel", "create_novel", {"title": "错误恢复"})],
            }
        if provider.call_count == 3:
            return {
                "type": "tool_calls",
                "calls": [_tool_call("create-plot", "create_plot_node", {
                    "novel_id": novel_id,
                    "title": "旧宅闻铃",
                    "summary": "恢复后的规划",
                    "detailed_outline": "先规划，再写正文。",
                })],
            }
        if provider.call_count == 4:
            return {
                "type": "tool_calls",
                "calls": [_tool_call("create-chapter", "create_chapter", {
                    "novel_id": novel_id,
                    "title": "第一章 恢复",
                    "content": "这是错误恢复后的正文。",
                })],
            }
        return {"type": "text", "content": "章节已保存。"}

    provider.resolver = resolve
    monkeypatch.setattr(
        "backend.react_agent.nodes.tool_execution.execute_tool_calls",
        sandbox,
    )
    graph = build_react_graph(provider)
    result = await graph.ainvoke(
        {
            "session_id": "react-eval-error-recovery",
            "user_request": "写一个错误恢复测试开头",
            "max_iterations": 6,
        },
        config={"configurable": {"thread_id": "react-eval-error-recovery"}},
    )

    report = EvalReport("backend.react_agent.tool_error_recovery")
    report.check("records_unknown_tool", "not_a_tool" in sandbox.tool_names)
    report.check("records_malformed_call", "create_plot_node" in sandbox.tool_names)
    report.check("continues_after_errors", result["result"]["tools_used"][:2] == ["not_a_tool", "create_plot_node"])
    report.check("saves_after_recovery", result["task_saved"] is True)
    report.check("partial_status_not_failure", result["status"] == "partial")
    assert_report(report)


@pytest.mark.asyncio
async def test_react_agent_handles_llm_failure_and_cancellation(monkeypatch):
    def explode(messages, tools):
        raise RuntimeError("provider unavailable")

    failure_provider = ScriptedToolProvider(resolver=explode)
    monkeypatch.setattr(
        "backend.react_agent.nodes.tool_execution.execute_tool_calls",
        ToolCallSandbox(),
    )
    graph = build_react_graph(failure_provider)
    failed = await graph.ainvoke(
        {
            "session_id": "react-eval-provider-failure",
            "user_request": "写一个稳定失败的测试",
        },
        config={"configurable": {"thread_id": "react-eval-provider-failure"}},
    )

    cancellation.register("react-eval-cancel-generation")
    cancellation.cancel("react-eval-cancel-generation")
    cancelled_provider = ScriptedToolProvider()
    cancelled_graph = build_react_graph(cancelled_provider)
    try:
        cancelled = await cancelled_graph.ainvoke(
            {
                "session_id": "react-eval-cancel",
                "user_request": "写一个应当被取消的任务",
                "generation_id": "react-eval-cancel-generation",
            },
            config={"configurable": {"thread_id": "react-eval-cancel"}},
        )
    finally:
        cancellation.unregister("react-eval-cancel-generation")

    report = EvalReport("backend.react_agent.runtime_errors")
    report.check("llm_failure_status_failed", failed["status"] == "failed")
    report.check("llm_failure_message", "provider unavailable" in failed["error"])
    report.check("cancelled_status", cancelled["status"] == "cancelled")
    report.check("cancelled_before_llm", cancelled_provider.call_count == 0)
    assert_report(report)


@pytest.mark.asyncio
async def test_react_agent_rejects_empty_input_and_max_iterations(monkeypatch):
    empty_provider = ScriptedToolProvider()
    maxed_provider = ScriptedToolProvider(
        [{"type": "tool_calls", "calls": [_tool_call("list", "list_novels", {})]}]
    )
    monkeypatch.setattr(
        "backend.react_agent.nodes.tool_execution.execute_tool_calls",
        ToolCallSandbox(),
    )
    graph = build_react_graph(empty_provider)
    empty = await graph.ainvoke(
        {"session_id": "react-eval-empty", "user_request": " "},
        config={"configurable": {"thread_id": "react-eval-empty"}},
    )
    maxed_graph = build_react_graph(maxed_provider)
    maxed = await maxed_graph.ainvoke(
        {
            "session_id": "react-eval-max",
            "user_request": "写一个长篇故事",
            "max_iterations": 1,
        },
        config={"configurable": {"thread_id": "react-eval-max"}},
    )

    report = EvalReport("backend.react_agent.guardrails")
    report.check("empty_request_rejected", empty["status"] == "failed" and "不能为空" in empty["error"])
    report.check("empty_request_does_not_call_llm", empty_provider.call_count == 0)
    report.check("max_iteration_uses_llm", maxed_provider.call_count == 1)
    report.check("max_iteration_stops", maxed["status"] == "failed" and maxed["iteration"] == 1)
    assert_report(report)
