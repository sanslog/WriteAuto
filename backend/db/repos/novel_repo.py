import uuid
import logging
from typing import Any

from backend.db.database import Database

logger = logging.getLogger(__name__)


class NovelRepo:
    """CRUD for novels table."""

    def __init__(self, db: Database):
        self.db = db

    async def get_all(self) -> list[dict[str, Any]]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM novels ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get(self, novel_id: str) -> dict[str, Any] | None:
        cursor = await self.db.conn.execute(
            "SELECT * FROM novels WHERE id = ?", (novel_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def create(self, data: dict) -> dict[str, Any]:
        novel_id = data.get("id", str(uuid.uuid4()))
        await self.db.conn.execute(
            """INSERT INTO novels (id, title, base_prompt, style_of_writing, world_outlook)
               VALUES (?, ?, ?, ?, ?)""",
            (novel_id, data.get("title", ""), data.get("base_prompt", ""),
             data.get("style_of_writing", ""), data.get("world_outlook", "")),
        )
        logger.info("Created novel %s", novel_id)
        return await self.get(novel_id)

    async def update(self, novel_id: str, data: dict) -> dict[str, Any] | None:
        fields = []
        values = []
        for k in ("title", "base_prompt", "style_of_writing", "world_outlook",
                  "cursor_position", "is_done"):
            if k in data:
                fields.append(f"{k} = ?")
                values.append(data[k])
        if not fields:
            return await self.get(novel_id)
        fields.append("updated_at = datetime('now')")
        values.append(novel_id)
        await self.db.conn.execute(
            f"UPDATE novels SET {', '.join(fields)} WHERE id = ?", values
        )
        logger.info("Updated novel %s with %s", novel_id, set(data.keys()))
        return await self.get(novel_id)

    async def delete(self, novel_id: str) -> None:
        await self.db.conn.execute(
            "DELETE FROM novels WHERE id = ?", (novel_id,)
        )
        logger.info("Deleted novel %s", novel_id)