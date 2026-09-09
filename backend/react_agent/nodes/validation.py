"""Input preparation node for the ReAct loop."""

from __future__ import annotations

import logging
from typing import Any

from backend.react_agent.prompts import (
    build_react_system_prompt,
    build_react_user_prompt,
)
from backend.react_agent.state import DEFAULT_MAX_REACT_ITERATIONS, ReactAgentState

logger = logging.getLogger(__name__)


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
            "content": build_react_user_prompt(
                request,
                str(state.get("novel_id", "")),
                cursor_position=int(state.get("cursor_position", 0)),
                outline_nodes_count=int(state.get("outline_nodes_count", 0)),
                outline_planned=bool(state.get("outline_planned", False)),
                outline_complete=bool(state.get("outline_complete", False)),
                task_saved=bool(state.get("task_saved", False)),
            ),
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
