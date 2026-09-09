"""Backend tool execution node for the ReAct loop."""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.agent import cancellation
from backend.config import (
    REACT_AGENT_PREVIOUS_TAIL_CHARS,
    REACT_AGENT_TOOL_RESULT_MAX_FIELD_CHARS,
)
from backend.react_agent.state import DEFAULT_MAX_REACT_ITERATIONS, ReactAgentState
from backend.react_agent.tools.registry import execute_tool_calls

logger = logging.getLogger(__name__)


def _novel_id_from_result(result: dict[str, Any], current: str) -> str:
    data = result.get("data")
    return str(data.get("id") or current) if isinstance(data, dict) else current


def _compact_value(value: Any, max_chars: int) -> Any:
    """Recursively truncate long string fields for the LLM context."""

    if isinstance(value, str) and len(value) > max_chars:
        return value[:max_chars] + f"…[已存入数据库，共{len(value)}字]"
    if isinstance(value, dict):
        return {key: _compact_value(item, max_chars) for key, item in value.items()}
    if isinstance(value, list):
        return [_compact_value(item, max_chars) for item in value]
    return value


def _compact_tool_result(result: dict[str, Any]) -> dict[str, Any]:
    """Return a compact copy of a tool result for the LLM chat history."""

    max_chars = REACT_AGENT_TOOL_RESULT_MAX_FIELD_CHARS
    return {key: _compact_value(value, max_chars) for key, value in result.items()}


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
    previous_chapter_tail = str(state.get("previous_chapter_tail", ""))
    errors: list[str] = []

    for observation in observations:
        tool_name = str(observation.get("tool_name", ""))
        result = observation.get("result", {})
        if tool_name not in tools_used:
            tools_used.append(tool_name)

        if result.get("success") is False:
            error_text = str(result.get("error", "工具调用失败"))
            errors.append(f"{tool_name}: {error_text}")
        elif tool_name == "create_novel":
            novel_id = _novel_id_from_result(result, novel_id)
        elif tool_name == "create_plot_node":
            outline_planned = True
            outline_nodes_count += 1
        elif tool_name == "get_writing_context" and isinstance(
            result.get("data"),
            dict,
        ):
            context = result["data"]
            cursor_position = int(context.get("cursor_position", cursor_position))
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
            content = str(chapter.get("content", ""))
            tail_chars = REACT_AGENT_PREVIOUS_TAIL_CHARS
            previous_chapter_tail = content[-tail_chars:] if content else ""
        elif tool_name == "complete_current_plot_node" and isinstance(
            result.get("data"),
            dict,
        ):
            completion = result["data"]
            novel_data = completion.get("novel", {})
            novel_id = str(novel_data.get("id") or novel_id)
            cursor_position = int(completion.get("cursor_position", cursor_position))
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
                "content": json.dumps(
                    _compact_tool_result(result),
                    ensure_ascii=False,
                    default=str,
                ),
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
        "previous_chapter_tail": previous_chapter_tail,
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
