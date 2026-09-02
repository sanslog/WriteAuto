"""Nodes for the one-sentence novel-writing ReAct loop."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from backend.agent import cancellation
from backend.llm.provider import LLMProvider
from backend.react_agent.prompts import build_react_system_prompt, build_react_user_prompt
from backend.react_agent.state import DEFAULT_MAX_REACT_ITERATIONS
from backend.react_agent.state import ReactAgentState
from backend.react_agent.tools.chapter import create_chapter
from backend.react_agent.tools.registry import execute_tool_calls, build_openai_tools

logger = logging.getLogger(__name__)


def _message_text(message: Any) -> str:
    content = message.get("content") if isinstance(message, dict) else message
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        ).strip()
    return ""


def _assistant_wire_tool_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wire_calls: list[dict[str, Any]] = []
    for index, call in enumerate(calls):
        function = call.get("function", {})
        arguments = function.get("arguments", {})
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments, ensure_ascii=False, default=str)
        wire_calls.append(
            {
                "id": call.get("id") or f"call_{index}",
                "type": "function",
                "function": {"name": function.get("name", ""), "arguments": arguments},
            }
        )
    return wire_calls


async def validate_input_node(state: ReactAgentState) -> dict[str, Any]:
    """Normalise the invocation and prepare the first provider messages."""

    request = str(state.get("user_request", "")).strip()
    if not request:
        logger.warning("ReAct agent rejected an empty writing request")
        return {
            "status": "failed",
            "error": "用户请求不能为空",
            "should_end": True,
            "chat_messages": [],
        }

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": build_react_system_prompt()},
        {
            "role": "user",
            "content": build_react_user_prompt(request, str(state.get("novel_id", ""))),
        },
    ]
    logger.info("ReAct agent accepted writing request (length=%d)", len(request))
    return {
        "chat_messages": messages,
        "tool_calls": [],
        "observations": [],
        "tools_used": [],
        "iteration": 0,
        "max_iterations": max(
            1,
            int(state.get("max_iterations") or DEFAULT_MAX_REACT_ITERATIONS),
        ),
        "status": "planning",
        "error": "",
        "cancelled": False,
        "task_saved": bool(state.get("saved_chapters")),
        "saved_chapters": list(state.get("saved_chapters", [])),
        "outline_planned": bool(state.get("outline_planned")),
        "outline_complete": bool(state.get("outline_complete")),
        "should_end": False,
    }


def make_agent_node(provider: LLMProvider):
    """Create the reasoning node bound to an LLM provider."""

    async def agent_node(state: ReactAgentState) -> dict[str, Any]:
        iteration = int(state.get("iteration", 0)) + 1
        max_iterations = max(
            1,
            int(state.get("max_iterations") or DEFAULT_MAX_REACT_ITERATIONS),
        )
        generation_id = str(state.get("generation_id", ""))

        if generation_id:
            provider.set_gen_id(generation_id)
            if cancellation.is_cancelled(generation_id):
                logger.info("ReAct agent cancelled before round %d", iteration)
                return {
                    "iteration": iteration,
                    "tool_calls": [],
                    "should_end": True,
                    "cancelled": True,
                    "status": "cancelled",
                    "error": "任务已取消",
                }

        if iteration > max_iterations:
            logger.warning("ReAct agent reached max rounds: %d", max_iterations)
            return {
                "iteration": iteration,
                "tool_calls": [],
                "should_end": True,
                "status": "failed",
                "error": f"已达最大循环轮次（{max_iterations}）",
            }

        tools = build_openai_tools()
        messages = list(state.get("chat_messages", []))
        logger.info(
            "ReAct agent round=%d messages=%d tools=%d",
            iteration,
            len(messages),
            len(tools),
        )

        try:
            decision = await provider.chat_with_tools(
                messages=messages,
                tools=tools,
                temperature=0.4,
                max_tokens=8192,
            )
        except asyncio.CancelledError:
            logger.info("ReAct agent LLM call cancelled at round %d", iteration)
            return {
                "iteration": iteration,
                "tool_calls": [],
                "should_end": True,
                "cancelled": True,
                "status": "cancelled",
                "error": "任务已取消",
            }
        except Exception as exc:
            logger.exception("ReAct agent LLM call failed at round %d", iteration)
            return {
                "iteration": iteration,
                "tool_calls": [],
                "should_end": True,
                "status": "failed",
                "error": f"LLM 调用失败：{exc}",
            }

        if decision.get("type") == "tool_calls":
            calls = [call for call in decision.get("calls", []) if call.get("function")]
            if calls:
                assistant: dict[str, Any] = {
                    "role": "assistant",
                    "content": decision.get("content") or "",
                    "tool_calls": _assistant_wire_tool_calls(calls),
                }
                tool_names = [str(call["function"]["name"]) for call in calls]
                logger.info(
                    "ReAct agent requested tools at round=%d: %s",
                    iteration,
                    ",".join(tool_names),
                )
                return {
                    "chat_messages": [assistant],
                    "tool_calls": calls,
                    "iteration": iteration,
                    "status": "calling_tools",
                    "error": "",
                }

        content = str(decision.get("content", "")).strip()
        if not state.get("outline_planned"):
            logger.info(
                "ReAct agent returned text before outline planning at round=%d",
                iteration,
            )
            reminder = (
                "第一步尚未完成。请先用 create_plot_node 把用户请求拆解成剧情大纲，"
                "至少创建一个包含 title、summary 和 detailed_outline 的剧情节点。"
            )
            return {
                "chat_messages": [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": reminder},
                ],
                "tool_calls": [],
                "iteration": iteration,
                "status": "awaiting_outline",
                "error": "",
            }

        if state.get("task_saved") and not state.get("outline_complete"):
            logger.info(
                "ReAct agent returned text before outline completion at round=%d",
                iteration,
            )
            reminder = (
                "当前剧情大纲尚未完成。请继续使用 get_writing_context 定位剧情游标，"
                "生成当前节点正文后调用 create_chapter，再调用 complete_current_plot_node。"
            )
            return {
                "chat_messages": [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": reminder},
                ],
                "tool_calls": [],
                "iteration": iteration,
                "status": "awaiting_tool_call",
                "error": "",
            }

        logger.info("ReAct agent produced final text at round=%d", iteration)
        return {
            "chat_messages": [{"role": "assistant", "content": content}],
            "tool_calls": [],
            "iteration": iteration,
            "final_response": content,
            "should_end": True,
            "status": "finalizing",
            "error": "",
        }

    return agent_node


def _novel_id_from_result(result: dict[str, Any], current: str) -> str:
    data = result.get("data")
    return str(data.get("id") or current) if isinstance(data, dict) else current


async def tool_node(state: ReactAgentState) -> dict[str, Any]:
    """Execute requested backend tools and append observations for the LLM."""

    calls = list(state.get("tool_calls", []))
    if not calls:
        return {"tool_calls": [], "status": "planning"}

    generation_id = str(state.get("generation_id", ""))
    if generation_id and cancellation.is_cancelled(generation_id):
        logger.info("ReAct tool node skipped cancelled calls")
        return {
            "tool_calls": [],
            "should_end": True,
            "cancelled": True,
            "status": "cancelled",
            "error": "任务已取消",
        }

    observations = await execute_tool_calls(calls)
    tool_messages: list[dict[str, Any]] = []
    previous_observations = list(state.get("observations", []))
    previous_observations.extend(observations)

    saved_chapters = list(state.get("saved_chapters", []))
    tools_used = list(state.get("tools_used", []))
    novel_id = str(state.get("novel_id", ""))
    task_saved = bool(state.get("task_saved"))
    cursor_position = int(state.get("cursor_position", 0))
    outline_nodes_count = int(state.get("outline_nodes_count", 0))
    outline_planned = bool(state.get("outline_planned"))
    outline_complete = bool(state.get("outline_complete"))
    errors: list[str] = []

    for observation in observations:
        tool_name = str(observation.get("tool_name", ""))
        result = observation.get("result", {})
        if tool_name not in tools_used:
            tools_used.append(tool_name)

        if result.get("success") is False:
            error_text = str(result.get("error", "工具调用失败"))
            errors.append(f"{tool_name}: {error_text}")
        else:
            if tool_name == "create_novel":
                novel_id = _novel_id_from_result(result, novel_id)
            elif tool_name == "create_plot_node":
                outline_planned = True
                outline_nodes_count += 1
            elif tool_name == "get_writing_context" and isinstance(
                result.get("data"), dict
            ):
                context = result["data"]
                cursor_position = int(
                    context.get("cursor_position", cursor_position)
                )
                outline_nodes_count = int(
                    context.get("outline_nodes_count", outline_nodes_count)
                )
                outline_planned = bool(context.get("outline_nodes_count"))
                outline_complete = bool(context.get("outline_complete", False))
            elif tool_name == "create_chapter" and isinstance(result.get("data"), dict):
                chapter = result["data"]
                saved_chapters.append(chapter)
                novel_id = str(chapter.get("novel_id") or novel_id)
                task_saved = True
            elif tool_name == "complete_current_plot_node" and isinstance(
                result.get("data"), dict
            ):
                completion = result["data"]
                novel_data = completion.get("novel", {})
                novel_id = str(novel_data.get("id") or novel_id)
                cursor_position = int(
                    completion.get("cursor_position", cursor_position)
                )
                outline_nodes_count = int(
                    completion.get("outline_nodes_count", outline_nodes_count)
                )
                outline_complete = bool(completion.get("outline_complete", False))
                if outline_complete:
                    logger.info(
                        "ReAct outline complete: novel_id=%s cursor=%d",
                        novel_id,
                        cursor_position,
                    )

        tool_messages.append(
            {
                "role": "tool",
                "tool_call_id": str(observation.get("tool_call_id", "")),
                "content": json.dumps(result, ensure_ascii=False, default=str),
            }
        )

    logger.info(
        "ReAct tool node completed: calls=%d success=%d saved_chapters=%d",
        len(observations),
        sum(1 for item in observations if item.get("result", {}).get("success")),
        len(saved_chapters),
    )

    update: dict[str, Any] = {
        "chat_messages": tool_messages,
        "tool_calls": [],
        "observations": previous_observations,
        "tools_used": tools_used,
        "novel_id": novel_id,
        "saved_chapters": saved_chapters,
        "task_saved": task_saved,
        "cursor_position": cursor_position,
        "outline_nodes_count": outline_nodes_count,
        "outline_planned": outline_planned,
        "outline_complete": outline_complete,
        "status": "observing",
    }
    iteration = int(state.get("iteration", 0))
    max_iterations = max(
        1,
        int(state.get("max_iterations") or DEFAULT_MAX_REACT_ITERATIONS),
    )
    if iteration >= max_iterations and not task_saved:
        update["should_end"] = True
        update["status"] = "failed"
        update["error"] = f"已达最大循环轮次（{max_iterations}）"
    if errors:
        update["error"] = "; ".join(errors)
    if outline_complete:
        update["final_response"] = "小说已按大纲完成并保存。"
        update["should_end"] = True
    return update


async def finalize_node(state: ReactAgentState) -> dict[str, Any]:
    """Build a stable result and preserve unsaved text with a fallback save."""

    chapters = list(state.get("saved_chapters", []))
    novel_id = str(state.get("novel_id", ""))
    error = str(state.get("error", ""))
    final_response = str(state.get("final_response", "")).strip()

    if not chapters and final_response and novel_id:
        request = str(state.get("user_request", "")).strip()
        try:
            fallback = await create_chapter(
                novel_id=novel_id,
                title="第一章 未命名",
                content=final_response,
                generation_id=str(state.get("generation_id", "")),
            )
            if fallback.get("success"):
                chapter = fallback["data"]
                chapters.append(chapter)
                logger.warning(
                    "ReAct fallback saved final assistant text as chapter %s",
                    chapter.get("id"),
                )
            else:
                error = error or str(fallback.get("error", "兜底保存失败"))
        except Exception as exc:
            logger.exception("ReAct fallback chapter save failed")
            error = error or f"兜底保存失败：{exc}"

    if not chapters and not error:
        error = "任务结束，但没有生成可保存的小说正文"

    status = str(state.get("status", "completed"))
    if state.get("cancelled"):
        status = "cancelled"
    elif not chapters:
        status = "failed"
    elif not state.get("outline_complete"):
        status = "partial"
    else:
        status = "completed"

    result = {
        "novel_id": novel_id,
        "chapters": chapters,
        "chapter_ids": [str(chapter.get("id")) for chapter in chapters],
        "text": "\n\n".join(str(chapter.get("content", "")) for chapter in chapters),
        "final_response": final_response,
        "tools_used": list(state.get("tools_used", [])),
        "iterations": int(state.get("iteration", 0)),
        "cursor_position": int(state.get("cursor_position", 0)),
        "outline_nodes_count": int(state.get("outline_nodes_count", 0)),
        "outline_planned": bool(state.get("outline_planned")),
        "outline_complete": bool(state.get("outline_complete")),
        "status": status,
        "error": error,
    }
    logger.info(
        "ReAct agent finalized: status=%s novel_id=%s chapters=%d rounds=%d",
        status,
        novel_id,
        len(chapters),
        result["iterations"],
    )
    return {"result": result, "status": status, "error": error, "should_end": True}
