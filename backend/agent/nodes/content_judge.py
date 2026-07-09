import json
import logging

from langgraph.types import interrupt

from backend.agent.state import State
from backend.config import MAX_MODIFICATION_COUNT, DB_PATH
from backend.db.database import Database
from backend.db.repos import (
    NovelRepo, PlotNodeRepo, ChapterRepo, CharacterRepo, ForeshadowRepo, SettingsRepo,
)

logger = logging.getLogger(__name__)


async def _save_approved_content(state: State):
    db = Database(DB_PATH)
    await db.init()
    try:
        novel_repo = NovelRepo(db)
        plot_repo = PlotNodeRepo(db)
        chapter_repo = ChapterRepo(db)
        char_repo = CharacterRepo(db)
        ff_repo = ForeshadowRepo(db)
        settings_repo = SettingsRepo(db)

        novel_id = state["novel_id"]
        saved_chapters = state.get("_saved_chapters", [])

        for ch in saved_chapters:
            await chapter_repo.update(ch["id"], {"status": "approved"})

        cursor = state["cursor_position"]
        nodes = await plot_repo.get_by_novel(novel_id)
        if cursor < len(nodes) and saved_chapters:
            await plot_repo.update(nodes[cursor]["id"], {
                "chapter_id": saved_chapters[0]["id"],
                "status": "written",
            })

        chars = await char_repo.get_by_novel(novel_id)
        states_json = state.get("character_states_json", "[]")
        states = json.loads(states_json) if isinstance(states_json, str) else states_json
        for ch_data in saved_chapters:
            for st in states:
                for char in chars:
                    if char["name"] == st.get("name", ""):
                        await char_repo.create_state({
                            "character_id": char["id"],
                            "chapter_id": ch_data["id"],
                            "state_json": json.dumps(st, ensure_ascii=False),
                        })

        new_cursor = min(cursor + 1, len(nodes) - 1) if nodes else 0
        await novel_repo.update(novel_id, {"cursor_position": new_cursor})

        foreshadow_ids = state.get("foreshadow_ids", [])
        if foreshadow_ids:
            for fid in foreshadow_ids:
                await ff_repo.update(fid, {"status": "used"})
        else:
            all_ff = await ff_repo.get_by_novel(novel_id)
            unused = [f for f in all_ff if f.get("status") == "unused"]
            if saved_chapters:
                for f in unused:
                    await ff_repo.update(f["id"], {
                        "status": "used",
                        "chapter_id": saved_chapters[0]["id"],
                    })

        await settings_repo.create_generation_log({
            "novel_id": novel_id,
            "generation_id": state["generation_id"],
            "prompt": "",
            "result": state.get("generated_text", "")[:500],
            "model": "",
            "tokens_used": 0,
        })
    finally:
        await db.close()


async def _mark_as_discarded(state: State):
    db = Database(DB_PATH)
    await db.init()
    try:
        chapter_repo = ChapterRepo(db)
        saved_chapters = state.get("_saved_chapters", [])
        for ch in saved_chapters:
            await chapter_repo.update(ch["id"], {"status": "discarded"})
    finally:
        await db.close()


async def content_judge_node(state: State) -> dict:
    if state.get("_cancelled"):
        return {"should_end": True, "enter_loop": False}

    judgment = interrupt({
        "type": "judgment",
        "generated_text": state["generated_text"],
        "chapter_titles": state["chapter_titles"],
        "character_states_json": state["character_states_json"],
        "modification_count": state.get("modification_count", 0),
    })

    action = judgment.get("action", "cancel")
    mod_count = state.get("modification_count", 0)

    if action == "approve":
        await _save_approved_content(state)
        return {"should_end": True, "enter_loop": False}
    elif action == "modify" and mod_count < MAX_MODIFICATION_COUNT:
        return {
            "should_end": False,
            "enter_loop": True,
            "modification_count": mod_count + 1,
            "user_input_text": judgment.get("text", ""),
        }
    else:
        if action != "approve":
            await _mark_as_discarded(state)
        return {"should_end": True, "enter_loop": False}
