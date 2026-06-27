from backend.agent.state import State


async def init_check_node(state: State) -> dict:
    from backend.db.database import Database
    from backend.config import DB_PATH
    from backend.services.cursor import get_cursor_info

    novel_id = state["novel_id"]

    db = Database(DB_PATH)
    await db.init()
    try:
        novel = await db.get_novel(novel_id)
        cursor_info = await get_cursor_info(db, novel_id)

        characters = await db.get_characters(novel_id)
        char_design = "\n".join(
            f"- {c['name']}（{c.get('role', '')}）: {c.get('description', '')}"
            for c in characters
        )

        foreshadows = await db.get_foreshadows(novel_id)
        unused_ff = [f for f in foreshadows if f.get("status") == "unused"]
        foreshadow_text = "\n".join(
            f"- [{f['title']}] {f.get('description', '')}" for f in unused_ff
        )

        return {
            "base_prompt": novel.get("base_prompt", ""),
            "style_of_writing": novel.get("style_of_writing", ""),
            "world_outlook": novel.get("world_outlook", ""),
            "outline": cursor_info.get("outline", ""),
            "detailed_outline": cursor_info.get("detailed_outline", ""),
            "cursor_position": cursor_info.get("cursor_position", 0),
            "plot_nodes_count": cursor_info.get("plot_nodes_count", 0),
            "next_node_title": cursor_info.get("next_node_title", ""),
            "main_character_design": char_design,
            "foreshadow": foreshadow_text,
            "unlawful": False,
            "unlaw_reason": "",
        }
    finally:
        await db.close()

