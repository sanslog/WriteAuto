"""Generation API routes - SSE-based streaming generation."""

import json as _json_mod
import logging
import sys
import uuid
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langgraph.types import Command

from backend.db.models import GenerationRunRequest, JudgeRequest
from backend.db.database import Database
from backend.db.repos import (
    NovelRepo, PlotNodeRepo, ChapterRepo, CharacterRepo, ForeshadowRepo,
)
from backend.agent import cancellation
from backend.config import RUN_DIRECT

logger = logging.getLogger(__name__)

if not RUN_DIRECT:
    try:
        _log_dir = Path(sys.executable).parent / "data"
        _log_dir.mkdir(parents=True, exist_ok=True)
        _fh = logging.FileHandler(_log_dir / "generation.log", encoding="utf-8")
        _fh.setLevel(logging.DEBUG)
        _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(_fh)
        _uvicorn_logger = logging.getLogger("uvicorn")
        _uvicorn_logger.addHandler(_fh)
        logger.info("File logger initialised: %s", _log_dir / "generation.log")
    except Exception as _e:
        logger.warning("Failed to init file logger: %s", _e)

router = APIRouter(prefix="/api", tags=["generation"])
_sessions: dict[str, "AgentSession"] = {}
PUBLIC_STATE_KEYS = {"generated_text", "chapter_titles", "character_states_json", "modification_count"}


class AgentSession:
    def __init__(self, novel_id: str, gen_id: str):
        self.generation_id = gen_id
        self.novel_id = novel_id
        self.step = "init"
        self.state: dict = {}
        self.interrupt_data: dict = {}
        self.error: str | None = None

    def to_dict(self) -> dict:
        public_state = {k: v for k, v in self.state.items() if k in PUBLIC_STATE_KEYS}
        if self.interrupt_data:
            public_state.update(self.interrupt_data)
        return {"generation_id": self.generation_id, "step": self.step, "error": self.error, "state": public_state}

    def set_step(self, step: str) -> None:
        self.step = step
    def set_state(self, state: dict) -> None:
        self.state = state
    def set_interrupt(self, data: dict) -> None:
        self.step = "waiting_input"
        self.interrupt_data = data
    def set_error(self, error: str) -> None:
        self.step = "failed"
        self.error = error
    def cancel(self) -> None:
        self.step = "failed"
        self.error = "User cancelled generation"


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {_json_mod.dumps(data, ensure_ascii=False)}\n\n"


def _get_interrupt_value(state_snapshot, node_name: str) -> dict | None:
    if not state_snapshot or not state_snapshot.tasks:
        return None
    for task in state_snapshot.tasks:
        if task.name == node_name and task.interrupts:
            val = task.interrupts[0].value
            return dict(val) if val else {}
    if state_snapshot.next and node_name in state_snapshot.next:
        return {}
    return None


async def _interrupt_loop(gen_id: str, config: dict, session: AgentSession):
    from backend.agent.graph import continue_writing_graph
    from backend.config import LLM_GENERATION_MAX_TOKENS
    from backend.llm.factory import create_llm_provider

    while True:
        current_state = continue_writing_graph.get_state(config)
        gen_req = _get_interrupt_value(current_state, "content_generation")
        if gen_req and gen_req.get("type") == "generation_request":
            yield _format_sse("generation_start", {})
            llm = create_llm_provider()
            full_text = ""
            async for chunk in llm.chat_stream(
                [{"role": "system", "content": gen_req["system"]}, {"role": "user", "content": gen_req["user"]}],
                temperature=0.8, max_tokens=LLM_GENERATION_MAX_TOKENS,
            ):
                if cancellation.is_cancelled(gen_id):
                    break
                full_text += chunk
                yield _format_sse("token", {"token": chunk})
            yield _format_sse("generation_done", {})
            continue_writing_graph.update_state(config, {"generated_text": full_text}, as_node="content_generation")
            continue

        judgment = _get_interrupt_value(current_state, "content_judge")
        if judgment and judgment.get("type") == "judgment":
            session.set_interrupt(judgment)
            yield _format_sse("judgment", judgment)
            return

        if current_state.next:
            async for event in continue_writing_graph.astream(None, config, stream_mode="updates"):
                for _node_name, output in event.items():
                    if isinstance(output, dict):
                        session.state.update(output)
            continue
        break

    session.set_step("complete")
    yield _format_sse("complete", {"message": "Generation finished"})


async def prepare_generation(novel_id: str) -> dict:
    from backend.config import DB_PATH
    db = Database(DB_PATH)
    await db.init()
    try:
        novel_repo = NovelRepo(db)
        plot_repo = PlotNodeRepo(db)
        char_repo = CharacterRepo(db)
        ff_repo = ForeshadowRepo(db)
        chapter_repo = ChapterRepo(db)

        novel = await novel_repo.get(novel_id)
        if not novel:
            return {"success": False, "error": "Novel not found"}

        gen_id = str(uuid.uuid4())
        nodes = await plot_repo.get_by_novel(novel_id)
        cursor = novel.get("cursor_position", 0)
        characters = await char_repo.get_by_novel(novel_id)
        foreshadows = await ff_repo.get_by_novel(novel_id)
        approved_chapters = await chapter_repo.get_by_status(novel_id, "approved")

        outline_lines = []
        detailed_outline = ""
        next_node_title = ""
        for i, node in enumerate(nodes):
            outline_lines.append(f"{i+1}. {node['title']}: {node.get('summary', '') or 'N/A'}")
            if i == cursor:
                detailed_outline = node.get("detailed_outline", "")
            if i == cursor + 1:
                next_node_title = node.get("title", "")

        if cursor >= len(nodes) and nodes:
            cursor = len(nodes) - 1
            await novel_repo.update(novel_id, {"cursor_position": cursor})
            detailed_outline = nodes[cursor].get("detailed_outline", "")

        return {
            "success": True,
            "data": {
                "generation_id": gen_id, "novel_id": novel_id,
                "outline": "\n".join(outline_lines),
                "detailed_outline": detailed_outline, "cursor_position": cursor,
                "plot_nodes_count": len(nodes), "next_node_title": next_node_title,
                "characters": characters, "foreshadows": foreshadows,
                "approved_chapters": approved_chapters,
            },
        }
    finally:
        await db.close()


@router.post("/novels/{novel_id}/generate/prepare")
async def prepare_and_store(novel_id: str):
    try:
        result = await prepare_generation(novel_id)
    except Exception as e:
        logger.exception("prepare_and_store failed (novel_id=%s): %s", novel_id, e)
        return {"success": False, "error": f"Internal error: {e}"}
    if result.get("success") and "data" in result:
        data = result["data"]
        gen_id = data["generation_id"]
        session = AgentSession(novel_id=novel_id, gen_id=gen_id)
        _sessions[gen_id] = session
        logger.info("Created generation session gen_id=%s novel_id=%s", gen_id, novel_id)
    return result


@router.post("/novels/{novel_id}/generate")
async def run_generation(novel_id: str, body: GenerationRunRequest):
    gen_id = str(uuid.uuid4())
    session = AgentSession(novel_id=novel_id, gen_id=gen_id)
    _sessions[gen_id] = session
    config = {"configurable": {"thread_id": gen_id}}

    initial_state = {
        "novel_id": novel_id, "generation_id": gen_id,
        "chapter_ids": body.chapter_ids, "foreshadow_ids": body.foreshadow_ids,
        "base_prompt": "", "style_of_writing": "", "world_outlook": "",
        "outline": "", "detailed_outline": "", "cursor_position": 0,
        "plot_nodes_count": 0, "next_node_title": "", "main_character_design": "",
        "foreshadow": "", "context": "", "generated_text": "", "chapter_titles": [],
        "character_states_json": "", "_saved_chapters": [], "_cancelled": False,
    }

    async def event_stream():
        from backend.agent.graph import continue_writing_graph
        cancellation.register(gen_id)
        try:
            session.set_step("generating")
            async for event in continue_writing_graph.astream(initial_state, config, stream_mode="updates"):
                for _node_name, output in event.items():
                    if isinstance(output, dict):
                        session.state.update(output)
            async for sse_event in _interrupt_loop(gen_id, config, session):
                yield sse_event
        except Exception as e:
            logger.exception("run_generation SSE error for %s", gen_id)
            if not cancellation.is_cancelled(gen_id):
                session.set_error(str(e))
                yield _format_sse("error", {"error": str(e)})
        finally:
            cancellation.unregister(gen_id)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/generations/{gen_id}/judge")
async def submit_judgment(gen_id: str, body: JudgeRequest):
    session = _sessions.get(gen_id)
    if not session:
        return {"success": False, "error": "Generation not found"}
    config = {"configurable": {"thread_id": gen_id}}
    judgment_payload = {"action": body.action, "text": body.text}

    async def judge_event_stream():
        from backend.agent.graph import continue_writing_graph
        cancellation.register(gen_id)
        try:
            session.set_step("generating")
            async for event in continue_writing_graph.astream(Command(resume=judgment_payload), config, stream_mode="updates"):
                for _node_name, output in event.items():
                    if isinstance(output, dict):
                        session.state.update(output)
            async for sse_event in _interrupt_loop(gen_id, config, session):
                yield sse_event
        except Exception as e:
            logger.exception("submit_judgment SSE error for %s", gen_id)
            if not cancellation.is_cancelled(gen_id):
                session.set_error(str(e))
                yield _format_sse("error", {"error": str(e)})
        finally:
            cancellation.unregister(gen_id)

    return StreamingResponse(judge_event_stream(), media_type="text/event-stream")


@router.post("/generations/{gen_id}/cancel")
async def cancel_generation(gen_id: str):
    session = _sessions.get(gen_id)
    if not session:
        return {"success": False, "error": "Generation not found"}
    cancellation.cancel(gen_id)
    session.cancel()
    logger.info("Generation %s cancelled via API", gen_id)
    return {"success": True}


@router.get("/generations/{gen_id}/status")
async def get_generation_status(gen_id: str):
    session = _sessions.get(gen_id)
    if not session:
        return {"success": False, "error": "Generation not found"}
    return {"success": True, **session.to_dict()}
