"""LLM reasoning node for the ReAct loop."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from backend.agent import cancellation
from backend.config import (
    REACT_AGENT_CONTEXT_CHAR_LIMIT,
    REACT_AGENT_CONTEXT_MESSAGE_WINDOW,
)
from backend.llm.provider import LLMProvider
from backend.react_agent.nodes.context_window import apply_chat_message_window
from backend.react_agent.prompts import (
    build_react_progress_hint,
    build_react_state_digest,
    build_react_system_prompt,
    build_react_user_prompt,
)
from backend.react_agent.state import DEFAULT_MAX_REACT_ITERATIONS, ReactAgentState
from backend.react_agent.tools.registry import build_openai_tools

logger = logging.getLogger(__name__)


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
        messages = apply_chat_message_window(
            state.get("chat_messages", []),
            max_messages=REACT_AGENT_CONTEXT_MESSAGE_WINDOW,
            max_chars=REACT_AGENT_CONTEXT_CHAR_LIMIT,
        )
        digest = build_react_state_digest(
            novel_id=str(state.get("novel_id", "")),
            cursor_position=int(state.get("cursor_position", 0)),
            outline_nodes_count=int(state.get("outline_nodes_count", 0)),
            outline_planned=bool(state.get("outline_planned")),
            outline_complete=bool(state.get("outline_complete")),
            task_saved=bool(state.get("task_saved")),
            previous_chapter_tail=str(state.get("previous_chapter_tail", "")),
        )
        if digest:
            messages.append({"role": "user", "content": digest})
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
            reminder = build_react_progress_hint(outline_planned=False)
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
            reminder = build_react_progress_hint(
                outline_planned=True,
                outline_complete=False,
                task_saved=True,
                cursor_position=int(state.get("cursor_position", 0)),
                outline_nodes_count=int(state.get("outline_nodes_count", 0)),
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
