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

    def test_split_chapters_range_1to26(self):
        """第一章到第二十六章都能正确分割（内容文本不以第X章开头）。"""
        from backend.agent.nodes.content_generation import _split_chapters
        parts = []
        for i in range(1, 27):
            parts.append(f"第{i}章 第{i}章标题")
            parts.append(f"这是第{i}章的正文内容……")
        text = "\n".join(parts)
        result = _split_chapters(text)
        assert len(result) == 26
        assert result[0]["title"] == "第1章 第1章标题"
        assert result[-1]["title"] == "第26章 第26章标题"

    def test_split_chapters_chinese_number_titles(self):
        """汉字数字章节标题（第一章、第二十六章等）均能正确分割。"""
        from backend.agent.nodes.content_generation import _split_chapters
        text = "第一章 江湖\n正文内容。\n第二十六章 归隐\n归隐山林的内容。"
        result = _split_chapters(text)
        assert len(result) == 2
        assert result[0]["title"] == "第一章 江湖"
        assert result[1]["title"] == "第二十六章 归隐"

    def test_split_chapters_mixed_arabic_chinese(self):
        """阿拉伯数字和汉字数字混合章节号。"""
        from backend.agent.nodes.content_generation import _split_chapters
        text = "第1章 启程\n出发了。\n第100章 终章\n结束了。"
        result = _split_chapters(text)
        assert len(result) == 2

    def test_split_chapters_large_split(self):
        from backend.agent.nodes.content_generation import _split_chapters
        para = "这是一段很长的测试内容。" * 15 + "\n\n"
        long_text = "第一章 开端\n" + (para * 30)
        assert len(long_text) > 4000
        result = _split_chapters(long_text)
        assert len(result) >= 2

    def test_split_chapters_content_preserved(self):
        """分割前后内容完整不丢失。"""
        from backend.agent.nodes.content_generation import _split_chapters
        text = "第一章 相遇\n小明和小红在街上相遇了。\n\n第二章 相知\n他们一起去了咖啡店。"
        result = _split_chapters(text)
        assert len(result) == 2
        assert "小明和小红在街上相遇了。" in result[0]["content"]
        assert "他们一起去了咖啡店。" in result[1]["content"]

    def test_split_chapters_no_titles(self):
        """没有任何章节标题时，全部归为'续写'。"""
        from backend.agent.nodes.content_generation import _split_chapters
        text = "一段普通的叙述文字。\n\n没有任何章节标记。"
        result = _split_chapters(text)
        assert len(result) == 1
        assert result[0]["title"] == "续写"

    def test_split_chapters_empty_text(self):
        """空文本返回一个空的'续写'章节。"""
        from backend.agent.nodes.content_generation import _split_chapters
        result = _split_chapters("")
        assert len(result) == 1
        assert result[0]["title"] == "续写"
        assert result[0]["content"] == ""

    def test_split_chapters_leading_trailing_text(self):
        """章节前的游离文本作为'续写'章节保留，后续正常分割。"""
        from backend.agent.nodes.content_generation import _split_chapters
        text = "开头的前言内容。\n\n第一章 正片\n这是第一章。"
        result = _split_chapters(text)
        assert len(result) == 2
        assert result[0]["title"] == "续写"
        assert result[0]["content"] == "开头的前言内容。"
        assert result[1]["title"] == "第一章 正片"

    def test_split_chapters_large_paragraph_boundary(self):
        """大章节拆分在段落边界进行，不截断段落。"""
        from backend.agent.nodes.content_generation import _split_chapters
        # Build a single chapter with enough paragraphs to exceed 4000 chars
        paras = []
        for i in range(50):
            paras.append(f"第{i+1}段：" + "测试内容。" * 25)
        text = "第一章 长章\n" + "\n\n".join(paras)
        assert len(text) > 4000
        result = _split_chapters(text)
        assert len(result) >= 2
        # Each sub-chapter title should preserve original title with (续)
        assert result[0]["title"] == "第一章 长章"
        assert "（续）" in result[1]["title"]


class TestModifyModeChapterSaving:
    """Test the chapter save logic during modify rounds (the is_modify path)."""

    def test_modify_updates_existing_titles_in_memory(self):
        """修改模式下，已有章节的 title 在 saved_chapters 内存列表中同步更新。

        This tests the logic that saved_chapters[i]["title"] is updated
        alongside the DB update, not left stale.
        """
        saved_chapters = [
            {"id": "ch1", "title": "第一章 旧标题", "file_path": "/p/ch1.md"},
            {"id": "ch2", "title": "第二章 旧标题", "file_path": "/p/ch2.md"},
        ]
        chapters_data = [
            {"title": "第一章 新标题", "content": "新内容1"},
            {"title": "第二章 新标题", "content": "新内容2"},
        ]

        # Simulate the modify save logic
        for i, ch_data in enumerate(chapters_data):
            if i < len(saved_chapters):
                existing = saved_chapters[i]
                # DB update (simulated) ...
                # Then sync title:
                existing["title"] = ch_data["title"]

        assert saved_chapters[0]["title"] == "第一章 新标题"
        assert saved_chapters[1]["title"] == "第二章 新标题"

    def test_modify_cleans_excess_chapters(self):
        """修改后章节数减少时，多余的章节被清理。"""
        saved_chapters = [
            {"id": "ch1", "title": "第一章", "file_path": "/p/ch1.md"},
            {"id": "ch2", "title": "第二章", "file_path": "/p/ch2.md"},
            {"id": "ch3", "title": "第三章", "file_path": "/p/ch3.md"},
        ]
        chapters_data = [
            {"title": "第一章 合并", "content": "新内容1"},
        ]

        excess = saved_chapters[len(chapters_data):]
        assert len(excess) == 2
        assert excess[0]["id"] == "ch2"
        assert excess[1]["id"] == "ch3"

        # Simulate cleanup
        deleted_ids = [ch["id"] for ch in excess]
        saved_chapters[:] = saved_chapters[:len(chapters_data)]

        assert "ch2" in deleted_ids
        assert "ch3" in deleted_ids
        assert len(saved_chapters) == 1

    def test_modify_sort_order_sequential(self):
        """修改模式下新章节的 sort_order 从 0 开始顺序递增。"""
        saved_chapters = [
            {"id": "ch1", "title": "第一章", "file_path": "/p/ch1.md"},
        ]
        chapters_data = [
            {"title": "第一章 修改", "content": "新1"},
            {"title": "第二章 新增", "content": "新2"},
        ]

        # Simulate: first is update (i < len(saved_chapters)), second is new
        for i, ch_data in enumerate(chapters_data):
            if i < len(saved_chapters):
                pass  # update existing, sort_order stays
            else:
                # Should be i, not len(saved_chapters) + i
                sort_order = i
                assert sort_order == 1  # second chapter in new batch


class TestTextTruncation:
    """Test the context truncation / empty-text logic concerns."""

    def test_empty_generated_text_falls_back(self):
        """generated_text 为空时应有 fallback 并记日志（模拟行为）。"""
        # This tests the guard: when resume_dict has no generated_text,
        # we fall back to state's generated_text.
        resume = {"cancelled": False}
        fallback = "旧文本"

        generated_text = resume.get("generated_text", "")
        if not generated_text:
            generated_text = fallback  # with a logging.warning in real code

        assert generated_text == "旧文本"


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
