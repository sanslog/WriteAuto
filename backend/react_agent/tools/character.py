"""Character-profile tools for maintaining narrative consistency."""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from backend.db.dependencies import db_session
from backend.db.repos import CharacterRepo, NovelRepo
from backend.react_agent.tools.base import ToolCallError, ToolInput


class ListCharactersInput(ToolInput):
    novel_id: str = Field(min_length=1, description="小说项目 ID")


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


async def list_characters(novel_id: str) -> dict:
    async with db_session() as db:
        characters = await CharacterRepo(db).get_by_novel(novel_id)
    return {"success": True, "data": characters}


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

