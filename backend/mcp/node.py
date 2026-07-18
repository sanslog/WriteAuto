"""Production-grade MCP tool node with native function calling + ReAct loop.

Placed between content_generation and content_judge.

Flow:
1. Convert registered MCP tools into OpenAI-compatible tools[] format
2. Pass to LLM via chat_with_tools() — model decides if/which tool to call
3. If tool_calls returned → execute each tool → feed result back as observation
4. Repeat step 2-3 (max 5 rounds, ReAct style)
5. When LLM responds with text (or max rounds reached) → summarise
6. Tool results + summary stored in mcp_results + mcp_context (fed back to generation)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.agent.state import State
from backend.mcp.service import list_services, execute_tool
from backend.config import LLM_GENERATION_MAX_TOKENS

logger = logging.getLogger(__name__)

_MAX_REACT_ROUNDS = 5
_MAX_TOOL_RESULT_CHARS = 2000


def _mcp_tools_to_openai_tools(services: list[dict]) -> list[dict]:
    """Convert MCP service tool definitions to OpenAI tools[] format."""
    openai_tools = []
    for svc in services:
        svc_id = svc.get("id", "")
        svc_name = svc.get("name", svc_id)
        for tool in svc.get("tools", []):
            t = tool if isinstance(tool, dict) else tool.model_dump()
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": f"{svc_id}__{t['name']}",
                    "description": t.get("description", f"Tool from {svc_name}"),
                    "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
                },
            })
    return openai_tools


def _parse_tool_name(full_name: str) -> tuple[str, str]:
    """Parse 'service_id__tool_name' back into (service_id, tool_name)."""
    if "__" in full_name:
        parts = full_name.split("__", 1)
        return parts[0], parts[1]
    return "", full_name


async def mcp_tool_node(state: State) -> dict[str, Any]:
    """Production ReAct tool node.

    Returns:
        mcp_results: list of tool execution results
        mcp_context: formatted tool result text for injection into next generation
    """
    if state.get("_cancelled"):
        return {"mcp_results": [], "mcp_context": ""}

    generated_text = state.get("generated_text", "")
    if not generated_text:
        return {"mcp_results": [], "mcp_context": ""}

    services = list_services()
    enabled = [s for s in services if s.get("enabled", True)]
    if not enabled:
        return {"mcp_results": [], "mcp_context": ""}

    openai_tools = _mcp_tools_to_openai_tools(enabled)
    if not openai_tools:
        return {"mcp_results": [], "mcp_context": ""}

    logger.info("MCP ReAct starting with %d tool(s) available", len(openai_tools))

    # ── System prompt for the tool-using agent ──
    system = (
        "You are a research assistant integrated into a novel-writing system. "
        "You have access to external tools that can fetch real-world information, "
        "check facts, or enrich the generated novel content.\n\n"
        "Guidelines:\n"
        "- Only call tools when the text genuinely needs external data.\n"
        "- If you call a tool, wait for the result and decide if more info is needed.\n"
        "- When you have enough information (or none is needed), summarise briefly.\n"
        "- Respond in the same language as the novel text."
    )

    # ── ReAct loop ──
    messages: list[dict] = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                f"Here is the generated novel text (last 4000 chars):\n"
                f"{generated_text[-4000:]}\n\n"
                f"Chapter titles: {json.dumps(state.get('chapter_titles', []), ensure_ascii=False)}\n"
                f"Novel context: {state.get('context', '')[:1500]}\n\n"
                "Decide if any external tool needs to be called to enrich this content. "
                "If yes, use the appropriate tool. If not, just respond with 'No tools needed.'"
            ),
        },
    ]

    all_results: list[dict] = []

    for _round in range(_MAX_REACT_ROUNDS):
        # LLM decides: text response or tool call
        decision = await _call_llm_with_tools(messages, openai_tools)

        if decision["type"] == "text":
            # LLM says done
            conclusion = decision["content"]
            logger.info("MCP ReAct finished at round %d: %s", _round + 1, conclusion[:100])
            messages.append({"role": "assistant", "content": conclusion})
            break

        # LLM wants to call tools
        tool_calls = decision["calls"]
        logger.info("MCP ReAct round %d: %d tool call(s)", _round + 1, len(tool_calls))

        # Build assistant message with tool_calls
        assistant_msg: dict[str, Any] = {"role": "assistant", "content": None}
        openai_tool_calls = []
        for tc in tool_calls:
            openai_tool_calls.append({
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["function"]["name"],
                    "arguments": json.dumps(tc["function"]["arguments"], ensure_ascii=False),
                },
            })
        assistant_msg["tool_calls"] = openai_tool_calls
        messages.append(assistant_msg)

        # Execute each tool call
        for tc in tool_calls:
            service_id, tool_name = _parse_tool_name(tc["function"]["name"])
            arguments = tc["function"]["arguments"]
            tool_call_id = tc["id"]

            logger.info("Executing tool: %s/%s", service_id, tool_name)

            if not service_id or not tool_name:
                result_text = f"Error: unknown tool '{tc['function']['name']}'"
                success = False
            else:
                try:
                    result_text = await execute_tool(service_id, tool_name, arguments, timeout=60)
                    success = True
                except Exception as exc:
                    logger.warning("Tool %s/%s failed: %s", service_id, tool_name, exc)
                    result_text = f"Error: {exc}"
                    success = False

            # Truncate long results
            if len(result_text) > _MAX_TOOL_RESULT_CHARS:
                result_text = result_text[:_MAX_TOOL_RESULT_CHARS] + "\n... (truncated)"

            all_results.append({
                "service_id": service_id,
                "tool_name": tool_name,
                "arguments": arguments,
                "result": result_text,
                "success": success,
            })

            # Feed observation back
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": result_text,
            })
    else:
        # Max rounds reached
        logger.warning("MCP ReAct reached max %d rounds, forcing conclusion", _MAX_REACT_ROUNDS)
        messages.append({"role": "user", "content": "Summarise what you found from the tools above."})

    # ── Build mcp_context for injection back into next generation ──
    if all_results:
        context_parts = ["=== MCP Tool Results ==="]
        for r in all_results:
            status = "OK" if r["success"] else "FAILED"
            context_parts.append(f"[{status}] {r['service_id']}/{r['tool_name']}: {r['result'][:500]}")
        context_parts.append("=== End MCP Results ===")
        mcp_context = "\n\n".join(context_parts)
    else:
        mcp_context = ""

    logger.info("MCP tool node complete: %d tool(s) executed", len(all_results))
    return {"mcp_results": all_results, "mcp_context": mcp_context}


async def _call_llm_with_tools(
    messages: list[dict],
    tools: list[dict] | None,
) -> dict[str, Any]:
    """Make an interrupt-based LLM call with tools.

    This uses the same interrupt/update_state pattern as the rest of the codebase.
    The actual LLM API call happens in generation.py's interrupt loop.
    """
    from langgraph.types import interrupt

    # Serialise messages for transport through interrupt
    serialised = json.dumps(messages, ensure_ascii=False, default=str)

    resume = interrupt({
        "type": "mcp_tool_call",
        "messages_json": serialised,
        "tools": tools or [],
    })
    resume_dict = resume if isinstance(resume, dict) else {}

    if resume_dict.get("cancelled") or resume_dict.get("cancel"):
        return {"type": "text", "content": ""}

    result_json = resume_dict.get("result_json", "")
    if not result_json:
        return {"type": "text", "content": ""}

    try:
        return json.loads(result_json)
    except json.JSONDecodeError:
        return {"type": "text", "content": result_json}
