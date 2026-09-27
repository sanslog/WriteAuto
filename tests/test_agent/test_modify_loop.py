"""Tests for the modify-loop gate and its integration with the workflow state.

The workflow must never accumulate conversation history: a user revision
request lives in a single ``modification_opinion`` field and the loop only
continues while that field actually carries content.
"""

from backend.agent.graph import (
    _route_after_content_judge,
    _route_after_modify_loop,
    continue_writing_graph,
)
from backend.agent.nodes.modify_loop import modify_loop_node
from backend.config import MAX_MODIFICATION_COUNT
from backend.llm.prompts import build_generation_prompt


def _state(**overrides):
    base = {
        "novel_id": "novel-1",
        "generation_id": "gen-1",
        "modification_count": 0,
        "modification_opinion": "",
        "enter_loop": False,
        "should_end": False,
    }
    base.update(overrides)
    return base


class TestModifyLoopGate:
    def test_continues_when_opinion_present(self):
        result = modify_loop_node(_state(modification_opinion="加强悬念"))

        assert result["enter_loop"] is True
        assert result["should_end"] is False
        assert result["modification_count"] == 1

    def test_ends_when_opinion_missing(self):
        result = modify_loop_node(_state(modification_count=3))

        assert result["enter_loop"] is False
        assert result["should_end"] is True
        assert result["modification_opinion"] == ""

    def test_ends_when_opinion_is_blank(self):
        result = modify_loop_node(_state(modification_opinion="\n\t  "))

        assert result["enter_loop"] is False
        assert result["should_end"] is True

    def test_ends_at_budget(self):
        result = modify_loop_node(
            _state(
                modification_count=MAX_MODIFICATION_COUNT,
                modification_opinion="继续修改",
            )
        )

        assert result["enter_loop"] is False
        assert result["should_end"] is True

    def test_last_allowed_round_still_runs(self):
        result = modify_loop_node(
            _state(
                modification_count=MAX_MODIFICATION_COUNT - 1,
                modification_opinion="最后一轮",
            )
        )

        assert result["enter_loop"] is True
        assert result["modification_count"] == MAX_MODIFICATION_COUNT

    def test_never_writes_messages(self):
        result = modify_loop_node(_state(modification_opinion="改"))

        assert "messages" not in result
        assert list(result) == [
            "enter_loop",
            "should_end",
            "modification_count",
            "modification_opinion",
        ]


class TestModifyLoopBoundedState:
    def test_repeated_rounds_do_not_grow_state(self):
        """Ten rounds must not add any state key (no history accumulation)."""
        state = _state(modification_opinion="每一轮都要求精简")
        for round_index in range(10):
            result = modify_loop_node(state)
            if result["should_end"]:
                break
            state = {**state, **result, "modification_opinion": "每一轮都要求精简"}

        assert set(state) == set(_state())
        assert state["modification_count"] == 10


class TestGraphRouting:
    def test_content_judge_routes_to_end_when_done(self):
        assert _route_after_content_judge(_state(should_end=True)) == "__end__"
        assert _route_after_content_judge(_state(should_end=False)) == "modify_loop"

    def test_modify_loop_routes_to_mcp_only_on_continue(self):
        assert _route_after_modify_loop(_state(enter_loop=True)) == "mcp_tool"
        assert _route_after_modify_loop(_state(enter_loop=False)) == "__end__"
        assert (
            _route_after_modify_loop(_state(enter_loop=True, should_end=True))
            == "__end__"
        )

    def test_graph_has_conditional_edge_from_modify_loop(self):
        mermaid = continue_writing_graph.get_graph().draw_mermaid()

        assert "modify_loop" in mermaid
        assert "mcp_tool" in mermaid
        edges = continue_writing_graph.get_graph().edges
        assert any(
            edge.source == "modify_loop" and edge.target == "mcp_tool"
            for edge in edges
        )


class TestPromptUsesPromotedOpinion:
    def test_opinion_injected_in_modify_mode(self):
        _, user = build_generation_prompt(
            base_prompt="",
            style_of_writing="",
            world_outlook="",
            outline="",
            detailed_outline="",
            next_node_title="",
            main_character_design="",
            foreshadow="",
            context="",
            modification_opinion="把结尾改得更有力",
            enter_loop=True,
            previous_generated_text="第一章 开端\n正文",
        )

        assert "把结尾改得更有力" in user
        assert "【修改意见】" in user

    def test_opinion_ignored_without_previous_text(self):
        _, user = build_generation_prompt(
            base_prompt="",
            style_of_writing="",
            world_outlook="",
            outline="",
            detailed_outline="",
            next_node_title="",
            main_character_design="",
            foreshadow="",
            context="",
            modification_opinion="把结尾改得更有力",
            enter_loop=True,
            previous_generated_text="",
        )

        assert "把结尾改得更有力" not in user
