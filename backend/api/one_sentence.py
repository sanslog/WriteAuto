"""SSE endpoint for the one-sentence novel-writing agent."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.agent import cancellation
from backend.config import DB_PATH
from backend.db.database import Database
from backend.db.repos import ChapterRepo, NovelRepo, PlotNodeRepo
from backend.react_agent.graph import run_react_agent
from backend.react_agent.state import DEFAULT_MAX_REACT_ITERATIONS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/one-sentence", tags=["one-sentence"])
_sessions: dict[str, "OneSentenceSession"] = {}
_DISCONNECT_POLL_SECONDS = 0.5


class OneSentenceRunRequest(BaseModel):
    """User-facing payload for starting a one-sentence writing run."""

    user_request: str = Field(min_length=1, max_length=2000)
    novel_id: str = ""
    max_iterations: int = Field(
        default=DEFAULT_MAX_REACT_ITERATIONS,
        ge=1,
        le=DEFAULT_MAX_REACT_ITERATIONS,
    )


@dataclass
class OneSentenceSession:
    """Server-side view of one agent run for SSE and cancellation."""

    generation_id: str
    user_request: str
    status: str = "running"
    task: asyncio.Task[dict[str, Any]] | None = None
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""


def _format_sse(event: str, data: dict[str, Any]) -> str:
    return (
        f"event: {event}\n"
        f"data: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
    )


async def _load_snapshot(novel_id: str) -> dict[str, Any]:
    """Return lightweight public novel state after each graph update."""

    if not novel_id:
        return {}

    db = Database(DB_PATH)
    await db.init()
    try:
        novel = await NovelRepo(db).get(novel_id)
        if not novel:
            return {}

        nodes = await PlotNodeRepo(db).get_by_novel(novel_id)
        chapters = await ChapterRepo(db).get_by_novel(novel_id)

    finally:
        await db.close()

    cursor = min(max(int(novel.get("cursor_position", 0)), 0), max(len(nodes) - 1, 0))
    current_node = nodes[cursor] if nodes else None
    latest_chapter = chapters[-1] if chapters else None
    return {
        "novel_id": novel_id,
        "novel_title": novel.get("title", ""),
        "status": novel.get("is_done", 0),
        "iteration": 0,
        "outline_nodes_count": len(nodes),
        "outline_complete": bool(novel.get("is_done")),
        "chapter_count": len(chapters),
        "cursor_position": cursor,
        "current_plot_node": current_node,
        "latest_chapter": latest_chapter,
        "saved_chapter_titles": [chapter.get("title", "") for chapter in chapters],
    }


async def _make_progress(session: OneSentenceSession):
    """Build the callback handed to the disposable ReAct graph run."""

    node_labels = {
        "validate_input": "正在校验写作请求",
        "agent": "AI 正在推理",
        "tools": "正在执行写作工具",
        "finalize": "正在保存结果",
    }

    async def on_progress(node_name: str, output: dict[str, Any]) -> None:
        novel_id = str(output.get("novel_id", "") or session.result.get("novel_id", ""))
        snapshot = await _load_snapshot(novel_id)
        result = output.get("result", {}) if isinstance(output.get("result", {}), dict) else {}
        payload: dict[str, Any] = {
            "generation_id": session.generation_id,
            "node": node_name,
            "message": node_labels.get(node_name, node_name),
            "iteration": int(output.get("iteration", 0) or result.get("iterations", 0)),
            "tools_used": output.get("tools_used", result.get("tools_used", [])),
            "saved_chapters": output.get("saved_chapters", result.get("chapters", [])),
            **snapshot,
        }
        if output.get("status"):
            payload["run_status"] = output.get("status")
            session.status = str(output.get("status"))
        if output.get("error"):
            payload["error"] = output.get("error")
            session.error = str(output.get("error"))
        if result:
            session.result = result
            payload["result"] = result
        await session.queue.put({"event": "progress", "data": payload})

    return on_progress


def _register(session: OneSentenceSession) -> None:
    cancellation.register(session.generation_id)
    _sessions[session.generation_id] = session


def _unregister(session: OneSentenceSession) -> None:
    _sessions.pop(session.generation_id, None)
    cancellation.unregister(session.generation_id)


async def _finish_task(session: OneSentenceSession) -> None:
    if not session.task or session.task.done():
        return
    try:
        result = await session.task
        session.result = result
        session.status = str(result.get("status", "completed"))
        session.error = str(result.get("error", ""))
    except asyncio.CancelledError:
        session.status = "cancelled"
        session.error = "任务已取消"
        raise
    except Exception as exc:
        logger.exception("One-sentence agent run failed: %s", session.generation_id)
        session.status = "failed"
        session.error = str(exc)


@router.post("/run")
async def run_one_sentence(request: Request, body: OneSentenceRunRequest):
    generation_id = str(uuid.uuid4())
    session = OneSentenceSession(
        generation_id=generation_id,
        user_request=body.user_request,
    )
    _register(session)
    progress_callback = await _make_progress(session)
    session.task = asyncio.create_task(
        run_react_agent(
            body.user_request,
            session_id=generation_id,
            novel_id=body.novel_id,
            generation_id=generation_id,
            max_iterations=body.max_iterations,
            progress_callback=progress_callback,
        ),
        name=f"one-sentence-{generation_id}",
    )
    logger.info("One-sentence run started: generation_id=%s", generation_id)
    await session.queue.put({
        "event": "progress",
        "data": {
            "generation_id": generation_id,
            "node": "started",
            "message": "任务已启动",
            "iteration": 0,
            "outline_nodes_count": 0,
            "chapter_count": 0,
            "saved_chapters": [],
            "tools_used": [],
            "run_status": "planning",
        },
    })

    async def event_stream():
        try:
            while True:
                try:
                    item = await asyncio.wait_for(
                        session.queue.get(),
                        timeout=_DISCONNECT_POLL_SECONDS,
                    )
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        cancellation.cancel(generation_id)
                        logger.info("One-sentence client disconnected: %s", generation_id)
                        yield _format_sse("cancelled", {"generation_id": generation_id})
                        break
                    continue

                yield _format_sse(item["event"], item["data"])
                if item["data"].get("node") == "finalize":
                    break

            await _finish_task(session)
            if session.error:
                event = "cancelled" if session.status == "cancelled" else "error"
                yield _format_sse(event, {
                    "generation_id": generation_id,
                    "error": session.error,
                    "result": session.result,
                })
            else:
                yield _format_sse("complete", {
                    "generation_id": generation_id,
                    "status": session.status,
                    "result": session.result,
                })
        finally:
            cancellation.cancel(generation_id)
            await _finish_task(session)
            _unregister(session)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Generation-Id": generation_id,
        },
    )


@router.post("/{generation_id}/cancel")
async def cancel_one_sentence(generation_id: str):
    session = _sessions.get(generation_id)
    if not session:
        return {"success": False, "error": "Generation not found"}

    cancellation.cancel(generation_id)
    if session.task and not session.task.done():
        logger.info("One-sentence run cancelled via API: %s", generation_id)
    return {"success": True, "data": {"generation_id": generation_id, "cancelled": True}}


@router.get("/{generation_id}/status")
async def get_one_sentence_status(generation_id: str):
    session = _sessions.get(generation_id)
    if not session:
        return {"success": False, "error": "Generation not found"}
    return {
        "success": True,
        "data": {
            "generation_id": generation_id,
            "status": session.status,
            "error": session.error,
            "result": session.result,
        },
    }
