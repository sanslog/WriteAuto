"""Chapter-text reading, generation-result saving, and revision tools."""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from backend.db.dependencies import db_session
from backend.db.repos import ChapterRepo, NovelRepo
from backend.react_agent.tools.base import ToolCallError, ToolInput


class ListChaptersInput(ToolInput):
    novel_id: str = Field(min_length=1, description="小说项目 ID")


class ChapterIdInput(ToolInput):
    chapter_id: str = Field(min_length=1)


class CreateChapterInput(ToolInput):
    novel_id: str = Field(min_length=1)
    title: str = Field(min_length=1, description="章节标题")
    content: str = Field(min_length=1, description="章节正文")
    status: str = Field(default="draft", description="draft / approved")
    sort_order: Optional[int] = Field(default=None, ge=0)
    word_count: Optional[int] = Field(default=None, ge=0)
    generation_id: str = Field(default="", description="生成任务 ID")


class UpdateChapterInput(ChapterIdInput):
    title: Optional[str] = Field(default=None, min_length=1)
    content: Optional[str] = Field(default=None, min_length=1)
    status: Optional[str] = None
    sort_order: Optional[int] = Field(default=None, ge=0)
    word_count: Optional[int] = Field(default=None, ge=0)
    generation_id: Optional[str] = None


async def list_chapters(novel_id: str) -> dict:
    async with db_session() as db:
        chapters = await ChapterRepo(db).get_by_novel(novel_id)
    return {"success": True, "data": chapters}


async def get_chapter(chapter_id: str) -> dict:
    async with db_session() as db:
        chapter = await ChapterRepo(db).get(chapter_id)
    if not chapter:
        raise ToolCallError(f"Chapter {chapter_id} not found")
    return {"success": True, "data": chapter}


async def create_chapter(
    novel_id: str,
    title: str,
    content: str,
    status: str = "draft",
    sort_order: Optional[int] = None,
    word_count: Optional[int] = None,
    generation_id: str = "",
) -> dict:
    async with db_session() as db:
        chapter_repo = ChapterRepo(db)
        if not await NovelRepo(db).get(novel_id):
            raise ToolCallError(f"Novel {novel_id} not found")

        if sort_order is None:
            existing = await chapter_repo.get_by_novel(novel_id)
            sort_order = len(existing)

        chapter = await chapter_repo.create(
            {
                "novel_id": novel_id,
                "title": title,
                "content": content,
                "status": status,
                "sort_order": sort_order,
                "word_count": len(content) if word_count is None else word_count,
                "generation_id": generation_id,
            }
        )
    return {"success": True, "data": chapter}


async def update_chapter(
    chapter_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    status: Optional[str] = None,
    sort_order: Optional[int] = None,
    word_count: Optional[int] = None,
    generation_id: Optional[str] = None,
) -> dict:
    fields = {
        key: value
        for key, value in {
            "title": title,
            "content": content,
            "status": status,
            "sort_order": sort_order,
            "word_count": word_count,
            "generation_id": generation_id,
        }.items()
        if value is not None
    }
    if "content" in fields and "word_count" not in fields:
        fields["word_count"] = len(fields["content"])

    async with db_session() as db:
        repo = ChapterRepo(db)
        chapter = await repo.update(chapter_id, fields)
        if not chapter:
            raise ToolCallError(f"Chapter {chapter_id} not found")
    return {"success": True, "data": chapter}


async def delete_chapter(chapter_id: str) -> dict:
    async with db_session() as db:
        repo = ChapterRepo(db)
        if not await repo.get(chapter_id):
            raise ToolCallError(f"Chapter {chapter_id} not found")
        await repo.delete(chapter_id)
    return {"success": True, "data": {"id": chapter_id, "deleted": True}}

