"""Writing-app configuration tools."""

from __future__ import annotations

from pydantic import Field

from backend.config import update_llm_config
from backend.db.dependencies import db_session
from backend.db.repos import SettingsRepo
from backend.react_agent.tools.base import ToolInput


class GetSettingsInput(ToolInput):
    pass


class UpdateSettingsInput(ToolInput):
    fields: dict[str, str] = Field(
        default_factory=dict,
        description="要写入 app_settings 的键值对",
    )


async def get_settings() -> dict:
    async with db_session() as db:
        settings = await SettingsRepo(db).get_all()
    return {"success": True, "data": settings}


async def update_settings(fields: dict[str, str]) -> dict:
    async with db_session() as db:
        settings = await SettingsRepo(db).update(fields)
    for key, value in fields.items():
        update_llm_config(key, str(value))
    return {"success": True, "data": settings}

