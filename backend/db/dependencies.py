import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Depends
from backend.config import DB_PATH
from backend.db.database import Database

logger = logging.getLogger(__name__)


async def get_db_session() -> AsyncGenerator[Database, Any]:
    db = Database(DB_PATH)
    await db.init()
    try:
        yield db
        await db.conn.commit()
        logger.debug("DB session committed")
    except Exception as e:
        if db.conn:
            await db.conn.rollback()
            logger.warning(f"DB session rollback due to: {e}")
        raise
    finally:
        await db.close()


from contextlib import asynccontextmanager


@asynccontextmanager
async def db_session() -> AsyncGenerator[Database, Any]:
    """Async context manager for direct DB access outside FastAPI.

    Usage:
        async with db_session() as db:
            repo = NovelRepo(db)
            novels = await repo.get_all()
    """
    db = Database(DB_PATH)
    await db.init()
    try:
        yield db
        await db.conn.commit()
    except Exception as e:
        if db.conn:
            await db.conn.rollback()
            logger.warning(f"DB session rollback due to: {e}")
        raise
    finally:
        await db.close()


def get_repo_session(*repo_types: type) -> Any:
    """Return a FastAPI dependency providing repo instances.
    Auto commit/rollback via shared DB session.
    Single repo type returns the instance directly;
    multiple types return a tuple."""
    if len(repo_types) == 1:
        async def _single(db: Database = Depends(get_db_session)) -> Any:
            return repo_types[0](db)
        return _single
    async def _multi(db: Database = Depends(get_db_session)) -> tuple[Any, ...]:
        return tuple(rt(db) for rt in repo_types)
    return _multi
