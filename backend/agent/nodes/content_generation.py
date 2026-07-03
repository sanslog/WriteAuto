import json
import logging
import re
import uuid

from langgraph.types import interrupt

from backend.agent.state import State
from backend.config import SPLIT_THRESHOLD_CHARS

logger = logging.getLogger(__name__)


def _count_chinese(text: str) -> int:
    return len(re.findall(r"[一-鿿]", text))


def _split_chapters(text: str) -> list[dict]:
    """Split generated text into chapters."""
    pattern = re.compile(r"^(第[一二三四五六七八九十百千\d]+章)\s*$")
    parts = pattern.split(text)

    chapters = []
    current_title = "续写"
    current_content = []

    for part in parts:
        if pattern.match(part):
            if current_content:
                body = "".join(current_content).strip()
                if body:
                    chapters.append({"title": current_title, "content": body})
                current_content = []
            current_title = part.strip()
        else:
            current_content.append(part)

    if current_content:
        body = "".join(current_content).strip()
        if body:
            chapters.append({"title": current_title, "content": body})

    # If no chapters found, treat as single chapter
    if not chapters:
        chapters = [{"title": "续写", "content": text.strip()}]

    # Split large chapters at paragraph boundaries
    result = []
    for ch in chapters:
        if len(ch["content"]) <= SPLIT_THRESHOLD_CHARS:
            result.append(ch)
        else:
            paragraphs = ch["content"].split("\n\n")
            buffer = ""
            buf_title = ch["title"]
            for para in paragraphs:
                if len(buffer) + len(para) > SPLIT_THRESHOLD_CHARS and buffer:
                    result.append({"title": buf_title, "content": buffer.strip()})
                    buffer = para
                    buf_title = ch["title"] + "（续）"
                else:
                    buffer = buffer + "\n\n" + para if buffer else para
            if buffer.strip():
                result.append({"title": buf_title, "content": buffer.strip()})

    return result


async def content_generation_node(state: State) -> dict:
    from backend.db.database import Database
    from backend.config import DB_PATH
    from backend.llm.prompts import build_generation_prompt
    from backend.services.style_extractor import extract_character_states
    from backend.storage.file_manager import FileManager

    # ── Quick exit on cancel ──
    if state.get("_cancelled"):
        return {"should_end": True}

    novel_id = state["novel_id"]
    generation_id = state["generation_id"]

    system, user = build_generation_prompt(
        base_prompt=state["base_prompt"],
        style_of_writing=state["style_of_writing"],
        world_outlook=state["world_outlook"],
        outline=state["outline"],
        detailed_outline=state["detailed_outline"],
        next_node_title=state["next_node_title"],
        main_character_design=state["main_character_design"],
        foreshadow=state["foreshadow"],
        context=state["context"],
        user_input_text=state.get("user_input_text", ""),
        enter_loop=state.get("enter_loop", False),
        previous_generated_text=state.get("generated_text", ""),
    )

    # ── Pause: hand prompt to API layer for streaming LLM call ──
    resume = interrupt({
        "type": "generation_request",
        "system": system,
        "user": user,
    })
    # On resume, interrupt() returns the value passed via Command(resume=...).
    resume_dict = resume if isinstance(resume, dict) else {}

    # Check cancel signal
    if resume_dict.get("cancelled") or resume_dict.get("cancel"):
        return {"should_end": True, "_cancelled": True}

    generated_text = resume_dict.get("generated_text", "")
    if not generated_text:
        saved_text = state.get("generated_text", "")
        if saved_text:
            logger.warning(
                "LLM returned empty text for generation %s, "
                "falling back to previous generated_text (%d chars)",
                state.get("generation_id"), len(saved_text),
            )
            generated_text = saved_text
        else:
            logger.warning(
                "LLM returned empty text for generation %s and no fallback available",
                state.get("generation_id"),
            )

    # Split into chapters
    chapters_data = _split_chapters(generated_text)
    chapter_titles = [ch["title"] for ch in chapters_data]

    # Save chapters
    db = Database(DB_PATH)
    await db.init()
    try:
        characters = await db.get_characters(novel_id)

        # Extract character states
        from backend.llm.factory import create_llm_provider
        llm = create_llm_provider()
        states = await extract_character_states(llm, generated_text, characters)
        character_states_json = json.dumps(states, ensure_ascii=False)

        saved_chapters = state.get("_saved_chapters", [])
        is_modify = state.get("enter_loop", False) and len(saved_chapters) > 0

        if is_modify:
            # Modify mode: update existing draft chapters
            for i, ch_data in enumerate(chapters_data):
                word_count = _count_chinese(ch_data["content"])
                if i < len(saved_chapters):
                    existing = saved_chapters[i]
                    await db.update_chapter(existing["id"], {
                        "title": ch_data["title"],
                        "content": ch_data["content"],
                        "word_count": word_count,
                        "generation_id": generation_id,
                    })
                    # Sync in-memory title so returned state is consistent
                    existing["title"] = ch_data["title"]
                else:
                    ch_id = str(uuid.uuid4())
                    ch_path = FileManager.chapter_path(novel_id, ch_id)
                    await db.create_chapter({
                        "id": ch_id,
                        "novel_id": novel_id,
                        "title": ch_data["title"],
                        "content": ch_data["content"],
                        "file_path": str(ch_path),
                        "status": "draft",
                        "sort_order": i,
                        "word_count": word_count,
                        "generation_id": generation_id,
                    })
                    saved_chapters.append({
                        "id": ch_id,
                        "title": ch_data["title"],
                        "file_path": str(ch_path),
                    })

            # ── Clean up excess chapters if count decreased ──
            if len(chapters_data) < len(saved_chapters):
                excess = saved_chapters[len(chapters_data):]
                for ch in excess:
                    await db.delete_chapter(ch["id"])
                saved_chapters[:] = saved_chapters[:len(chapters_data)]
        else:
            # First generation: create new chapters
            existing_chapters = await db.get_chapters_by_status(novel_id, "draft")
            for ch in existing_chapters:
                await db.delete_chapter(ch["id"])

            for i, ch_data in enumerate(chapters_data):
                ch_id = str(uuid.uuid4())
                word_count = _count_chinese(ch_data["content"])
                path = FileManager.chapter_path(novel_id, ch_id)
                await db.create_chapter({
                    "id": ch_id,
                    "novel_id": novel_id,
                    "title": ch_data["title"],
                    "content": ch_data["content"],
                    "file_path": str(path),
                    "status": "draft",
                    "sort_order": i,
                    "word_count": word_count,
                    "generation_id": generation_id,
                })
                saved_chapters.append({
                    "id": ch_id,
                    "title": ch_data["title"],
                    "file_path": str(path),
                })

        return {
            "generated_text": generated_text,
            "chapter_titles": chapter_titles,
            "character_states_json": character_states_json,
            "_saved_chapters": saved_chapters,
        }
    finally:
        await db.close()
