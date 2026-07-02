import sys
import os

# 将项目根目录加入 sys.path，确保能找到 backend 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent.graph import continue_writing_graph

if __name__ == '__main__':
    png_bytes = continue_writing_graph.get_graph().draw_mermaid_png()
    with open("./resources/my_graph.png", "wb") as f:
        f.write(png_bytes)