from abc import ABC, abstractmethod


class LLMProvider(ABC):
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
