import logging

from backend.db.database import Database
from backend.db.repos import NovelRepo, PlotNodeRepo

logger = logging.getLogger(__name__)


async def get_cursor_info(db: Database, novel_id: str) -> dict:
    novel_repo = NovelRepo(db)
    plot_repo = PlotNodeRepo(db)

    novel = await novel_repo.get(novel_id)
    if not novel:
        return {}

    cursor = novel.get("cursor_position", 0)
    nodes = await plot_repo.get_by_novel(novel_id)

    outline_lines = []
    detailed_outline = ""
    next_node_title = ""

    for i, node in enumerate(nodes):
        outline_lines.append(f"{i+1}. {node['title']}: {node.get('summary', '') or 'N/A'}")
        if i == cursor:
            detailed_outline += f"Current node: >> {i+1}. {node['title']} <<\n"
            detailed_outline += node.get("detailed_outline", "")
        if i == cursor + 1:
            next_node_title = node.get("title", "")

    if cursor >= len(nodes) and nodes:
        cursor = len(nodes) - 1
        await novel_repo.update(novel_id, {"cursor_position": cursor})
        detailed_outline = nodes[cursor].get("detailed_outline", "")

    logger.debug(
        "cursor info - outline:\n%s\n\ndetailed:\n%s\ncursor: %d",
        "\n".join(outline_lines), detailed_outline[:200], cursor,
    )

    return {
        "outline": "\n".join(outline_lines),
        "detailed_outline": detailed_outline,
        "cursor_position": cursor,
        "plot_nodes_count": len(nodes),
        "next_node_title": next_node_title,
    }
