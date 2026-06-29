"""Unit tests for agent nodes."""

import asyncio
import pytest


def make_state(**overrides):
    defaults = {
        "base_prompt": "",
        "style_of_writing": "",
        "world_outlook": "",
        "outline": "",
        "detailed_outline": "",
        "cursor_position": 0,
        "plot_nodes_count": 0,
        "next_node_title": "",
        "main_character_design": "",
        "foreshadow": "",
        "context": "",
        "chapter_ids": [],
        "foreshadow_ids": [],
        "generated_text": "",
        "chapter_titles": [],
        "character_states_json": "",
        "enter_loop": False,
        "should_end": False,
        "modification_count": 0,
        "user_input_text": "",
        "unlawful": False,
        "unlaw_reason": "",
        "messages": [],
        "novel_id": "test-novel-1",
        "generation_id": "test-gen-1",
        "_saved_chapters": [],
        "_cancelled": False,
    }
    defaults.update(overrides)
    return defaults


class TestContentGenerationUtils:
    def test_count_chinese(self):
        from backend.agent.nodes.content_generation import _count_chinese
        assert _count_chinese("你好世界") == 4
        assert _count_chinese("Hello 世界") == 2
        assert _count_chinese("abc") == 0

    def test_split_chapters_single(self):
        from backend.agent.nodes.content_generation import _split_chapters
        result = _split_chapters("这是一段测试文本。")
        assert len(result) == 1
        assert result[0]["content"] == "这是一段测试文本。"

    def test_split_chapters_multi(self):
        from backend.agent.nodes.content_generation import _split_chapters
        text = "第一章 开始\n这是第一章的内容。\n第二章 继续\n这是第二章的内容。"
        result = _split_chapters(text)
        assert len(result) == 2
        assert "第一章" in result[0]["title"]
        assert "第二章" in result[1]["title"]

    def test_split_chapters_large_split(self):
        from backend.agent.nodes.content_generation import _split_chapters
        para = "这是一段很长的测试内容。" * 15 + "\n\n"
        long_text = "第一章 开端\n" + (para * 30)
        assert len(long_text) > 4000
        result = _split_chapters(long_text)
        assert len(result) >= 2


class TestStateDefaults:
    def test_state_creation(self):
        state = make_state()
        assert state["novel_id"] == "test-novel-1"
        assert state["modification_count"] == 0
        assert state["enter_loop"] is False

    def test_state_chapter_ids(self):
        state = make_state(chapter_ids=["ch1", "ch2"])
        assert len(state["chapter_ids"]) == 2


class TestGraphStructure:
    def test_graph_compiles(self):
        from backend.agent.graph import continue_writing_graph
        nodes = list(continue_writing_graph.nodes.keys())
        assert "init_check" in nodes
        assert "character_fetch" in nodes
        assert "content_generation" in nodes
        assert "content_judge" in nodes
        assert "modify_loop" in nodes


class TestModifyLoop:
    def test_modify_loop_updates_state(self):
        from backend.agent.nodes.modify_loop import modify_loop_node
        state = make_state(modification_count=2, user_input_text="改一下")
        result = modify_loop_node(state)
        assert result["enter_loop"] is True
        assert len(result["messages"]) == 1
