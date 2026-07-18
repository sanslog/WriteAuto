"""Abstract LLM provider interface with cancellation and tool support."""

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):

    def set_gen_id(self, gen_id: str | None) -> None:
        """Bind this provider to a generation session for cancellation support."""
        if hasattr(self, '_gen_id'):
            self._gen_id = gen_id

    @abstractmethod
    async def chat(self, messages: list[dict], temperature: float = 0.8,
                   max_tokens: int = 8192) -> str:
        ...

    @abstractmethod
    async def chat_json(self, messages: list[dict], temperature: float = 0.3,
                        max_tokens: int = 4096) -> dict:
        ...

    async def chat_stream(self, messages: list[dict], temperature: float = 0.8,
                          max_tokens: int | None = None):
        text = await self.chat(messages, temperature, max_tokens or 0)
        yield text

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Chat with tool/function calling support.

        Returns a dict with either:
          {"type": "text", "content": "..."} for text response, or
          {"type": "tool_calls", "calls": [{"id": "...", "function": {"name": "...", "arguments": {...}}}, ...]}

        Default implementation falls back to chat() with JSON parsing.
        Subclasses should override with native function calling when available.
        """
        text = await self.chat(messages, temperature, max_tokens)
        return {"type": "text", "content": text}

    async def chat_with_tools_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ):
        """Streaming variant with tool support.

        Yields tokens for text responses, or a single dict for tool_calls.
        """
        result = await self.chat_with_tools(messages, tools, temperature, max_tokens)
        if result["type"] == "text":
            yield result["content"]
        else:
            yield result

    def name(self) -> str:
        """Return a human-readable name for this provider."""
        return self.__class__.__name__