from backend.react_agent.prompts import (
    build_react_progress_hint,
    build_react_system_prompt,
    build_react_user_prompt,
)


def test_user_prompt_places_stable_prefix_before_variable_content():
    prompt_a = build_react_user_prompt("写一个科幻故事")
    prompt_b = build_react_user_prompt(
        "写一个武侠故事",
        novel_id="novel-123",
        cursor_position=2,
        outline_nodes_count=10,
        outline_planned=True,
        task_saved=True,
    )

    # The static instruction block must lead so prefix-cache can match it.
    assert prompt_a.startswith("工作流：")
    assert prompt_b.startswith("工作流：")
    # Variable content follows at the tail.
    assert prompt_a.endswith("用户请求：写一个科幻故事")
    assert prompt_b.endswith("用户请求：写一个武侠故事")


def test_user_prompt_reuses_tool_state_in_context():
    prompt = build_react_user_prompt(
        "继续写",
        novel_id="novel-456",
        cursor_position=3,
        outline_nodes_count=12,
        outline_planned=True,
        task_saved=True,
    )

    assert "novel_id=novel-456" in prompt
    assert "大纲节点=12" in prompt
    assert "游标=3" in prompt
    assert "已有正文" in prompt
    assert "已完成" not in prompt


def test_user_prompt_marks_completed_outline():
    prompt = build_react_user_prompt(
        "继续写",
        novel_id="novel-789",
        outline_nodes_count=8,
        outline_planned=True,
        outline_complete=True,
    )

    assert "已完成" in prompt
    assert "游标=" not in prompt


def test_user_prompt_omits_empty_state_fields():
    prompt = build_react_user_prompt("新故事")

    assert "项目状态" not in prompt
    assert "novel_id" not in prompt
    assert prompt == (
        "工作流：先拆解剧情大纲，再按当前游标循环生成并保存章节，"
        "同步角色状态和伏笔，直到大纲完成或收到中止信号。\n"
        "用户请求：新故事"
    )


def test_progress_hint_for_unplanned_outline():
    hint = build_react_progress_hint()

    assert "create_plot_node" in hint
    assert "大纲未建立" in hint


def test_progress_hint_for_active_writing():
    hint = build_react_progress_hint(
        outline_planned=True,
        outline_complete=False,
        task_saved=True,
        cursor_position=5,
        outline_nodes_count=20,
    )

    assert "游标=5" in hint
    assert "大纲节点=20" in hint
    assert "已有章节" in hint
    assert "get_writing_context" in hint
    assert "create_chapter" in hint
    assert "complete_current_plot_node" in hint


def test_progress_hint_for_completed_outline():
    hint = build_react_progress_hint(
        outline_planned=True,
        outline_complete=True,
    )

    assert hint == "大纲已完成，停止创作。"


def test_system_prompt_remains_unchanged_contract():
    prompt = build_react_system_prompt()

    # Verify the durable tool names and safety rules are still present.
    for key in (
        "create_novel",
        "create_chapter",
        "get_writing_context",
        "complete_current_plot_node",
        "剧情游标",
        "不得编造工具返回值",
    ):
        assert key in prompt
