import asyncio

from backend.agent.state import State


async def _injection_foreshadow_impl(state: State) -> dict:
    from backend.db.database import Database
    from backend.config import DB_PATH

    novel_id = state["novel_id"]
    foreshadow_ids = state.get("foreshadow_ids", [])

    db = Database(DB_PATH)
    await db.init()
    try:
        all_ff = await db.get_foreshadows(novel_id)

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


def injection_foreshadow_node(state: State) -> dict:
    return asyncio.run(_injection_foreshadow_impl(state))
