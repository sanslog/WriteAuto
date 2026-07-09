from backend.agent.state import State
from backend.db.database import Database
from backend.db.repos import CharacterRepo
from backend.config import DB_PATH


async def character_fetch_node(state: State) -> dict:
    novel_id = state["novel_id"]
    detailed_outline = state.get("detailed_outline", "")

    if not detailed_outline.strip():
        return {"main_character_design": "", "unlawful": False, "unlaw_reason": ""}

    db = Database(DB_PATH)
    await db.init()
    try:
        char_repo = CharacterRepo(db)
        characters = await char_repo.get_by_novel(novel_id)
        matched = [c for c in characters if c.get("name") and c["name"] in detailed_outline]

        if not matched:
            return {"main_character_design": "", "unlawful": False, "unlaw_reason": ""}

        char_design = "\n".join(
            f"- {c['name']} ({c.get('role', '')}): {c.get('description', '')}"
            for c in matched
        )
        return {"main_character_design": char_design, "unlawful": False, "unlaw_reason": ""}
    finally:
        await db.close()
