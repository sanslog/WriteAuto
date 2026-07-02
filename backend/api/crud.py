from fastapi import APIRouter, Depends

from backend.db.database import Database
from backend.db.models import (
    NovelCreate, NovelUpdate,
    PlotNodeCreate, PlotNodeUpdate,
    ChapterCreate, ChapterUpdate,
    CharacterCreate, CharacterUpdate,
    ForeshadowCreate, ForeshadowUpdate,
)
from backend.db import get_db_yield as get_db

router = APIRouter(prefix="/api", tags=["crud"])


# ══════ Novels ══════

@router.get("/novels")
async def list_novels(db: Database = Depends(get_db)):
    novels = await db.get_all_novels()
    return {"success": True, "data": novels}


@router.get("/novels/{novel_id}")
async def get_novel(novel_id: str, db: Database = Depends(get_db)):
    novel = await db.get_novel(novel_id)
    return {"success": True, "data": novel}


@router.post("/novels")
async def create_novel(body: NovelCreate, db: Database = Depends(get_db)):
    novel = await db.create_novel(body.model_dump())
    return {"success": True, "data": novel}


@router.put("/novels/{novel_id}")
async def update_novel(novel_id: str, body: NovelUpdate, db: Database = Depends(get_db)):
    novel = await db.update_novel(novel_id, body.model_dump(exclude_none=True))
    return {"success": True, "data": novel}


@router.delete("/novels/{novel_id}")
async def delete_novel(novel_id: str, db: Database = Depends(get_db)):
    await db.delete_novel(novel_id)
    return {"success": True}


# ══════ Plot Nodes ══════

@router.get("/novels/{novel_id}/outline")
async def list_plot_nodes(novel_id: str, db: Database = Depends(get_db)):
    nodes = await db.get_plot_nodes(novel_id)
    return {"success": True, "data": nodes}


@router.post("/plot-nodes")
async def create_plot_node(body: PlotNodeCreate, db: Database = Depends(get_db)):
    node = await db.create_plot_node(body.model_dump())
    return {"success": True, "data": node}


@router.put("/plot-nodes/{node_id}")
async def update_plot_node(node_id: str, body: PlotNodeUpdate, db: Database = Depends(get_db)):
    node = await db.update_plot_node(node_id, body.model_dump(exclude_none=True))
    return {"success": True, "data": node}


@router.delete("/plot-nodes/{node_id}")
async def delete_plot_node(node_id: str, db: Database = Depends(get_db)):
    node = await db._get_plot_node(node_id)
    if not node:
        return {"success": False, "error": "节点不存在"}
    novel_id = node["novel_id"]
    deleted_order = node["sort_order"]

    await db.delete_plot_node(node_id)

    # ── 游标修正 ──
    novel = await db.get_novel(novel_id)
    cursor = novel.get("cursor_position", 0)

    # 被删节点在游标之前或位置相同 → 游标左移
    if deleted_order <= cursor and cursor > 0:
        cursor -= 1

    # 节点总长度小于游标 → 回退到最后
    remaining = await db.get_plot_nodes(novel_id)
    if cursor >= len(remaining) and remaining:
        cursor = len(remaining) - 1
    elif not remaining:
        cursor = 0

    if cursor != novel.get("cursor_position", 0):
        await db.update_novel(novel_id, {"cursor_position": cursor})

    return {"success": True, "cursor_position": cursor}


# ══════ Cursor ══════

@router.put("/novels/{novel_id}/cursor")
async def update_cursor(novel_id: str, body: dict, db: Database = Depends(get_db)):
    """手动拨动游标位置。body: {"cursor_position": int}"""
    cp = body.get("cursor_position", 0)
    if not isinstance(cp, int) or cp < 0:
        return {"success": False, "error": "cursor_position 必须是非负整数"}

    # 不得超过节点总数-1
    nodes = await db.get_plot_nodes(novel_id)
    max_cp = max(0, len(nodes) - 1)
    if cp > max_cp:
        cp = max_cp

    novel = await db.update_novel(novel_id, {"cursor_position": cp})
    return {"success": True, "data": novel}


# ══════ Chapters ══════

@router.get("/novels/{novel_id}/chapters")
async def list_chapters(novel_id: str, db: Database = Depends(get_db)):
    chapters = await db.get_chapters(novel_id)
    return {"success": True, "data": chapters}


@router.get("/chapters/{chapter_id}")
async def get_chapter(chapter_id: str, db: Database = Depends(get_db)):
    chapter = await db.get_chapter(chapter_id)
    return {"success": True, "data": chapter}


@router.post("/chapters")
async def create_chapter(body: ChapterCreate, db: Database = Depends(get_db)):
    chapter = await db.create_chapter(body.model_dump())
    return {"success": True, "data": chapter}


@router.put("/chapters/{chapter_id}")
async def update_chapter(chapter_id: str, body: ChapterUpdate, db: Database = Depends(get_db)):
    chapter = await db.update_chapter(chapter_id, body.model_dump(exclude_none=True))
    return {"success": True, "data": chapter}


@router.delete("/chapters/{chapter_id}")
async def delete_chapter(chapter_id: str, db: Database = Depends(get_db)):
    await db.delete_chapter(chapter_id)
    return {"success": True}


# ══════ Characters ══════

@router.get("/novels/{novel_id}/characters")
async def list_characters(novel_id: str, db: Database = Depends(get_db)):
    characters = await db.get_characters(novel_id)
    return {"success": True, "data": characters}


@router.post("/characters")
async def create_character(body: CharacterCreate, db: Database = Depends(get_db)):
    character = await db.create_character(body.model_dump())
    return {"success": True, "data": character}


@router.put("/characters/{char_id}")
async def update_character(char_id: str, body: CharacterUpdate, db: Database = Depends(get_db)):
    character = await db.update_character(char_id, body.model_dump(exclude_none=True))
    return {"success": True, "data": character}


@router.delete("/characters/{char_id}")
async def delete_character(char_id: str, db: Database = Depends(get_db)):
    await db.delete_character(char_id)
    return {"success": True}


# ══════ Foreshadows ══════

@router.get("/novels/{novel_id}/foreshadows")
async def list_foreshadows(novel_id: str, db: Database = Depends(get_db)):
    foreshadows = await db.get_foreshadows(novel_id)
    return {"success": True, "data": foreshadows}


@router.post("/foreshadows")
async def create_foreshadow(body: ForeshadowCreate, db: Database = Depends(get_db)):
    foreshadow = await db.create_foreshadow(body.model_dump())
    return {"success": True, "data": foreshadow}


@router.put("/foreshadows/{fid}")
async def update_foreshadow(fid: str, body: ForeshadowUpdate, db: Database = Depends(get_db)):
    foreshadow = await db.update_foreshadow(fid, body.model_dump(exclude_none=True))
    return {"success": True, "data": foreshadow}


@router.delete("/foreshadows/{fid}")
async def delete_foreshadow(fid: str, db: Database = Depends(get_db)):
    await db.delete_foreshadow(fid)
    return {"success": True}


# ══════ Settings ══════

@router.get("/settings")
async def get_settings(db: Database = Depends(get_db)):
    settings = await db.get_settings()
    return {"success": True, "data": settings}


@router.put("/settings")
async def update_settings(body: dict, db: Database = Depends(get_db)):
    from backend.config import update_llm_config

    settings = await db.update_settings(body)
    # Reflect changes in-memory immediately (no restart needed)
    for k, v in body.items():
        update_llm_config(k, str(v))
    return {"success": True, "data": settings}