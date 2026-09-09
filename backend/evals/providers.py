"""Deterministic LLM providers for graph evaluation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from backend.llm.provider import LLMProvider


class ScriptedToolProvider(LLMProvider):
    """Return scripted decisions and record every tool-enabled request."""

    def __init__(
        self,
        decisions: list[dict[str, Any]] | None = None,
        resolver: (
            Callable[[list[dict[str, Any]], list[dict[str, Any]]], dict[str, Any] | Awaitable[dict[str, Any]]]
            | None
        ) = None,
    ):
        self.decisions = list(decisions or [])
        self.resolver = resolver
        self.requests: list[dict[str, Any]] = []
        self.call_count = 0

    async def chat(self, messages: list[dict], temperature: float = 0.8, max_tokens: int = 8192) -> str:
        raise AssertionError("Tool graph evaluation should use chat_with_tools")

    async def chat_json(self, messages: list[dict], temperature: float = 0.3, max_tokens: int = 4096) -> dict:
        raise AssertionError("Tool graph evaluation should use chat_with_tools")

    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        self.call_count += 1
        request = {
            "round": self.call_count,
            "messages": messages,
            "tools": tools or [],
        }
        self.requests.append(request)
        if self.resolver is not None:
            decision = self.resolver(self.requests[-1]["messages"], self.requests[-1]["tools"])
            if hasattr(decision, "__await__"):
                decision = await decision
        elif self.decisions:
            decision = self.decisions.pop(0)
        else:
            decision = {"type": "text", "content": "done"}
        return decision
