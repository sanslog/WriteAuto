"""LangGraph wiring for the one-sentence novel-writing ReAct agent."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.llm.factory import create_llm_provider
from backend.llm.provider import LLMProvider
from backend.react_agent.nodes import (
    finalize_node,
    make_agent_node,
    tool_node,
    validate_input_node,
)
from backend.react_agent.state import DEFAULT_MAX_REACT_ITERATIONS, ReactAgentState

logger = logging.getLogger(__name__)


def _route_after_validation(state: ReactAgentState) -> str:
    if state.get("should_end"):
        return "finalize"
    return "agent"


def _route_after_agent(state: ReactAgentState) -> str:
    if state.get("should_end"):
        return "finalize"
    if state.get("tool_calls"):
        return "tools"
    return "agent"


def _route_after_tools(state: ReactAgentState) -> str:
    if state.get("should_end") or state.get("cancelled"):
        return "finalize"
    if state.get("outline_complete"):
        return "finalize"
    iteration = int(state.get("iteration", 0))
    max_iterations = max(
        1,
        int(state.get("max_iterations") or DEFAULT_MAX_REACT_ITERATIONS),
    )
    if iteration >= max_iterations:
        return "finalize"
    return "agent"


def build_react_graph(provider: LLMProvider | None = None) -> CompiledStateGraph:
    """Build a checkpointed one-sentence writing graph.

    A provider can be injected for tests and alternative deployments; by
    default the graph uses the application-wide OpenAI-compatible provider.
    """

    llm = provider or create_llm_provider()
    builder = StateGraph(ReactAgentState)

    builder.add_node("validate_input", validate_input_node)
    builder.add_node("agent", make_agent_node(llm))
    builder.add_node("tools", tool_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "validate_input")
    builder.add_conditional_edges(
        "validate_input",
        _route_after_validation,
        {"agent": "agent", "finalize": "finalize"},
    )
    builder.add_conditional_edges(
        "agent",
        _route_after_agent,
        {"agent": "agent", "tools": "tools", "finalize": "finalize"},
    )
    builder.add_conditional_edges(
        "tools",
        _route_after_tools,
        {"agent": "agent", "finalize": "finalize"},
    )
    builder.add_edge("finalize", END)

    graph = builder.compile(checkpointer=MemorySaver())
    logger.info("One-sentence writing ReAct graph built")
    return graph


one_sentence_writing_graph: CompiledStateGraph = build_react_graph()


async def run_react_agent(
    user_request: str,
    *,
    session_id: str | None = None,
    novel_id: str = "",
    generation_id: str = "",
    max_iterations: int = DEFAULT_MAX_REACT_ITERATIONS,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """Run a disposable graph instance and return the final state."""

    graph = build_react_graph(provider=provider)
    thread_id = session_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    logger.info("ReAct agent run started: session_id=%s", thread_id)
    return await graph.ainvoke(
        {
            "session_id": thread_id,
            "generation_id": generation_id,
            "user_request": user_request,
            "novel_id": novel_id,
            "max_iterations": max_iterations,
        },
        config=config,
    )
