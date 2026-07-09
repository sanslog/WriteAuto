import uuid
import logging
from typing import Any

from backend.db.database import Database

logger = logging.getLogger(__name__)


class PlotNodeRepo:
    """CRUD for plot_nodes table."""

    def __init__(self, db: Database):
        self.db = db

    async def get_by_novel(self, novel_id: str) -> list[dict[str, Any]]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM plot_nodes WHERE novel_id = ? ORDER BY sort_order",
            (novel_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get(self, node_id: str) -> dict[str, Any] | None:
        cursor = await self.db.conn.execute(
            "SELECT * FROM plot_nodes WHERE id = ?", (node_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def create(self, data: dict) -> dict[str, Any]:
        node_id = data.get("id", str(uuid.uuid4()))
        await self.db.conn.execute(
            """INSERT INTO plot_nodes
               (id, novel_id, sort_order, title, summary, detailed_outline, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (node_id, data["novel_id"], data.get("sort_order", 0),
             data.get("title", ""), data.get("summary", ""),
             data.get("detailed_outline", ""), data.get("status", "planned")),
        )
        logger.info("Created plot_node %s for novel %s", node_id, data["novel_id"])
        return await self.get(node_id)

    async def update(self, node_id: str, data: dict) -> dict[str, Any] | None:
        fields = []
        values = []
        for k in ("title", "summary", "detailed_outline", "status", "sort_order", "chapter_id"):
            if k in data:
                fields.append(f"{k} = ?")
                values.append(data[k])
        if not fields:
            return await self.get(node_id)
        fields.append("updated_at = datetime('now')")
        values.append(node_id)
        await self.db.conn.execute(
            f"UPDATE plot_nodes SET {', '.join(fields)} WHERE id = ?", values
        )
        logger.info("Updated plot_node %s", node_id)
        return await self.get(node_id)

    async def delete(self, node_id: str) -> None:
        await self.db.conn.execute(
            "DELETE FROM plot_nodes WHERE id = ?", (node_id,)
        )
        logger.info("Deleted plot_node %s", node_id)