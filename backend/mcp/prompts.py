"""Prompt builder for the MCP tool node.

The LLM decides whether any MCP tools should be called to enrich
the novel generation context before content generation.
"""

from __future__ import annotations

from typing import Any


def build_mcp_tool_system_prompt() -> str:
    """System prompt for the MCP ReAct agent that runs before content generation.

    The agent receives the current writing context and decides whether any
    external tools (e.g. search, database lookup, fact-checking) should be
    called to enrich the generation prompt.
    """
    return (
        "You are a research assistant integrated into a novel-writing system. "
        "Your task is to analyse the upcoming writing context and decide whether "
        "external tools should be called to enrich the content.\n\n"
        "Guidelines:\n"
        "- You receive the novel's outline, world setting, character design, foreshadow "
        "information, and previously written content.\n"
        "- Only call tools when the writing genuinely needs external data (e.g. "
        "real-world historical facts, geographical details, cultural references, "
        "weather data, or specialised terminology).\n"
        "- If you call a tool, wait for the result and decide if more info is needed.\n"
        "- When you have enough information (or none is needed), summarise briefly "
        "what was found (or state that no external data was required).\n"
        "- Respond in the same language as the novel text."
    )


def build_mcp_tool_user_prompt(state: dict[str, Any]) -> str:
    """Build the user message for the MCP ReAct agent from the current state."""
    parts = []

    if state.get("outline"):
        parts.append(f"[Novel Outline]\n{state['outline']}")

    if state.get("detailed_outline"):
        parts.append(f"[Current Plot Node - Detailed Outline]\n{state['detailed_outline']}")

    if state.get("next_node_title"):
        parts.append(f"[Next Node Title]\n{state['next_node_title']}")

    if state.get("world_outlook"):
        parts.append(f"[World Setting]\n{state['world_outlook']}")

    if state.get("style_of_writing"):
        parts.append(f"[Writing Style]\n{state['style_of_writing']}")

    if state.get("main_character_design"):
        parts.append(f"[Character Design]\n{state['main_character_design']}")

    if state.get("foreshadow"):
        parts.append(f"[Foreshadowing to Resolve]\n{state['foreshadow']}")

    if state.get("context"):
        context = state["context"]
        parts.append(f"[Previously Written Content (last {len(context)} chars)]\n{context[-3000:]}")

    parts.append(
        "\nAnalyse the above context. If any external tool can provide useful information "
        "to enrich the upcoming generation, call the appropriate tool(s). "
        "Otherwise, respond with 'No tools needed.'"
    )

    return "\n\n".join(parts)
