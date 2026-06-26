from langgraph.types import interrupt

from backend.agent.state import State
from backend.config import MAX_MODIFICATION_COUNT


def _save_approved_content(state: State):
    """Save all approved content: mark chapters approved, advance cursor, etc."""
    import asyncio
    from backend.db.database import Database
    from backend.config import DB_PATH
    from backend.storage.file_manager import FileManager
    from backend.storage.markdown import write_markdown

    async def _save():
        db = Database(DB_PATH)
        await db.init()
        try:
            novel_id = state["novel_id"]
            saved_chapters = state.get("_saved_chapters", [])

            # Mark chapters as approved
            for ch in saved_chapters:
                await db.update_chapter(ch["id"], {"status": "approved"})

            # Associate chapter to current plot node
            cursor = state["cursor_position"]
            nodes = await db.get_plot_nodes(novel_id)
            if cursor < len(nodes) and saved_chapters:
                await db.update_plot_node(nodes[cursor]["id"], {
                    "chapter_id": saved_chapters[0]["id"],
                    "status": "written",
                })

            # Save character states
            chars = await db.get_characters(novel_id)
            states_json = state.get("character_states_json", "[]")
            import json
            states = json.loads(states_json) if isinstance(states_json, str) else states_json
            for ch_data in saved_chapters:
                for st in states:
                    for char in chars:
                        if char["name"] == st.get("name", ""):
                            await db.create_character_state({
                                "character_id": char["id"],
                                "chapter_id": ch_data["id"],
                                "state_json": json.dumps(st, ensure_ascii=False),
                            })

            # Advance cursor
            new_cursor = min(cursor + 1, len(nodes) - 1) if nodes else 0
            await db.update_novel(novel_id, {"cursor_position": new_cursor})

            # Mark foreshadows as used
            foreshadow_ids = state.get("foreshadow_ids", [])
            if foreshadow_ids:
                for fid in foreshadow_ids:
                    await db.update_foreshadow(fid, {"status": "used"})
            else:
                all_ff = await db.get_foreshadows(novel_id)
                unused = [f for f in all_ff if f.get("status") == "unused"]
                if saved_chapters:
                    for f in unused:
                        await db.update_foreshadow(f["id"], {
                            "status": "used",
                            "chapter_id": saved_chapters[0]["id"],
                        })

            # Export outline
            outline_path = FileManager.outline_path(novel_id)
            write_markdown(outline_path, state.get("outline", ""))

            # Log generation
            await db.create_generation_log({
                "novel_id": novel_id,
                "generation_id": state["generation_id"],
                "prompt": "",
                "result": state.get("generated_text", "")[:500],
                "model": "",
                "tokens_used": 0,
            })
        finally:
            await db.close()

    asyncio.run(_save())


def _mark_as_discarded(state: State):
    """Mark draft chapters as discarded."""
    import asyncio
    from backend.db.database import Database
    from backend.config import DB_PATH

    async def _discard():
        db = Database(DB_PATH)
        await db.init()
        try:
            saved_chapters = state.get("_saved_chapters", [])
            for ch in saved_chapters:
                await db.update_chapter(ch["id"], {"status": "discarded"})
        finally:
            await db.close()

    asyncio.run(_discard())


def content_judge_node(state: State) -> dict:
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
        _save_approved_content(state)
        return {"should_end": True, "enter_loop": False}

    elif action == "modify" and mod_count < MAX_MODIFICATION_COUNT:
        return {
            "should_end": False,
            "enter_loop": True,
            "modification_count": mod_count + 1,
            "user_input_text": judgment.get("text", ""),
        }

    else:  # cancel or overflow
        if action != "approve":
            _mark_as_discarded(state)
        return {"should_end": True, "enter_loop": False}
