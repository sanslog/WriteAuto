import uuid
import logging
from typing import Any

from backend.db.database import Database

logger = logging.getLogger(__name__)


class CharacterRepo:
    """CRUD for characters + character_states tables."""

    def __init__(self, db: Database):
        self.db = db

    # ?? Characters ??

    async def get_by_novel(self, novel_id: str) -> list[dict[str, Any]]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM characters WHERE novel_id = ? ORDER BY created_at",
            (novel_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get(self, char_id: str) -> dict[str, Any] | None:
        cursor = await self.db.conn.execute(
            "SELECT * FROM characters WHERE id = ?", (char_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def create(self, data: dict) -> dict[str, Any]:
        char_id = data.get("id", str(uuid.uuid4()))
        await self.db.conn.execute(
            """INSERT INTO characters (id, novel_id, name, description, role)
               VALUES (?, ?, ?, ?, ?)""",
            (char_id, data["novel_id"], data.get("name", ""),
             data.get("description", ""), data.get("role", "")),
        )
        logger.info("Created character %s for novel %s", char_id, data["novel_id"])
        return await self.get(char_id)

    async def update(self, char_id: str, data: dict) -> dict[str, Any] | None:
        fields = []
        values = []
        for k in ("name", "description", "role"):
            if k in data:
                fields.append(f"{k} = ?")
                values.append(data[k])
        if not fields:
            return await self.get(char_id)
        fields.append("updated_at = datetime('now')")
        values.append(char_id)
        await self.db.conn.execute(
            f"UPDATE characters SET {', '.join(fields)} WHERE id = ?", values
        )
        logger.info("Updated character %s", char_id)
        return await self.get(char_id)

    async def delete(self, char_id: str) -> None:
        await self.db.conn.execute(
            "DELETE FROM characters WHERE id = ?", (char_id,)
        )
        logger.info("Deleted character %s", char_id)

    # ?? Character States ??

    async def get_states(self, character_id: str) -> list[dict[str, Any]]:
        cursor = await self.db.conn.execute(
            "SELECT * FROM character_states WHERE character_id = ? ORDER BY created_at",
            (character_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def create_state(self, data: dict) -> dict[str, Any]:
        cs_id = data.get("id", str(uuid.uuid4()))
        await self.db.conn.execute(
            """INSERT INTO character_states (id, character_id, chapter_id, state_json)
               VALUES (?, ?, ?, ?)""",
            (cs_id, data["character_id"], data["chapter_id"],
             data.get("state_json", "{}")),
        )
        logger.info("Created character_state %s", cs_id)
        return {"id": cs_id, **data}