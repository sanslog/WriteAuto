"""Novel project and writing-style tools."""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from backend.db.dependencies import db_session
from backend.db.repos import NovelRepo
from backend.react_agent.tools.base import ToolCallError, ToolInput


class ListNovelsInput(ToolInput):
    pass


class NovelIdInput(ToolInput):
    novel_id: str = Field(min_length=1, description="小说项目 ID")


class CreateNovelInput(ToolInput):
    title: str = Field(min_length=1, description="小说标题")
    base_prompt: str = Field(default="", description="题材、主角或剧情梗概")
    style_of_writing: str = Field(default="", description="叙述文风")
    world_outlook: str = Field(default="", description="世界观设定")


class UpdateNovelInput(ToolInput):
    novel_id: str = Field(min_length=1)
    title: Optional[str] = Field(default=None, min_length=1)
    base_prompt: Optional[str] = None
    style_of_writing: Optional[str] = None
    world_outlook: Optional[str] = None


async def list_novels() -> dict:
    async with db_session() as db:
        novels = await NovelRepo(db).get_all()
    return {"success": True, "data": novels}


async def get_novel(novel_id: str) -> dict:
    async with db_session() as db:
        novel = await NovelRepo(db).get(novel_id)
    if not novel:
        raise ToolCallError(f"Novel {novel_id} not found")
    return {"success": True, "data": novel}


async def create_novel(
    title: str,
    base_prompt: str = "",
    style_of_writing: str = "",
    world_outlook: str = "",
) -> dict:
    async with db_session() as db:
        novel = await NovelRepo(db).create(
            {
                "title": title,
                "base_prompt": base_prompt,
                "style_of_writing": style_of_writing,
                "world_outlook": world_outlook,
            }
        )
    return {"success": True, "data": novel}


async def update_novel(
    novel_id: str,
    title: Optional[str] = None,
    base_prompt: Optional[str] = None,
    style_of_writing: Optional[str] = None,
    world_outlook: Optional[str] = None,
) -> dict:
    fields = {
        key: value
        for key, value in {
            "title": title,
            "base_prompt": base_prompt,
            "style_of_writing": style_of_writing,
            "world_outlook": world_outlook,
        }.items()
        if value is not None
    }
    async with db_session() as db:
        repo = NovelRepo(db)
        if not await repo.get(novel_id):
            raise ToolCallError(f"Novel {novel_id} not found")
        novel = await repo.update(novel_id, fields)
    return {"success": True, "data": novel}


async def delete_novel(novel_id: str) -> dict:
    async with db_session() as db:
        repo = NovelRepo(db)
        if not await repo.get(novel_id):
            raise ToolCallError(f"Novel {novel_id} not found")
        await repo.delete(novel_id)
    return {"success": True, "data": {"id": novel_id, "deleted": True}}

