from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from backend.agent.state import State
from backend.agent.nodes.init_check import init_check_node
from backend.agent.nodes.character_fetch import character_fetch_node
from backend.agent.nodes.injection_context import injection_context_node
from backend.agent.nodes.injection_foreshadow import injection_foreshadow_node
from backend.agent.nodes.content_generation import content_generation_node
from backend.agent.nodes.content_judge import content_judge_node
from backend.agent.nodes.modify_loop import modify_loop_node


def _route_after_character_fetch(state: State) -> str:
    if state.get("unlawful"):
        return END
    return "injection_context"


def _route_after_content_judge(state: State) -> str:
    if state.get("should_end"):
        return END
    return "modify_loop"


checkpointer = MemorySaver()


def build_graph() -> CompiledStateGraph:
    builder = StateGraph(State)

    builder.add_node("init_check", init_check_node)
    builder.add_node("character_fetch", character_fetch_node)
    builder.add_node("injection_context", injection_context_node)
    builder.add_node("injection_foreshadow", injection_foreshadow_node)
    builder.add_node("content_generation", content_generation_node)
    builder.add_node("content_judge", content_judge_node)
    builder.add_node("modify_loop", modify_loop_node)

    builder.add_edge(START, "init_check")
    builder.add_edge("init_check", "character_fetch")

    builder.add_conditional_edges(
        "character_fetch",
        _route_after_character_fetch,
        {"injection_context": "injection_context", END: END},
    )

    builder.add_edge("injection_context", "injection_foreshadow")
    builder.add_edge("injection_foreshadow", "content_generation")
    builder.add_edge("content_generation", "content_judge")

    builder.add_conditional_edges(
        "content_judge",
        _route_after_content_judge,
        {"modify_loop": "modify_loop", END: END},
    )

    builder.add_edge("modify_loop", "content_generation")

    return builder.compile(checkpointer=checkpointer)


continue_writing_graph : CompiledStateGraph= build_graph()