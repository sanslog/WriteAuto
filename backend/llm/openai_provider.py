import asyncio
import json
from typing import Any

from openai import AsyncOpenAI

from backend import config
from backend.llm.provider import LLMProvider
from backend.agent import cancellation


class OpenAIProvider(LLMProvider):

    async def _wait_for_cancel(self, event: asyncio.Event) -> None:
        await event.wait()

    def __init__(self, api_key: str = "", base_url: str = "", model: str = "",
                 max_tokens: int = 0):
        import httpx
        self.client = AsyncOpenAI(
            api_key=api_key or config.LLM_API_KEY,
            base_url=base_url or config.LLM_BASE_URL,
            timeout=httpx.Timeout(
                timeout=120.0, connect=15.0, read=120.0, write=30.0,
            ),
            max_retries=1,
        )
        self.model = model or config.LLM_MODEL
        self.max_tokens = max_tokens or config.LLM_MAX_TOKENS
        self._gen_id: str | None = None

    def set_gen_id(self, gen_id: str | None) -> None:
        self._gen_id = gen_id

    def _get_cancel_event(self) -> asyncio.Event | None:
        if not self._gen_id:
            return None
        return cancellation.get_async_event(self._gen_id)

    async def _abort_if_cancelled(self) -> None:
        cancel_event = self._get_cancel_event()
        if cancel_event and cancel_event.is_set():
            raise asyncio.CancelledError(f"Generation {self._gen_id} was cancelled")

    async def _race_with_cancel(self, api_task) -> Any:
        """Run an API task, racing it against cancellation if a cancel event exists."""
        cancel_event = self._get_cancel_event()
        if not cancel_event:
            return await api_task

        cancel_watch = asyncio.create_task(self._wait_for_cancel(cancel_event))
        done, pending = await asyncio.wait(
            [api_task, cancel_watch],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        if cancel_watch in done:
            api_task.cancel()
            try:
                await api_task
            except (asyncio.CancelledError, Exception):
                pass
            raise asyncio.CancelledError(f"Generation {self._gen_id} was cancelled")
        return api_task.result()

    async def chat(self, messages: list[dict], temperature: float = 0.8,
                   max_tokens: int | None = None) -> str:
        await self._abort_if_cancelled()

        api_task = asyncio.create_task(
            self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
            )
        )
        resp = await self._race_with_cancel(api_task)
        return resp.choices[0].message.content or ""

    async def chat_stream(self, messages: list[dict], temperature: float = 0.8,
                          max_tokens: int | None = None):
        await self._abort_if_cancelled()
        cancel_event = self._get_cancel_event()

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
            stream=True,
        )
        try:
            async for chunk in stream:
                if cancel_event and cancel_event.is_set():
                    break
                delta = chunk.choices[0].delta if chunk.choices else None
                content = delta.content if delta else ""
                if content:
                    yield content
        finally:
            try:
                await stream.response.aclose()
            except Exception:
                pass

    async def chat_json(self, messages: list[dict], temperature: float = 0.3,
                        max_tokens: int | None = None) -> dict:
        await self._abort_if_cancelled()
        text = await self.chat(
            messages, temperature=temperature,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
        )
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]) if len(lines) > 1 else text
            text = text[:-3] if text.endswith("```") else text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Use OpenAI native function calling.

        Returns:
            {"type": "text", "content": "..."} — LLM chose to respond with text
            {"type": "tool_calls", "calls": [...]} — LLM wants to call tools
        """
        await self._abort_if_cancelled()

        kwargs = dict(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        api_task = asyncio.create_task(
            self.client.chat.completions.create(**kwargs)
        )
        resp = await self._race_with_cancel(api_task)
        msg = resp.choices[0].message

        # Native tool_calls from the API
        if msg.tool_calls:
            calls = []
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {"_raw": tc.function.arguments}
                calls.append({
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": args,
                    },
                })
            return {"type": "tool_calls", "calls": calls}

        # Content response (tool not needed, or no tools passed)
        return {"type": "text", "content": msg.content or ""}
