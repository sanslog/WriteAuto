import logging
from typing import Any

from backend.db.database import Database

logger = logging.getLogger(__name__)


class SettingsRepo:
    """CRUD for app_settings table."""

    def __init__(self, db: Database):
        self.db = db

    async def get_all(self) -> dict[str, str]:
        cursor = await self.db.conn.execute("SELECT * FROM app_settings")
        rows = await cursor.fetchall()
        return {r["key"]: r["value"] for r in rows}

    async def update(self, data: dict[str, str]) -> dict[str, str]:
        for k, v in data.items():
            await self.db.conn.execute(
                "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
                (k, str(v)),
            )
        logger.info("Updated %d settings", len(data))
        return await self.get_all()

    async def create_generation_log(self, data: dict[str, Any]) -> dict[str, Any]:
        import uuid
        log_id = data.get("id", str(uuid.uuid4()))
        await self.db.conn.execute(
            """INSERT INTO generation_logs
               (id, novel_id, generation_id, prompt, result, model, tokens_used)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (log_id, data["novel_id"], data["generation_id"],
             data.get("prompt", ""), data.get("result", ""),
             data.get("model", ""), data.get("tokens_used", 0)),
        )
        logger.info("Created generation_log %s", log_id)
        return {"id": log_id, **data}