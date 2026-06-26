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
