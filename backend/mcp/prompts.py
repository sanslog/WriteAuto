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
        "- Respond in the same language as the novel text.\n\n"
        "Error handling:\n"
        "- If a tool returns an error message, read it carefully. The error format is:\n"
        "  Error [ErrorType]: description\n"
        "  Common ErrorTypes: TIMEOUT, CONNECTION_REFUSED, HTTP_429 (rate limit),\n"
        "  HTTP_500/502/503/504 (server error), INVALID_RESPONSE_JSON, ValueError,\n"
        "  RuntimeError, UNKNOWN\n"
        "- For CONNECTION_REFUSED or TIMEOUT: the service may be temporarily down.\n"
        "  You may retry once with a different tool, or skip if the information is "
        "not critical.\n"
        "- For HTTP_429 (rate limit): back off and do NOT retry the same tool "
        "immediately. Try a different tool or wait.\n"
        "- For HTTP_5xx: the server-side error is transient. You may retry after "
        "a brief delay (in the next round).\n"
        "- For ValueError or 'not found': you may have the wrong service_id or "
        "tool_name, or the arguments are invalid. Adjust your approach if retrying.\n"
        "- If a tool persistently fails after retries, fall back to using your own "
        "knowledge and note the information gap."
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
