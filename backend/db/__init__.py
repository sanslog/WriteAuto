from backend.config import DB_PATH
from backend.db.database import Database

async def get_db_yield():
    db = Database(DB_PATH)
    await db.init()
    try:
        yield db
    finally:
        await db.close()
        