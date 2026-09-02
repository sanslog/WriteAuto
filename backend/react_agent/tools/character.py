"""Character-profile tools for maintaining narrative consistency."""

from __future__ import annotations

import json
from typing import Optional

from pydantic import Field

from backend.db.dependencies import db_session
from backend.db.repos import ChapterRepo, CharacterRepo, NovelRepo
from backend.react_agent.tools.base import ToolCallError, ToolInput


class ListCharactersInput(ToolInput):
    novel_id: str = Field(min_length=1, description="小说项目 ID")


class SearchCharactersInput(ToolInput):
    novel_id: str = Field(min_length=1, description="小说项目 ID")
    name: str = Field(min_length=1, description="要搜索的角色名称")
    exact: bool = Field(default=False, description="为 true 时按名称精确匹配")


class CharacterIdInput(ToolInput):
    character_id: str = Field(min_length=1)


class CreateCharacterInput(ToolInput):
    novel_id: str = Field(min_length=1)
    name: str = Field(min_length=1, description="角色名")
    description: str = Field(default="", description="性格、外貌、能力和背景")
    role: str = Field(default="", description="主角 / 配角 / 反派等定位")


class UpdateCharacterInput(CharacterIdInput):
    name: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None
    role: Optional[str] = None


class CharacterStateEntry(ToolInput):
    name: str = Field(min_length=1, description="角色名，必须与角色档案一致")
    state: str = Field(default="", description="本节点结束时的角色状态")
    location: str = Field(default="", description="当前位置")
    status_condition: str = Field(default="", description="身体状况或行动能力")


class RecordCharacterStatesInput(ToolInput):
    novel_id: str = Field(min_length=1)
    chapter_id: str = Field(min_length=1)
    states: list[CharacterStateEntry] = Field(default_factory=list)


async def _with_latest_state(
    db,
    repo: CharacterRepo,
    characters: list[dict],
) -> list[dict]:
    enriched: list[dict] = []
    for character in characters:
        item = dict(character)
        states = await repo.get_states(character["id"])
        item["latest_state"] = states[-1] if states else None
        item["state_count"] = len(states)
        enriched.append(item)
    return enriched


async def list_characters(novel_id: str) -> dict:
    async with db_session() as db:
        repo = CharacterRepo(db)
        characters = await _with_latest_state(db, repo, await repo.get_by_novel(novel_id))
    return {"success": True, "data": characters}


async def search_characters(
    novel_id: str,
    name: str,
    exact: bool = False,
) -> dict:
    """Find a character by a known name without dumping the whole catalog."""

    async with db_session() as db:
        repo = CharacterRepo(db)
        characters = await repo.get_by_novel(novel_id)
        if exact:
            matched = [item for item in characters if item.get("name") == name]
        else:
            lowered = name.lower()
            matched = [
                item
                for item in characters
                if lowered in str(item.get("name", "")).lower()
            ]
        matched = await _with_latest_state(db, repo, matched)
    return {"success": True, "data": matched}


async def create_character(
    novel_id: str,
    name: str,
    description: str = "",
    role: str = "",
) -> dict:
    async with db_session() as db:
        if not await NovelRepo(db).get(novel_id):
            raise ToolCallError(f"Novel {novel_id} not found")
        character = await CharacterRepo(db).create(
            {
                "novel_id": novel_id,
                "name": name,
                "description": description,
                "role": role,
            }
        )
    return {"success": True, "data": character}


async def update_character(
    character_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    role: Optional[str] = None,
) -> dict:
    fields = {
        key: value
        for key, value in {
            "name": name,
            "description": description,
            "role": role,
        }.items()
        if value is not None
    }
    async with db_session() as db:
        repo = CharacterRepo(db)
        character = await repo.update(character_id, fields)
        if not character:
            raise ToolCallError(f"Character {character_id} not found")
    return {"success": True, "data": character}


async def delete_character(character_id: str) -> dict:
    async with db_session() as db:
        repo = CharacterRepo(db)
        if not await repo.get(character_id):
            raise ToolCallError(f"Character {character_id} not found")
        await repo.delete(character_id)
    return {"success": True, "data": {"id": character_id, "deleted": True}}


async def record_character_states(
    novel_id: str,
    chapter_id: str,
    states: list[CharacterStateEntry],
) -> dict:
    """Persist one long-term state snapshot per recognised character."""

    async with db_session() as db:
        char_repo = CharacterRepo(db)
        chapter_repo = ChapterRepo(db)
        chapter = await chapter_repo.get(chapter_id)
        if not chapter or chapter.get("novel_id") != novel_id:
            raise ToolCallError(f"Chapter {chapter_id} does not belong to novel {novel_id}")

        characters = await char_repo.get_by_novel(novel_id)
        characters_by_name = {item["name"]: item for item in characters if item.get("name")}
        saved: list[dict] = []
        missing: list[str] = []

        for entry in states:
            entry_data = (
                entry.model_dump() if hasattr(entry, "model_dump") else dict(entry)
            )
            character = characters_by_name.get(entry_data["name"])
            if not character:
                missing.append(entry_data["name"])
                continue
            state = await char_repo.create_state(
                {
                    "character_id": character["id"],
                    "chapter_id": chapter_id,
                    "state_json": json.dumps(entry_data, ensure_ascii=False),
                }
            )
            saved.append(state)

    return {
        "success": True,
        "data": {
            "chapter_id": chapter_id,
            "saved_states": saved,
            "missing_characters": missing,
        },
    }
