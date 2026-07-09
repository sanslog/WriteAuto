import uuid
import logging
from typing import Any

from backend.db.database import Database

logger = logging.getLogger(__name__)


class ChapterRepo:
    """CRUD for chapters table."""

    def __init__(self, db: Database):
        self.db = db

    async def get_by_novel(self, novel_id: str) -> list[dict[str, Any]]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM chapters WHERE novel_id = ? ORDER BY sort_order",
            (novel_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get(self, chapter_id: str) -> dict[str, Any] | None:
        cursor = await self.db.conn.execute(
            "SELECT * FROM chapters WHERE id = ?", (chapter_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_by_status(self, novel_id: str, status: str) -> list[dict[str, Any]]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM chapters WHERE novel_id = ? AND status = ? ORDER BY sort_order",
            (novel_id, status),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def create(self, data: dict) -> dict[str, Any]:
        chapter_id = data.get("id", str(uuid.uuid4()))
        await self.db.conn.execute(
            """INSERT INTO chapters
               (id, novel_id, title, content, file_path, status, sort_order, word_count, generation_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (chapter_id, data["novel_id"], data.get("title", ""),
             data.get("content", ""), data.get("file_path", ""),
             data.get("status", "draft"), data.get("sort_order", 0),
             data.get("word_count", 0), data.get("generation_id", "")),
        )
        logger.info("Created chapter %s for novel %s", chapter_id, data["novel_id"])
        return await self.get(chapter_id)

    async def update(self, chapter_id: str, data: dict) -> dict[str, Any] | None:
        fields = []
        values = []
        for k in ("title", "content", "file_path", "status", "sort_order",
                  "word_count", "generation_id"):
            if k in data:
                fields.append(f"{k} = ?")
                values.append(data[k])
        if not fields:
            return await self.get(chapter_id)
        fields.append("updated_at = datetime('now')")
        values.append(chapter_id)
        await self.db.conn.execute(
            f"UPDATE chapters SET {', '.join(fields)} WHERE id = ?", values
        )
        logger.info("Updated chapter %s", chapter_id)
        return await self.get(chapter_id)

    async def delete(self, chapter_id: str) -> None:
        await self.db.conn.execute(
            "DELETE FROM chapters WHERE id = ?", (chapter_id,)
        )
        logger.info("Deleted chapter %s", chapter_id)