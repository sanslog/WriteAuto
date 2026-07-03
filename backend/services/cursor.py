import logging

from backend.db.database import Database

logger = logging.getLogger(__name__)


async def get_cursor_info(db:Database, novel_id: str) -> dict:
    novel = await db.get_novel(novel_id)
    if not novel:
        return {}

    cursor = novel.get("cursor_position", 0)
    nodes = await db.get_plot_nodes(novel_id)

    outline_lines = []
    detailed_outline = ""
    next_node_title = ""

    for i, node in enumerate(nodes):
        outline_lines.append(f"{i+1}.节点名称：{node['title']}，内容梗概：{node['summary'] or '无'}")
        if i == cursor:
            detailed_outline += f"当前节点：► {i+1}.节点名称：{node['title']} ◄\n节点细纲："
            detailed_outline += node.get("detailed_outline", "")
        if i == cursor + 1:
            next_node_title = node.get("title", "")

    if cursor >= len(nodes) and nodes:
        cursor = len(nodes) - 1
        await db.update_novel(novel_id, {"cursor_position": cursor})
        detailed_outline = nodes[cursor].get("detailed_outline", "")

    logger.debug("cursor info — outline:\n%s\n\ndetailed:\n%s\ncursor: %d",
                 "\n".join(outline_lines), detailed_outline[:200], cursor)

    return {
        "outline": "\n".join(outline_lines),
        "detailed_outline": detailed_outline,
        "cursor_position": cursor,
        "plot_nodes_count": len(nodes),
        "next_node_title": next_node_title,
    }
