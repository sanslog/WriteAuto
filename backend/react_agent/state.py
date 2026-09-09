"""State contract for the one-sentence novel-writing ReAct graph."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


DEFAULT_MAX_REACT_ITERATIONS = 128


class ReactAgentState(TypedDict, total=False):
    """Mutable data shared by the ReAct loop nodes.

    ``chat_messages`` follows the provider's OpenAI-compatible message format, so
    assistant tool-call turns and tool observations can be replayed directly.
    """

    session_id: str
    generation_id: str
    user_request: str
    novel_id: str

    chat_messages: Annotated[list[dict[str, Any]], operator.add]
    tool_calls: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    tools_used: list[str]

    iteration: int
    max_iterations: int
    should_end: bool
    status: str
    error: str
    cancelled: bool
    final_response: str

    task_saved: bool
    saved_chapters: list[dict[str, Any]]
    previous_chapter_tail: str
    result: dict[str, Any]

    cursor_position: int
    outline_nodes_count: int
    outline_planned: bool
    outline_complete: bool
