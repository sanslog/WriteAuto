import json
import logging
import sys
import uuid
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langgraph.types import Command

from backend.db.models import GenerationRunRequest, JudgeRequest

from backend.agent import cancellation
from backend.config import RUN_DIRECT

logger = logging.getLogger(__name__)

# ── 文件日志：打包后写入 DATA_DIR，确保能捕获到错误 ──
if not RUN_DIRECT:
    try:
        _log_dir = Path(sys.executable).parent / "data"
        _log_dir.mkdir(parents=True, exist_ok=True)
        _fh = logging.FileHandler(_log_dir / "generation.log", encoding="utf-8")
        _fh.setLevel(logging.DEBUG)
        _fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        logger.addHandler(_fh)
        # 也把 uvicorn 级别的日志写入同一文件
        _uvicorn_logger = logging.getLogger("uvicorn")
        _uvicorn_logger.addHandler(_fh)
        logger.info("文件日志已初始化: %s", _log_dir / "generation.log")
    except Exception as _e:
        # 如果写文件日志失败，不影响主流程
        logger.warning("初始化文件日志失败: %s", _e)

router = APIRouter(prefix="/api", tags=["generation"])

# In-memory session store
_sessions: dict[str, "AgentSession"] = {}

PUBLIC_STATE_KEYS = {
    "generated_text", "chapter_titles", "character_states_json",
    "modification_count",
}


class AgentSession:
    def __init__(self, novel_id: str, gen_id: str):
        self.generation_id = gen_id
        self.novel_id = novel_id
        self.step = "init"  # init | generating | waiting_input | complete | failed
        self.state: dict = {}
        self.interrupt_data: dict = {}
        self.error: str | None = None

    def to_dict(self) -> dict:
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
        self.step = step

    def set_state(self, state: dict):
        self.state = state

    def set_interrupt(self, data: dict):
        self.step = "waiting_input"
        self.interrupt_data = data

    def set_error(self, error: str):
        self.step = "failed"
        self.error = error

    def cancel(self):
        self.step = "failed"
        self.error = "用户取消生成"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_sse(event: str, data: dict) -> str:
    """Return a single SSE-formatted string."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_interrupt_value(state_snapshot, node_name: str) -> dict | None:
    """Return the interrupt payload for *node_name*, or None if not interrupted."""
    if not state_snapshot or not state_snapshot.tasks:
        return None
    for task in state_snapshot.tasks:
        if task.name == node_name and task.interrupts:
            val = task.interrupts[0].value
            return dict(val) if val else {}
    # v1.2.x fallback: check .next
    if state_snapshot.next and node_name in state_snapshot.next:
        return {}
    return None


async def _interrupt_loop(gen_id: str, config: dict, session: AgentSession):
    """Async generator that processes graph interrupts in a loop.

    Handles generation_request, judgment, and complete/terminal states.
    Yields SSE-formatted strings.  Caller must wrap in StreamingResponse.
    """
    from backend.agent.graph import continue_writing_graph
    from backend.config import LLM_GENERATION_MAX_TOKENS
    from backend.llm.factory import create_llm_provider

    while True:
        current_state = continue_writing_graph.get_state(config)

        # ── 1. generation_request → call LLM via streaming ──
        gen_req = _get_interrupt_value(current_state, "content_generation")
        if gen_req and gen_req.get("type") == "generation_request":
            yield _format_sse("generation_start", {})

            llm = create_llm_provider()
            full_text = ""
            async for chunk in llm.chat_stream(
                [
                    {"role": "system", "content": gen_req["system"]},
                    {"role": "user", "content": gen_req["user"]},
                ],
                temperature=0.8,
                max_tokens=LLM_GENERATION_MAX_TOKENS,
            ):
                # ── cancel check between every chunk ──
                if cancellation.is_cancelled(gen_id):
                    logger.info("Generation %s cancelled mid-stream", gen_id)
                    # Resume graph with cancelled signal; content_generation
                    # will return should_end → content_judge → END.
                    async for _ in continue_writing_graph.astream(Command(resume={"cancelled": True})):
                        pass
                    yield _format_sse("cancelled", {})
                    return

                full_text += chunk
                yield _format_sse("token", {"text": chunk})

            # Write generated text back into graph state and resume
            logger.info("Generation %s LLM complete (%d chars)", gen_id, len(full_text))
            async for event in continue_writing_graph.astream(
                Command(resume={"generated_text": full_text}), config, stream_mode="updates",
            ):
                for _node_name, output in event.items():
                    if isinstance(output, dict):
                        session.state.update(output)
            continue  # check the next interrupt

        # ── 2. judgment interrupt (graph paused at content_judge) ──
        judgment_val = _get_interrupt_value(current_state, "content_judge")
        if judgment_val:
            state_dict = dict(current_state.values) if current_state and current_state.values else {}
            session.set_state(state_dict)
            session.set_interrupt(judgment_val)
            yield _format_sse("judgment", session.interrupt_data)
            return

        # ── 3. Graph reached END — done ──
        if current_state and current_state.values:
            session.state.update(dict(current_state.values))
        session.set_step("complete")
        logger.info("Generation %s complete", gen_id)
        yield _format_sse("complete", {})
        return


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------


@router.post("/novels/{novel_id}/generate")
async def prepare_generation(novel_id: str):
    from backend.db.database import Database
    from backend.config import DB_PATH
    from backend.services.cursor import get_cursor_info

    gen_id = str(uuid.uuid4())

    try:
        db = Database(DB_PATH)
        await db.init()
    except Exception as e:
        logger.exception("数据库初始化失败 (DB_PATH=%s): %s", DB_PATH, e)
        return {"success": False, "error": f"数据库初始化失败: {e}"}

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
    except Exception as e:
        logger.exception("prepare_generation 失败 (novel_id=%s): %s", novel_id, e)
        return {"success": False, "error": f"生成准备失败: {e}"}
    finally:
        await db.close()


@router.post("/generations/{gen_id}/run")
async def run_generation(gen_id: str, body: GenerationRunRequest):
    """Start / resume generation via SSE streaming.

    The graph runs until it hits an interrupt:
      - content_generation (generation_request): API calls LLM, streams tokens,
        writes result back, resumes graph.
      - content_judge (judgment): the generated preview is sent to the frontend
        for human review.
    """
    session = _sessions.get(gen_id)
    if not session:
        return {"success": False, "error": "Generation not prepared. Call prepare first."}

    config = {"configurable": {"thread_id": gen_id}}

    # Build the initial state payload (same keys as before)
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
        "_cancelled": False,
    }

    async def event_stream():
        from backend.agent.graph import continue_writing_graph

        cancellation.register(gen_id)
        try:
            session.set_step("generating")

            # ── Phase 1: run graph from START until first interrupt ──
            async for event in continue_writing_graph.astream(
                initial_state, config, stream_mode="updates",
            ):
                for _node_name, output in event.items():
                    if isinstance(output, dict):
                        session.state.update(output)

            # ── Phase 2: enter the interrupt-handling loop ──
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
    """Submit human judgment (approve / modify / cancel) via SSE.

    - approve → graph runs to END.
    - modify → graph re-enters the generation loop; LLM is called again
      and tokens are streamed via SSE.
    """
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

            # ── Resume graph with the judgment payload ──
            async for event in continue_writing_graph.astream(
                Command(resume=judgment_payload), config, stream_mode="updates",
            ):
                for _node_name, output in event.items():
                    if isinstance(output, dict):
                        session.state.update(output)

            # ── Same interrupt loop (may hit another generation_request) ──
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
    """Cancel a running generation.

    Sets the cancellation Event so the SSE loop terminates at the next
    chunk boundary, then marks the session as failed.
    """
    session = _sessions.get(gen_id)
    if not session:
        return {"success": False, "error": "Generation not found"}

    cancellation.cancel(gen_id)
    session.cancel()
    logger.info("Generation %s cancelled via API", gen_id)
    return {"success": True}


@router.get("/generations/{gen_id}/status")
async def get_generation_status(gen_id: str):
    """Return the current session state (for debugging / backward compat)."""
    session = _sessions.get(gen_id)
    if not session:
        return {"success": False, "error": "Generation not found"}
    return {"success": True, **session.to_dict()}


@router.post("/novels/{novel_id}/generate/prepare")
async def prepare_and_store(novel_id: str):
    """Combined prepare + session creation."""
    try:
        result = await prepare_generation(novel_id)
    except Exception as e:
        logger.exception("prepare_and_store 内部崩溃 (novel_id=%s): %s", novel_id, e)
        return {"success": False, "error": f"服务内部错误: {e}"}
    if result.get("success") and "data" in result:
        data = result["data"]
        gen_id = data["generation_id"]
        session = AgentSession(novel_id=novel_id, gen_id=gen_id)
        _sessions[gen_id] = session
        logger.info(
            "已创建 generation session  gen_id=%s  novel_id=%s",
            gen_id, novel_id,
        )
    return result
