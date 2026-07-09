from backend.agent.state import State
from backend.db.database import Database
from backend.db.repos import ForeshadowRepo
from backend.config import DB_PATH


async def injection_foreshadow_node(state: State) -> dict:
    novel_id = state["novel_id"]
    foreshadow_ids = state.get("foreshadow_ids", [])

    db = Database(DB_PATH)
    await db.init()
    try:
        ff_repo = ForeshadowRepo(db)
        all_ff = await ff_repo.get_by_novel(novel_id)

        if foreshadow_ids:
            selected = [f for f in all_ff if f["id"] in foreshadow_ids]
        else:
            selected = [f for f in all_ff if f.get("status") == "unused"]

        foreshadow_text = "\n".join(
            f"- [{f['title']}] {f.get('description', '')}" for f in selected
        )
        return {"foreshadow": foreshadow_text}
    finally:
        await db.close()
