import uuid
import logging
from typing import Any

from backend.db.database import Database

logger = logging.getLogger(__name__)


class ForeshadowRepo:
    """CRUD for foreshadows table."""

    def __init__(self, db: Database):
        self.db = db

    async def get_by_novel(self, novel_id: str) -> list[dict[str, Any]]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM foreshadows WHERE novel_id = ? ORDER BY created_at",
            (novel_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get(self, fid: str) -> dict[str, Any] | None:
        cursor = await self.db.conn.execute(
            "SELECT * FROM foreshadows WHERE id = ?", (fid,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def create(self, data: dict) -> dict[str, Any]:
        fid = data.get("id", str(uuid.uuid4()))
        await self.db.conn.execute(
            """INSERT INTO foreshadows (id, novel_id, title, description, status)
               VALUES (?, ?, ?, ?, ?)""",
            (fid, data["novel_id"], data.get("title", ""),
             data.get("description", ""), data.get("status", "unused")),
        )
        logger.info("Created foreshadow %s for novel %s", fid, data["novel_id"])
        return await self.get(fid)

    async def update(self, fid: str, data: dict) -> dict[str, Any] | None:
        fields = []
        values = []
        for k in ("title", "description", "status", "chapter_id"):
            if k in data:
                fields.append(f"{k} = ?")
                values.append(data[k])
        if not fields:
            return await self.get(fid)
        fields.append("updated_at = datetime('now')")
        values.append(fid)
        await self.db.conn.execute(
            f"UPDATE foreshadows SET {', '.join(fields)} WHERE id = ?", values
        )
        logger.info("Updated foreshadow %s", fid)
        return await self.get(fid)

    async def delete(self, fid: str) -> None:
        await self.db.conn.execute(
            "DELETE FROM foreshadows WHERE id = ?", (fid,)
        )
        logger.info("Deleted foreshadow %s", fid)