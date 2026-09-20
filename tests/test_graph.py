import sys
import os
import logging
from pathlib import Path

# 将项目根目录加入 sys.path，确保能找到 backend 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.react_agent.graph import build_react_graph
from backend.agent.graph import continue_writing_graph

logger = logging.getLogger(__name__)
RESOURCES_DIR = Path(__file__).resolve().parents[1] / "resources"


def save_graph_diagram(graph, base_name: str) -> Path:
    try:
        payload = graph.get_graph().draw_mermaid_png()
        path = RESOURCES_DIR / f"{base_name}.png"
        logger.info("Rendered graph PNG: %s", path)
    except Exception as exc:
        # draw_mermaid_png uses mermaid.ink by default, which is not
        # available in restricted-network environments.
        logger.warning("PNG rendering unavailable, saving Mermaid source: %s", exc)
        payload = graph.get_graph().draw_mermaid().encode("utf-8")
        path = RESOURCES_DIR / f"{base_name}.mmd"

    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def test_generation_graph_mermaid():
    mermaid = continue_writing_graph.get_graph().draw_mermaid()
    assert "init_check" in mermaid
    assert "content_generation" in mermaid


def test_react_graph_mermaid():
    graph = build_react_graph()
    mermaid = graph.get_graph().draw_mermaid()
    assert "validate_input" in mermaid
    assert "tools" in mermaid


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    save_graph_diagram(continue_writing_graph, "my_graph")
    graph2 = build_react_graph()
    save_graph_diagram(graph2, "my_graph2")
