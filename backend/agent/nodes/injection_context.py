from backend.agent.state import State
from backend.db.database import Database
from backend.db.repos import ChapterRepo
from backend.config import DB_PATH
from backend.services.context import build_context


async def injection_context_node(state: State) -> dict:
    novel_id = state["novel_id"]
    chapter_ids = state.get("chapter_ids", [])

    db = Database(DB_PATH)
    await db.init()
    try:
        chapter_repo = ChapterRepo(db)
        context = await build_context(db, novel_id, chapter_ids if chapter_ids else None)
        return {"context": context}
    finally:
        await db.close()
