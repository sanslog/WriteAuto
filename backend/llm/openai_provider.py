import json

from openai import AsyncOpenAI

from backend import config
from backend.llm.provider import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str = "", base_url: str = "", model: str = "",
                 max_tokens: int = 0):
        import httpx
        self.client = AsyncOpenAI(
            api_key=api_key or config.LLM_API_KEY,
            base_url=base_url or config.LLM_BASE_URL,
            timeout=httpx.Timeout(
                timeout=120.0,       # total request timeout
                connect=15.0,        # connection timeout
                read=120.0,          # read timeout (main generation can be slow)
                write=30.0,          # write timeout
            ),
            max_retries=1,
        )
        self.model = model or config.LLM_MODEL
        self.max_tokens = max_tokens or config.LLM_MAX_TOKENS

    async def chat(self, messages: list[dict], temperature: float = 0.8,
                   max_tokens: int | None = None) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
        )
        return resp.choices[0].message.content or ""

    async def chat_json(self, messages: list[dict], temperature: float = 0.3,
                        max_tokens: int | None = None) -> dict:
        text = await self.chat(
            messages, temperature=temperature,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
        )
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]) if lines[1:] else text
            if text.endswith("```"):
                text = text[:-3]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}
