"""Abstract LLM provider interface with cancellation support."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):

    def set_gen_id(self, gen_id: str | None) -> None:
        """Bind this provider to a generation session.
        
        When set, all chat/chat_stream/chat_json calls should
        watch the cancellation signal and abort early to save tokens.
        The default implementation is a no-op; subclasses should
        override with actual cancellation logic.
        """
        self._gen_id = gen_id if hasattr(self, '_gen_id') else None

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
        """Streaming variant of chat().

        Default fallback yields the complete result in one chunk.
        Subclasses should override with true streaming (stream=True) for
        cancellation support.
        """
        text = await self.chat(messages, temperature, max_tokens or 0)
        yield text
