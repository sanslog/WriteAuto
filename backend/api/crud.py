import logging

from fastapi import APIRouter, Depends

from backend.db.dependencies import get_repo_session
from backend.db.repos import (
    NovelRepo,
    PlotNodeRepo,
    ChapterRepo,
    CharacterRepo,
    ForeshadowRepo,
    SettingsRepo,
)
from backend.db.models import (
    NovelCreate, NovelUpdate,
    PlotNodeCreate, PlotNodeUpdate,
    ChapterCreate, ChapterUpdate,
    CharacterCreate, CharacterUpdate,
    ForeshadowCreate, ForeshadowUpdate,
)
from backend.config import update_llm_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["crud"])


#  Novels 

@router.get("/novels")
async def list_novels(
    repo: NovelRepo = Depends(get_repo_session(NovelRepo), use_cache=False),
):
    novels = await repo.get_all()
    return {"success": True, "data": novels}


@router.get("/novels/{novel_id}")
async def get_novel(
    novel_id: str,
    repo: NovelRepo = Depends(get_repo_session(NovelRepo), use_cache=False),
):
    novel = await repo.get(novel_id)
    return {"success": True, "data": novel}


@router.post("/novels")
async def create_novel(
    body: NovelCreate,
    repo: NovelRepo = Depends(get_repo_session(NovelRepo), use_cache=False),
):
    novel = await repo.create(body.model_dump())
    return {"success": True, "data": novel}


@router.put("/novels/{novel_id}")
async def update_novel(
    novel_id: str,
    body: NovelUpdate,
    repo: NovelRepo = Depends(get_repo_session(NovelRepo), use_cache=False),
):
    novel = await repo.update(novel_id, body.model_dump(exclude_none=True))
    return {"success": True, "data": novel}


@router.delete("/novels/{novel_id}")
async def delete_novel(
    novel_id: str,
    repo: NovelRepo = Depends(get_repo_session(NovelRepo), use_cache=False),
):
    await repo.delete(novel_id)
    return {"success": True}


#  Plot Nodes 

@router.get("/novels/{novel_id}/outline")
async def list_plot_nodes(
    novel_id: str,
    repo: PlotNodeRepo = Depends(get_repo_session(PlotNodeRepo), use_cache=False),
):
    nodes = await repo.get_by_novel(novel_id)
    return {"success": True, "data": nodes}


@router.post("/plot-nodes")
async def create_plot_node(
    body: PlotNodeCreate,
    repo: PlotNodeRepo = Depends(get_repo_session(PlotNodeRepo), use_cache=False),
):
    node = await repo.create(body.model_dump())
    return {"success": True, "data": node}


@router.put("/plot-nodes/{node_id}")
async def update_plot_node(
    node_id: str,
    body: PlotNodeUpdate,
    repos: tuple[PlotNodeRepo, NovelRepo] = Depends(
        get_repo_session(PlotNodeRepo, NovelRepo), use_cache=False
    ),
):
    plot_repo, novel_repo = repos
    node = await plot_repo.update(node_id, body.model_dump(exclude_none=True))
    return {"success": True, "data": node}


@router.delete("/plot-nodes/{node_id}")
async def delete_plot_node(
    node_id: str,
    repos: tuple[PlotNodeRepo, NovelRepo] = Depends(
        get_repo_session(PlotNodeRepo, NovelRepo), use_cache=False
    ),
):
    plot_repo, novel_repo = repos
    node = await plot_repo.get(node_id)
    if not node:
        return {"success": False, "error": "?????"}

    novel_id = node["novel_id"]
    deleted_order = node["sort_order"]

    await plot_repo.delete(node_id)

    # ?? Cursor correction ??
    novel = await novel_repo.get(novel_id)
    cursor = novel.get("cursor_position", 0) if novel else 0

    if deleted_order <= cursor and cursor > 0:
        cursor -= 1

    remaining = await plot_repo.get_by_novel(novel_id)
    if cursor >= len(remaining) and remaining:
        cursor = len(remaining) - 1
    elif not remaining:
        cursor = 0

    if cursor != (novel.get("cursor_position", 0) if novel else 0):
        await novel_repo.update(novel_id, {"cursor_position": cursor})

    return {"success": True, "cursor_position": cursor}


#  Cursor 

@router.put("/novels/{novel_id}/cursor")
async def update_cursor(
    novel_id: str,
    body: dict,
    repos: tuple[NovelRepo, PlotNodeRepo] = Depends(
        get_repo_session(NovelRepo, PlotNodeRepo), use_cache=False
    ),
):
    """Manually move the cursor position."""
    novel_repo, plot_repo = repos
    cp = body.get("cursor_position", 0)
    if not isinstance(cp, int) or cp < 0:
        return {"success": False, "error": "cursor_position ???????"}

    nodes = await plot_repo.get_by_novel(novel_id)
    max_cp = max(0, len(nodes) - 1)
    if cp > max_cp:
        cp = max_cp

    novel = await novel_repo.update(novel_id, {"cursor_position": cp})
    return {"success": True, "data": novel}


#  Chapters 

@router.get("/novels/{novel_id}/chapters")
async def list_chapters(
    novel_id: str,
    repo: ChapterRepo = Depends(get_repo_session(ChapterRepo), use_cache=False),
):
    chapters = await repo.get_by_novel(novel_id)
    return {"success": True, "data": chapters}


@router.get("/chapters/{chapter_id}")
async def get_chapter(
    chapter_id: str,
    repo: ChapterRepo = Depends(get_repo_session(ChapterRepo), use_cache=False),
):
    chapter = await repo.get(chapter_id)
    return {"success": True, "data": chapter}


@router.post("/chapters")
async def create_chapter(
    body: ChapterCreate,
    repo: ChapterRepo = Depends(get_repo_session(ChapterRepo), use_cache=False),
):
    chapter = await repo.create(body.model_dump())
    return {"success": True, "data": chapter}


@router.put("/chapters/{chapter_id}")
async def update_chapter(
    chapter_id: str,
    body: ChapterUpdate,
    repo: ChapterRepo = Depends(get_repo_session(ChapterRepo), use_cache=False),
):
    chapter = await repo.update(chapter_id, body.model_dump(exclude_none=True))
    return {"success": True, "data": chapter}


@router.delete("/chapters/{chapter_id}")
async def delete_chapter(
    chapter_id: str,
    repo: ChapterRepo = Depends(get_repo_session(ChapterRepo), use_cache=False),
):
    await repo.delete(chapter_id)
    return {"success": True}


#  Characters 

@router.get("/novels/{novel_id}/characters")
async def list_characters(
    novel_id: str,
    repo: CharacterRepo = Depends(get_repo_session(CharacterRepo), use_cache=False),
):
    characters = await repo.get_by_novel(novel_id)
    return {"success": True, "data": characters}


@router.post("/characters")
async def create_character(
    body: CharacterCreate,
    repo: CharacterRepo = Depends(get_repo_session(CharacterRepo), use_cache=False),
):
    character = await repo.create(body.model_dump())
    return {"success": True, "data": character}


@router.put("/characters/{char_id}")
async def update_character(
    char_id: str,
    body: CharacterUpdate,
    repo: CharacterRepo = Depends(get_repo_session(CharacterRepo), use_cache=False),
):
    character = await repo.update(char_id, body.model_dump(exclude_none=True))
    return {"success": True, "data": character}


@router.delete("/characters/{char_id}")
async def delete_character(
    char_id: str,
    repo: CharacterRepo = Depends(get_repo_session(CharacterRepo), use_cache=False),
):
    await repo.delete(char_id)
    return {"success": True}


#  Foreshadows 

@router.get("/novels/{novel_id}/foreshadows")
async def list_foreshadows(
    novel_id: str,
    repo: ForeshadowRepo = Depends(get_repo_session(ForeshadowRepo), use_cache=False),
):
    foreshadows = await repo.get_by_novel(novel_id)
    return {"success": True, "data": foreshadows}


@router.post("/foreshadows")
async def create_foreshadow(
    body: ForeshadowCreate,
    repo: ForeshadowRepo = Depends(get_repo_session(ForeshadowRepo), use_cache=False),
):
    foreshadow = await repo.create(body.model_dump())
    return {"success": True, "data": foreshadow}


@router.put("/foreshadows/{fid}")
async def update_foreshadow(
    fid: str,
    body: ForeshadowUpdate,
    repo: ForeshadowRepo = Depends(get_repo_session(ForeshadowRepo), use_cache=False),
):
    foreshadow = await repo.update(fid, body.model_dump(exclude_none=True))
    return {"success": True, "data": foreshadow}


@router.delete("/foreshadows/{fid}")
async def delete_foreshadow(
    fid: str,
    repo: ForeshadowRepo = Depends(get_repo_session(ForeshadowRepo), use_cache=False),
):
    await repo.delete(fid)
    return {"success": True}


#  Settings 

@router.get("/settings")
async def get_settings(
    repo: SettingsRepo = Depends(get_repo_session(SettingsRepo), use_cache=False),
):
    settings = await repo.get_all()
    return {"success": True, "data": settings}


@router.put("/settings")
async def update_settings(
    body: dict,
    repos: tuple[SettingsRepo, NovelRepo] = Depends(
        get_repo_session(SettingsRepo, NovelRepo), use_cache=False
    ),
):
    settings_repo = repos[0]
    settings = await settings_repo.update(body)
    for k, v in body.items():
        update_llm_config(k, str(v))
    return {"success": True, "data": settings}
