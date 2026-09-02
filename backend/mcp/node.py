"""Pre-generation MCP tool node with native function calling + ReAct loop.

Placed between injection_foreshadow and content_generation.

Flow:
1. Receive writing context (outline, world setting, character design, etc.)
2. Convert registered MCP tools into OpenAI-compatible tools[] format
3. Pass to LLM via chat_with_tools() — model decides if/which tool to call
4. If tool_calls returned → execute each tool → feed result back as observation
5. Repeat step 3-4 (max 5 rounds, ReAct style)
6. When LLM responds with text (or max rounds reached) → summarise
7. Tool results + summary stored in mcp_results + mcp_context (fed into generation prompt)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.agent.state import State
from backend.mcp.service import list_services, execute_tool
from backend.mcp.prompts import build_mcp_tool_system_prompt, build_mcp_tool_user_prompt

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
    """Pre-generation MCP tool node — enrich generation context before content generation.

    Reads the current writing context (outline, world setting, characters, etc.)
    and decides whether any external MCP tools should be called. Tool results
    are formatted into mcp_context, which is injected into the generation prompt.

    Returns:
        mcp_results: list of tool execution results
        mcp_context: formatted tool result text for injection into generation prompt
    """
    if state.get("_cancelled"):
        logger.debug("MCP node skipping — generation cancelled")
        return {"mcp_results": [], "mcp_context": ""}

    services = list_services()
    enabled = [s for s in services if s.get("enabled", True)]
    if not enabled:
        logger.debug("MCP node skipping — no enabled services")
        return {"mcp_results": [], "mcp_context": ""}

    openai_tools = _mcp_tools_to_openai_tools(enabled)
    if not openai_tools:
        logger.debug("MCP node skipping — no tools from enabled services")
        return {"mcp_results": [], "mcp_context": ""}

    logger.info(
        "MCP ReAct starting with %d tool(s) from %d service(s)",
        len(openai_tools),
        len(enabled),
    )

    # ── Prompts from prompts.py ──
    system = build_mcp_tool_system_prompt()
    user = build_mcp_tool_user_prompt(dict(state))

    # ── ReAct loop ──
    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    all_results: list[dict] = []

    for _round in range(_MAX_REACT_ROUNDS):
        decision = await _call_llm_with_tools(messages, openai_tools)

        if decision["type"] == "text":
            conclusion = decision["content"]
            logger.info(
                "MCP ReAct finished at round %d: %s",
                _round + 1,
                conclusion[:120],
            )
            messages.append({"role": "assistant", "content": conclusion})
            break

        # LLM wants to call tools
        tool_calls = decision["calls"]
        logger.info(
            "MCP ReAct round %d: %d tool call(s)",
            _round + 1,
            len(tool_calls),
        )

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

        for tc in tool_calls:
            service_id, tool_name = _parse_tool_name(tc["function"]["name"])
            arguments = tc["function"]["arguments"]
            tool_call_id = tc["id"]

            logger.info("Executing tool: %s/%s with args: %s", service_id, tool_name, arguments)

            if not service_id or not tool_name:
                logger.error(
                    "MCP tool call skipped: cannot parse tool name '%s'. "
                    "This usually means the tool name format 'service_id__tool_name' is incorrect.",
                    tc['function']['name'],
                )
                result_text = (
                    "Error: unknown tool. The tool name format is invalid. "
                    "Available tools are named as 'service_id__tool_name'. "
                    "Please check the tool name and try again."
                )
                success = False
            else:
                try:
                    result_text = await execute_tool(service_id, tool_name, arguments, timeout=60)
                    success = True
                    logger.info(
                        "Tool call succeeded: %s/%s (args keys=%s, result length=%d)",
                        service_id, tool_name,
                        list(arguments.keys()) if isinstance(arguments, dict) else "N/A",
                        len(result_text),
                    )
                except Exception as exc:
                    logger.warning(
                        "Tool call failed: service=%s tool=%s args=%s error_type=%s error=%s",
                        service_id, tool_name,
                        arguments,
                        type(exc).__name__,
                        exc,
                    )
                    result_text = f"Error [{type(exc).__name__}]: {exc}"
                    success = False

            if len(result_text) > _MAX_TOOL_RESULT_CHARS:
                logger.debug(
                    "Truncating tool result for %s/%s from %d to %d chars",
                    service_id, tool_name,
                    len(result_text), _MAX_TOOL_RESULT_CHARS,
                )
                result_text = result_text[:_MAX_TOOL_RESULT_CHARS] + "\n... (truncated)"

            all_results.append({
                "service_id": service_id,
                "tool_name": tool_name,
                "arguments": arguments,
                "result": result_text,
                "success": success,
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": result_text,
            })
    else:
        logger.warning(
            "MCP ReAct reached max %d rounds, forcing conclusion",
            _MAX_REACT_ROUNDS,
        )
        messages.append({
            "role": "user",
            "content": "Summarise what you found from the tools above.",
        })

    # ── Build mcp_context for injection into generation prompt ──
    if all_results:
        context_parts = ["=== MCP Tool Results ==="]
        for r in all_results:
            status = "OK" if r["success"] else "FAILED"
            context_parts.append(
                f"[{status}] {r['service_id']}/{r['tool_name']}: {r['result'][:500]}"
            )
        context_parts.append("=== End MCP Results ===")
        mcp_context = "\n\n".join(context_parts)
        logger.info(
            "MCP tool node complete: %d tool(s) executed, mcp_context length=%d",
            len(all_results),
            len(mcp_context),
        )
    else:
        mcp_context = ""
        logger.info("MCP tool node complete: no tools called")

    return {"mcp_results": all_results, "mcp_context": mcp_context}


async def _call_llm_with_tools(
    messages: list[dict],
    tools: list[dict] | None,
) -> dict[str, Any]:
    """Make an interrupt-based LLM call with tools.

    Uses the same interrupt/update_state pattern as content_generation node.
    """
    from langgraph.types import interrupt

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
