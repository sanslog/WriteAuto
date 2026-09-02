"""Plot-outline and writing-position tools."""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from backend.db.dependencies import db_session
from backend.db.repos import NovelRepo, PlotNodeRepo
from backend.react_agent.tools.base import ToolCallError, ToolInput


class NovelIdInput(ToolInput):
    novel_id: str = Field(min_length=1, description="小说项目 ID")


class CreatePlotNodeInput(NovelIdInput):
    title: str = Field(min_length=1, description="剧情节点标题")
    summary: str = Field(default="", description="剧情节点摘要")
    detailed_outline: str = Field(default="", description="供写作使用的详细大纲")
    status: str = Field(default="planned", description="planned / writing / done")
    sort_order: Optional[int] = Field(default=None, ge=0)


class UpdatePlotNodeInput(ToolInput):
    node_id: str = Field(min_length=1)
    title: Optional[str] = Field(default=None, min_length=1)
    summary: Optional[str] = None
    detailed_outline: Optional[str] = None
    status: Optional[str] = None
    sort_order: Optional[int] = Field(default=None, ge=0)
    chapter_id: Optional[str] = None


class DeletePlotNodeInput(ToolInput):
    node_id: str = Field(min_length=1)


class MoveCursorInput(NovelIdInput):
    cursor_position: int = Field(ge=0, description="剧情节点下标，从 0 开始")


async def list_plot_nodes(novel_id: str) -> dict:
    async with db_session() as db:
        nodes = await PlotNodeRepo(db).get_by_novel(novel_id)
    return {"success": True, "data": nodes}


async def create_plot_node(
    novel_id: str,
    title: str,
    summary: str = "",
    detailed_outline: str = "",
    status: str = "planned",
    sort_order: Optional[int] = None,
) -> dict:
    async with db_session() as db:
        plot_repo = PlotNodeRepo(db)
        if not await NovelRepo(db).get(novel_id):
            raise ToolCallError(f"Novel {novel_id} not found")

        if sort_order is None:
            existing = await plot_repo.get_by_novel(novel_id)
            sort_order = len(existing)

        node = await plot_repo.create(
            {
                "novel_id": novel_id,
                "title": title,
                "summary": summary,
                "detailed_outline": detailed_outline,
                "status": status,
                "sort_order": sort_order,
            }
        )
    return {"success": True, "data": node}


async def update_plot_node(
    node_id: str,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    detailed_outline: Optional[str] = None,
    status: Optional[str] = None,
    sort_order: Optional[int] = None,
    chapter_id: Optional[str] = None,
) -> dict:
    fields = {
        key: value
        for key, value in {
            "title": title,
            "summary": summary,
            "detailed_outline": detailed_outline,
            "status": status,
            "sort_order": sort_order,
            "chapter_id": chapter_id,
        }.items()
        if value is not None
    }
    async with db_session() as db:
        plot_repo = PlotNodeRepo(db)
        node = await plot_repo.update(node_id, fields)
        if not node:
            raise ToolCallError(f"Plot node {node_id} not found")
    return {"success": True, "data": node}


async def delete_plot_node(node_id: str) -> dict:
    async with db_session() as db:
        plot_repo = PlotNodeRepo(db)
        novel_repo = NovelRepo(db)
        node = await plot_repo.get(node_id)
        if not node:
            raise ToolCallError(f"Plot node {node_id} not found")

        novel_id = node["novel_id"]
        deleted_order = node["sort_order"]
        await plot_repo.delete(node_id)

        novel = await novel_repo.get(novel_id)
        cursor = novel.get("cursor_position", 0) if novel else 0
        if deleted_order <= cursor and cursor > 0:
            cursor -= 1

        remaining = await plot_repo.get_by_novel(novel_id)
        if cursor >= len(remaining) and remaining:
            cursor = len(remaining) - 1
        elif not remaining:
            cursor = 0

        if novel and cursor != novel.get("cursor_position", 0):
            await novel_repo.update(novel_id, {"cursor_position": cursor})

    return {"success": True, "data": {"id": node_id, "cursor_position": cursor}}


async def move_plot_cursor(novel_id: str, cursor_position: int) -> dict:
    async with db_session() as db:
        novel_repo = NovelRepo(db)
        plot_repo = PlotNodeRepo(db)
        nodes = await plot_repo.get_by_novel(novel_id)
        if not nodes:
            raise ToolCallError(f"Novel {novel_id} has no plot nodes")

        bounded_position = min(cursor_position, len(nodes) - 1)
        novel = await novel_repo.update(novel_id, {"cursor_position": bounded_position})
        if not novel:
            raise ToolCallError(f"Novel {novel_id} not found")

    return {"success": True, "data": novel}

