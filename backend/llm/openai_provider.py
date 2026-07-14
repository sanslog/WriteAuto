import asyncio
import json

from openai import AsyncOpenAI

from backend import config
from backend.llm.provider import LLMProvider
from backend.agent import cancellation


class OpenAIProvider(LLMProvider):

    async def _wait_for_cancel(self, event: asyncio.Event) -> None:
        """Wait asynchronously until the cancel event is set."""
        await event.wait()

    def __init__(self, api_key: str = "", base_url: str = "", model: str = "",
                 max_tokens: int = 0):
        import httpx
        self.client = AsyncOpenAI(
            api_key=api_key or config.LLM_API_KEY,
            base_url=base_url or config.LLM_BASE_URL,
            timeout=httpx.Timeout(
                timeout=120.0,
                connect=15.0,
                read=120.0,
                write=30.0,
            ),
            max_retries=1,
        )
        self.model = model or config.LLM_MODEL
        self.max_tokens = max_tokens or config.LLM_MAX_TOKENS
        self._gen_id: str | None = None

    def set_gen_id(self, gen_id: str | None) -> None:
        """Bind this provider instance to a generation session for cancellation support."""
        self._gen_id = gen_id

    def _get_cancel_event(self) -> asyncio.Event | None:
        if not self._gen_id:
            return None
        return cancellation.get_async_event(self._gen_id)

    async def _abort_if_cancelled(self) -> None:
        """Raise an exception if the generation has been cancelled.
        
        This is used inside chat() / chat_json() to abort before making
        an API call (best-effort token saving).
        """
        cancel_event = self._get_cancel_event()
        if cancel_event and cancel_event.is_set():
            raise asyncio.CancelledError(f"Generation {self._gen_id} was cancelled")

    async def chat(self, messages: list[dict], temperature: float = 0.8,
                   max_tokens: int | None = None) -> str:
        cancel_event = self._get_cancel_event()
        if cancel_event and cancel_event.is_set():
            raise asyncio.CancelledError(f"Generation {self._gen_id} was cancelled")

        # Create the API call as a task so we can race it with cancellation
        api_task = asyncio.create_task(
            self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
            )
        )

        if cancel_event:
            # Race: API call vs cancellation watch
            cancel_watch = asyncio.create_task(self._wait_for_cancel(cancel_event))
            done, pending = await asyncio.wait(
                [api_task, cancel_watch],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            if cancel_watch in done:
                # Cancellation won the race
                api_task.cancel()
                try:
                    await api_task
                except (asyncio.CancelledError, Exception):
                    pass
                raise asyncio.CancelledError(f"Generation {self._gen_id} was cancelled")
            # API call won
            resp = api_task.result()
        else:
            resp = await api_task

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
        if text.startswith("`"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]) if lines[1:] else text
            if text.endswith("`"):
                text = text[:-3]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}
