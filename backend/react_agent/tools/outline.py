"""Plot-outline and writing-position tools."""

from __future__ import annotations

import json
from typing import Optional

from pydantic import Field

from backend.db.dependencies import db_session
from backend.db.repos import NovelRepo, PlotNodeRepo
from backend.db.repos.character_repo import CharacterRepo
from backend.db.repos.chapter_repo import ChapterRepo
from backend.db.repos.foreshadow_repo import ForeshadowRepo
from backend.react_agent.tools.base import ToolCallError, ToolInput
from backend.react_agent.tools.character import CharacterStateEntry


class NovelIdInput(ToolInput):
    novel_id: str = Field(min_length=1, description="小说项目 ID")


class CreatePlotNodeInput(NovelIdInput):
    title: str = Field(min_length=1, description="剧情节点标题")
    summary: str = Field(default="", description="剧情节点摘要")
    detailed_outline: str = Field(default="", description="供写作使用的详细大纲")
    status: str = Field(default="planned", description="planned / writing / written")
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


class CompletePlotNodeInput(ToolInput):
    novel_id: str = Field(min_length=1)
    chapter_id: str = Field(min_length=1, description="刚保存且要归档到当前节点的章节 ID")
    character_states: list[CharacterStateEntry] = Field(default_factory=list)
    resolved_foreshadow_ids: list[str] = Field(default_factory=list)


async def get_writing_context(novel_id: str) -> dict:
    """Return one stable snapshot for writing at the current plot cursor."""

    async with db_session() as db:
        novel_repo = NovelRepo(db)
        plot_repo = PlotNodeRepo(db)
        chapter_repo = ChapterRepo(db)
        char_repo = CharacterRepo(db)
        ff_repo = ForeshadowRepo(db)

        novel = await novel_repo.get(novel_id)
        if not novel:
            raise ToolCallError(f"Novel {novel_id} not found")

        nodes = await plot_repo.get_by_novel(novel_id)
        chapters = await chapter_repo.get_by_novel(novel_id)
        characters = await char_repo.get_by_novel(novel_id)
        foreshadows = await ff_repo.get_by_novel(novel_id)

        cursor = int(novel.get("cursor_position", 0))
        if not nodes:
            cursor = 0
        else:
            cursor = min(max(cursor, 0), len(nodes) - 1)

        current_node = nodes[cursor] if nodes else None
        next_node = nodes[cursor + 1] if cursor + 1 < len(nodes) else None
        recent_chapters = []
        for chapter in chapters[-2:]:
            item = dict(chapter)
            item["content"] = str(item.get("content", ""))[-4000:]
            recent_chapters.append(item)

    return {
        "success": True,
        "data": {
            "novel": novel,
            "cursor_position": cursor,
            "outline_nodes_count": len(nodes),
            "outline_complete": bool(novel.get("is_done")),
            "current_node": current_node,
            "next_node": next_node,
            "outline_nodes": nodes,
            "recent_chapters": recent_chapters,
            "characters": characters,
            "foreshadows": foreshadows,
        },
    }


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


async def complete_current_plot_node(
    novel_id: str,
    chapter_id: str,
    character_states: list[CharacterStateEntry],
    resolved_foreshadow_ids: list[str],
) -> dict:
    """Archive the saved chapter, persist memory, and advance the plot cursor.

    The cursor stays on the completed final node so it always points at a
    concrete outline node, while ``is_done`` records that the outline ended.
    """

    async with db_session() as db:
        novel_repo = NovelRepo(db)
        plot_repo = PlotNodeRepo(db)
        chapter_repo = ChapterRepo(db)
        char_repo = CharacterRepo(db)
        ff_repo = ForeshadowRepo(db)

        novel = await novel_repo.get(novel_id)
        if not novel:
            raise ToolCallError(f"Novel {novel_id} not found")

        nodes = await plot_repo.get_by_novel(novel_id)
        if not nodes:
            raise ToolCallError(f"Novel {novel_id} has no plot nodes")

        cursor = min(max(int(novel.get("cursor_position", 0)), 0), len(nodes) - 1)
        chapter = await chapter_repo.get(chapter_id)
        if not chapter or chapter.get("novel_id") != novel_id:
            raise ToolCallError(f"Chapter {chapter_id} does not belong to novel {novel_id}")

        current_node = nodes[cursor]
        existing_chapter_id = current_node.get("chapter_id")
        if existing_chapter_id and existing_chapter_id != chapter_id:
            raise ToolCallError(
                f"Plot node {current_node['id']} is already linked to chapter {existing_chapter_id}"
            )

        node = await plot_repo.update(
            current_node["id"],
            {"chapter_id": chapter_id, "status": "written"},
        )

        characters = await char_repo.get_by_novel(novel_id)
        characters_by_name = {item["name"]: item for item in characters if item.get("name")}
        saved_states: list[dict] = []
        missing_characters: list[str] = []
        for entry in character_states:
            entry_data = (
                entry.model_dump() if hasattr(entry, "model_dump") else dict(entry)
            )
            character = characters_by_name.get(entry_data["name"])
            if not character:
                missing_characters.append(entry_data["name"])
                continue
            saved_states.append(
                await char_repo.create_state(
                    {
                        "character_id": character["id"],
                        "chapter_id": chapter_id,
                        "state_json": json.dumps(entry_data, ensure_ascii=False),
                    }
                )
            )

        resolved_foreshadows: list[dict] = []
        unknown_foreshadow_ids: list[str] = []
        foreshadow_ids = {item["id"]: item for item in await ff_repo.get_by_novel(novel_id)}
        for foreshadow_id in resolved_foreshadow_ids:
            foreshadow = foreshadow_ids.get(foreshadow_id)
            if not foreshadow:
                unknown_foreshadow_ids.append(foreshadow_id)
                continue
            resolved_foreshadows.append(
                await ff_repo.update(
                    foreshadow_id,
                    {"status": "resolved", "chapter_id": chapter_id},
                )
            )

        next_cursor = cursor + 1
        outline_complete = next_cursor >= len(nodes)
        if outline_complete:
            next_cursor = len(nodes) - 1
        novel = await novel_repo.update(
            novel_id,
            {
                "cursor_position": next_cursor,
                "is_done": int(outline_complete),
            },
        )

    return {
        "success": True,
        "data": {
            "novel": novel,
            "chapter": chapter,
            "node": node,
            "previous_cursor_position": cursor,
            "cursor_position": next_cursor,
            "next_node": nodes[next_cursor] if not outline_complete else None,
            "outline_nodes_count": len(nodes),
            "outline_complete": outline_complete,
            "saved_character_states": saved_states,
            "missing_characters": missing_characters,
            "resolved_foreshadows": resolved_foreshadows,
            "unknown_foreshadow_ids": unknown_foreshadow_ids,
        },
    }
