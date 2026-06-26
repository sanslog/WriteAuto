import threading
import uuid
from typing import Any

from fastapi import APIRouter
from langgraph.types import Command

from backend.db.models import (
    GenerationRunRequest,
    JudgeRequest,
)

router = APIRouter(prefix="/api", tags=["generation"])

# In-memory session store
_sessions: dict[str, "AgentSession"] = {}
_session_lock = threading.Lock()

PUBLIC_STATE_KEYS = {
    "generated_text", "chapter_titles", "character_states_json",
    "modification_count",
}


class AgentSession:
    def __init__(self, novel_id: str, gen_id: str):
        self.generation_id = gen_id
        self.novel_id = novel_id
        self.step = "init"  # init | generating | waiting_input | complete | failed
        self.state: dict[str, Any] = {}
        self.interrupt_data: dict[str, Any] = {}
        self.error: str | None = None
        self._lock = threading.Lock()

    def to_dict(self) -> dict:
        with self._lock:
            public_state = {
                k: v for k, v in self.state.items() if k in PUBLIC_STATE_KEYS
            }
            if self.interrupt_data:
                public_state.update(self.interrupt_data)
            return {
                "generation_id": self.generation_id,
                "step": self.step,
                "error": self.error,
                "state": public_state,
            }

    def set_step(self, step: str):
        with self._lock:
            self.step = step

    def set_state(self, state: dict):
        with self._lock:
            self.state = state

    def set_interrupt(self, data: dict):
        with self._lock:
            self.step = "waiting_input"
            self.interrupt_data = data

    def set_error(self, error: str):
        with self._lock:
            self.step = "failed"
            self.error = error

    def cancel(self):
        """Mark the session as cancelled — stops frontend polling from showing generating state."""
        with self._lock:
            self.step = "failed"
            self.error = "用户取消生成"


@router.post("/novels/{novel_id}/generate")
async def prepare_generation(novel_id: str):
    from backend.db.database import Database
    from backend.config import DB_PATH
    from backend.services.cursor import get_cursor_info

    gen_id = str(uuid.uuid4())

    db = Database(DB_PATH)
    await db.init()
    try:
        novel = await db.get_novel(novel_id)
        if not novel:
            return {"success": False, "error": "Novel not found"}

        cursor_info = await get_cursor_info(db, novel_id)
        characters = await db.get_characters(novel_id)
        foreshadows = await db.get_foreshadows(novel_id)
        chapters = await db.get_chapters_by_status(novel_id, "approved")
        approved_chapters = [{
            "id": ch["id"],
            "title": ch.get("title", ""),
            "word_count": ch.get("word_count", 0),
        } for ch in chapters]

        return {
            "success": True,
            "data": {
                "generation_id": gen_id,
                "novel_id": novel_id,
                "outline": cursor_info.get("outline", ""),
                "detailed_outline": cursor_info.get("detailed_outline", ""),
                "cursor_position": cursor_info.get("cursor_position", 0),
                "plot_nodes_count": cursor_info.get("plot_nodes_count", 0),
                "next_node_title": cursor_info.get("next_node_title", ""),
                "characters": characters,
                "foreshadows": foreshadows,
                "approved_chapters": approved_chapters,
            },
        }
    finally:
        await db.close()


@router.post("/generations/{gen_id}/run")
async def run_generation(gen_id: str, body: GenerationRunRequest):
    session = _sessions.get(gen_id)
    if not session:
        return {"success": False, "error": "Generation not prepared. Call prepare first."}

    session.set_step("generating")

    config = {"configurable": {"thread_id": gen_id}}
    initial_state = {
        "novel_id": session.novel_id,
        "generation_id": gen_id,
        "chapter_ids": body.chapter_ids,
        "foreshadow_ids": body.foreshadow_ids,
        "enter_loop": False,
        "should_end": False,
        "modification_count": 0,
        "user_input_text": "",
        "unlawful": False,
        "unlaw_reason": "",
        "messages": [],
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
        "generated_text": "",
        "chapter_titles": [],
        "character_states_json": "",
        "_saved_chapters": [],
    }

    def _detect_interrupt(session, state_snapshot) -> bool:
        """Check if the graph is paused at content_judge due to interrupt.

        langgraph v1.2.5: after interrupt(), .next is empty (graph is waiting),
        so we must check .tasks for pending interrupts instead.
        """
        if not state_snapshot or not state_snapshot.values:
            return False

        state_dict = dict(state_snapshot.values)

        # Method 1: check tasks (langgraph v1.2.5+ — reliable)
        if state_snapshot.tasks:
            for task in state_snapshot.tasks:
                if task.name == "content_judge" and task.interrupts:
                    session.set_state(state_dict)
                    # Use the interrupt payload if available, else build from state
                    interrupt_val = task.interrupts[0].value if task.interrupts[0].value else {}
                    session.set_interrupt({
                        "type": "judgment",
                        "generated_text": interrupt_val.get("generated_text", state_dict.get("generated_text", "")),
                        "chapter_titles": interrupt_val.get("chapter_titles", state_dict.get("chapter_titles", [])),
                        "character_states_json": interrupt_val.get("character_states_json", state_dict.get("character_states_json", "")),
                        "modification_count": interrupt_val.get("modification_count", state_dict.get("modification_count", 0)),
                    })
                    return True

        # Method 2: check .next (langgraph < 1.0 / older v1 compat)
        if state_snapshot.next and "content_judge" in state_snapshot.next:
            session.set_state(state_dict)
            session.set_interrupt({
                "type": "judgment",
                "generated_text": state_dict.get("generated_text", ""),
                "chapter_titles": state_dict.get("chapter_titles", []),
                "character_states_json": state_dict.get("character_states_json", ""),
                "modification_count": state_dict.get("modification_count", 0),
            })
            return True

        return False

    def _run():
        from backend.agent.graph import continue_writing_graph
        try:
            for event in continue_writing_graph.stream(
                initial_state, config=config, stream_mode="updates"
            ):
                # Merge events from stream_mode="updates" ({node: output}) into flat state
                for _node_name, output in event.items():
                    if isinstance(output, dict):
                        session.set_state({**session.state, **output})
                session.set_step("generating")

            # After streaming, check where we are
            current_state = continue_writing_graph.get_state(config)
            if _detect_interrupt(session, current_state):
                return

            if current_state and current_state.values:
                state_dict = dict(current_state.values)
                session.set_state(state_dict)

                if state_dict.get("should_end"):
                    session.set_step("complete")
                else:
                    session.set_step("generating")
            else:
                session.set_step("complete")

        except Exception as e:
            error_msg = str(e)
            if "GraphInterrupt" in error_msg or "interrupt" in error_msg.lower():
                # langgraph < 1.0 fallback: interrupt throws
                try:
                    current_state = continue_writing_graph.get_state(config)
                    _detect_interrupt(session, current_state)
                except Exception:
                    pass
            else:
                session.set_error(error_msg)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {"success": True, "generation_id": gen_id, "status": "generating"}


@router.get("/generations/{gen_id}/status")
async def get_generation_status(gen_id: str):
    session = _sessions.get(gen_id)
    if not session:
        return {"success": False, "error": "Generation not found"}
    return {"success": True, **session.to_dict()}


@router.post("/generations/{gen_id}/judge")
async def submit_judgment(gen_id: str, body: JudgeRequest):
    session = _sessions.get(gen_id)
    if not session:
        return {"success": False, "error": "Generation not found"}

    config = {"configurable": {"thread_id": gen_id}}
    judgment = {"action": body.action, "text": body.text}

    def _resume():
        from backend.agent.graph import continue_writing_graph
        try:
            # Use stream() instead of invoke() for consistency with _run().
            # stream() yields updates for each node execution after resume.
            # After it completes, we check get_state() for the final state.
            for event in continue_writing_graph.stream(
                Command(resume=judgment), config=config, stream_mode="updates"
            ):
                for _node_name, output in event.items():
                    if isinstance(output, dict):
                        session.set_state({**session.state, **output})

            # After resume stream completes, read authoritative state from checkpointer
            current_state = continue_writing_graph.get_state(config)
            if _detect_interrupt(session, current_state):
                return

            if current_state and current_state.values:
                state_dict = dict(current_state.values)
                session.set_state(state_dict)

                if state_dict.get("should_end"):
                    session.set_step("complete")
                elif not current_state.next:
                    # Graph reached END (no pending nodes) → treat as complete
                    session.set_step("complete")
                else:
                    session.set_step("generating")
            else:
                session.set_step("complete")

        except Exception as e:
            error_msg = str(e)
            if "GraphInterrupt" in error_msg or "interrupt" in error_msg.lower():
                try:
                    current_state = continue_writing_graph.get_state(config)
                    if not _detect_interrupt(session, current_state):
                        # Graph said it was interrupted but no interrupt in state
                        # — best-effort: treat as complete to avoid infinite polling
                        session.set_step("complete")
                except Exception:
                    session.set_step("complete")
                return

            session.set_error(error_msg)

    thread = threading.Thread(target=_resume, daemon=True)
    thread.start()

    session.set_step("generating")
    return {"success": True, "generation_id": gen_id, "status": "processing"}


@router.post("/generations/{gen_id}/cancel")
async def cancel_generation(gen_id: str):
    """Cancel a generation session — marks it as failed so frontend stops polling."""
    session = _sessions.get(gen_id)
    if not session:
        return {"success": False, "error": "Generation not found"}
    session.cancel()
    return {"success": True}


@router.post("/novels/{novel_id}/generate/prepare")
async def prepare_and_store(novel_id: str):
    """Combined prepare + session creation endpoint for convenience."""
    result = await prepare_generation(novel_id)
    if result.get("success") and "data" in result:
        data = result["data"]
        gen_id = data["generation_id"]
        session = AgentSession(novel_id=novel_id, gen_id=gen_id)
        with _session_lock:
            _sessions[gen_id] = session
    return result
