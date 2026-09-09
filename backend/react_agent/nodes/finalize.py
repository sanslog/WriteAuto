"""Final result node for the ReAct loop."""

from __future__ import annotations

import logging
from typing import Any

from backend.react_agent.state import ReactAgentState
from backend.react_agent.tools.chapter import create_chapter

logger = logging.getLogger(__name__)


async def finalize_node(state: ReactAgentState) -> dict[str, Any]:
    """Build a stable result and preserve unsaved text with a fallback save."""

    chapters = list(state.get("saved_chapters", []))
    novel_id = str(state.get("novel_id", ""))
    error = str(state.get("error", ""))
    final_response = str(state.get("final_response", "")).strip()

    if not chapters and final_response and novel_id:
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
