"""In-memory tool executor used to evaluate ReAct orchestration safely."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

Handler = Callable[[str, dict[str, Any], dict[str, Any]], Any]


class ToolCallSandbox:
    """Replace database-backed tools with a deterministic, observable sandbox.

    A handler may return a JSON-serialisable payload or an ``AgentTool``-style
    observation. Raising marks the call failed, which lets evaluations check
    whether the graph continues after one bad tool result.
    """

    def __init__(self, handler: Handler | None = None):
        self.handler = handler
        self.calls: list[dict[str, Any]] = []
        self.observations: list[dict[str, Any]] = []
        self.store: dict[str, Any] = {}

    @property
    def tool_names(self) -> list[str]:
        return [call["name"] for call in self.calls]

    async def __call__(self, tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        observations: list[dict[str, Any]] = []
        for index, call in enumerate(tool_calls):
            function = call.get("function", {})
            name = str(call.get("name") or function.get("name") or "")
            call_id = str(call.get("id") or f"call_{index}")
            raw_arguments = call.get("arguments", function.get("arguments", {}))
            arguments, parse_error = self._parse_arguments(name, raw_arguments)

            self.calls.append(
                {
                    "call_id": call_id,
                    "name": name,
                    "arguments": arguments,
                    "parse_error": parse_error,
                }
            )
            if parse_error:
                result = {
                    "success": False,
                    "error": parse_error,
                    "error_type": "invalid_tool_call",
                }
            else:
                try:
                    payload = self.handler(name, arguments, self.store) if self.handler else {}
                    if hasattr(payload, "__await__"):
                        payload = await payload
                    result = payload if isinstance(payload, dict) and "success" in payload else {
                        "success": True,
                        "data": payload,
                    }
                except Exception as exc:
                    result = {
                        "success": False,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    }

            observation = {
                "tool_call_id": call_id,
                "tool_name": name,
                "result": result,
            }
            self.observations.append(observation)
            observations.append(observation)
            logger.debug("Tool sandbox call name=%s success=%s", name, result.get("success"))
        return observations

    @staticmethod
    def _parse_arguments(
        name: str, raw_arguments: Any
    ) -> tuple[dict[str, Any], str]:
        if raw_arguments in (None, ""):
            return {}, ""
        if isinstance(raw_arguments, dict):
            return raw_arguments, ""
        if isinstance(raw_arguments, str):
            try:
                parsed = json.loads(raw_arguments)
            except json.JSONDecodeError as exc:
                return {}, f"Arguments for {name} are not valid JSON: {exc}"
            if isinstance(parsed, dict):
                return parsed, ""
        return {}, f"Arguments for {name} must be a JSON object"
