from pydantic import BaseModel, Field
from typing import Optional


# ── Novel ──

class NovelCreate(BaseModel):
    title: str = ""
    base_prompt: str = ""
    style_of_writing: str = ""
    world_outlook: str = ""


class NovelUpdate(BaseModel):
    title: Optional[str] = None
    base_prompt: Optional[str] = None
    style_of_writing: Optional[str] = None
    world_outlook: Optional[str] = None
    cursor_position: Optional[int] = None
    is_done: Optional[int] = None


# ── Plot Node ──

class PlotNodeCreate(BaseModel):
    novel_id: str
    sort_order: int = 0
    title: str = ""
    summary: str = ""
    detailed_outline: str = ""
    status: str = "planned"


class PlotNodeUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    detailed_outline: Optional[str] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None
    chapter_id: Optional[str] = None


# ── Chapter ──

class ChapterCreate(BaseModel):
    novel_id: str
    title: str = ""
    content: str = ""
    file_path: str = ""
    status: str = "draft"
    sort_order: int = 0
    word_count: int = 0
    generation_id: str = ""


class ChapterUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    file_path: Optional[str] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None
    word_count: Optional[int] = None
    generation_id: Optional[str] = None


# ── Character ──

class CharacterCreate(BaseModel):
    novel_id: str
    name: str = ""
    description: str = ""
    role: str = ""


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None


# ── Character State ──

class CharacterStateCreate(BaseModel):
    character_id: str
    chapter_id: str
    state_json: str = "{}"


# ── Foreshadow ──

class ForeshadowCreate(BaseModel):
    novel_id: str
    title: str = ""
    description: str = ""
    status: str = "unused"


class ForeshadowUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    chapter_id: Optional[str] = None


# ── Generation ──

class GenerationPrepareResponse(BaseModel):
    generation_id: str
    novel_id: str
    outline: str
    detailed_outline: str
    cursor_position: int
    plot_nodes_count: int
    next_node_title: str
    characters: list[dict]
    foreshadows: list[dict]
    approved_chapters: list[dict]


class GenerationRunRequest(BaseModel):
    chapter_ids: list[str] = []
    foreshadow_ids: list[str] = []


class JudgeRequest(BaseModel):
    action: str  # "approve" | "modify" | "cancel"
    text: str = ""
    character_states: list[dict] = []
