"""Foreshadowing tools for long-form plot continuity."""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from backend.db.dependencies import db_session
from backend.db.repos import ForeshadowRepo, NovelRepo
from backend.react_agent.tools.base import ToolCallError, ToolInput


class ListForeshadowsInput(ToolInput):
    novel_id: str = Field(min_length=1, description="小说项目 ID")


class ForeshadowIdInput(ToolInput):
    foreshadow_id: str = Field(min_length=1)


class CreateForeshadowInput(ToolInput):
    novel_id: str = Field(min_length=1)
    title: str = Field(min_length=1, description="伏笔名称")
    description: str = Field(default="", description="伏笔内容和后续回收方向")
    status: str = Field(default="unused", description="unused / resolved")
    chapter_id: Optional[str] = None


class UpdateForeshadowInput(ForeshadowIdInput):
    title: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None
    status: Optional[str] = None
    chapter_id: Optional[str] = None


async def list_foreshadows(novel_id: str) -> dict:
    async with db_session() as db:
        foreshadows = await ForeshadowRepo(db).get_by_novel(novel_id)
    return {"success": True, "data": foreshadows}


async def create_foreshadow(
    novel_id: str,
    title: str,
    description: str = "",
    status: str = "unused",
    chapter_id: Optional[str] = None,
) -> dict:
    async with db_session() as db:
        if not await NovelRepo(db).get(novel_id):
            raise ToolCallError(f"Novel {novel_id} not found")
        foreshadow = await ForeshadowRepo(db).create(
            {
                "novel_id": novel_id,
                "title": title,
                "description": description,
                "status": status,
                "chapter_id": chapter_id,
            }
        )
    return {"success": True, "data": foreshadow}


async def update_foreshadow(
    foreshadow_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    chapter_id: Optional[str] = None,
) -> dict:
    fields = {
        key: value
        for key, value in {
            "title": title,
            "description": description,
            "status": status,
            "chapter_id": chapter_id,
        }.items()
        if value is not None
    }
    async with db_session() as db:
        repo = ForeshadowRepo(db)
        foreshadow = await repo.update(foreshadow_id, fields)
        if not foreshadow:
            raise ToolCallError(f"Foreshadow {foreshadow_id} not found")
    return {"success": True, "data": foreshadow}


async def delete_foreshadow(foreshadow_id: str) -> dict:
    async with db_session() as db:
        repo = ForeshadowRepo(db)
        if not await repo.get(foreshadow_id):
            raise ToolCallError(f"Foreshadow {foreshadow_id} not found")
        await repo.delete(foreshadow_id)
    return {"success": True, "data": {"id": foreshadow_id, "deleted": True}}

