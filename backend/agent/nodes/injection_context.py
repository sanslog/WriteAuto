import asyncio

from backend.agent.state import State


async def _injection_context_impl(state: State) -> dict:
    from backend.db.database import Database
    from backend.config import DB_PATH
    from backend.services.context import build_context

    novel_id = state["novel_id"]
    chapter_ids = state.get("chapter_ids", [])

    db = Database(DB_PATH)
    await db.init()
    try:
        context = await build_context(db, novel_id, chapter_ids if chapter_ids else None)
        return {"context": context}
    finally:
        await db.close()


def injection_context_node(state: State) -> dict:
    return asyncio.run(_injection_context_impl(state))
