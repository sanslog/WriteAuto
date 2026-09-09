import asyncio

import httpx
import pytest

from backend.agent import cancellation
from backend.api import one_sentence
from backend.api.one_sentence import OneSentenceSession, _register, _unregister
from backend.llm.provider import LLMProvider
from backend.react_agent import graph as react_graph
from backend.server import create_app


class CancelledProvider(LLMProvider):
    def __init__(self):
        self._gen_id = ""
        self.generation_id = ""
        self.cancelled_at_llm = False

    def set_gen_id(self, gen_id):
        self._gen_id = gen_id
        self.generation_id = gen_id

    async def chat(self, messages, temperature=0.8, max_tokens=8192):
        raise AssertionError("ReAct graph should use chat_with_tools")

    async def chat_json(self, messages, temperature=0.3, max_tokens=4096):
        raise AssertionError("ReAct graph should use chat_with_tools")

    async def chat_with_tools(self, messages, tools=None, temperature=0.3, max_tokens=4096):
        cancel_event = cancellation.get_async_event(self._gen_id)
        assert cancel_event is not None
        await cancel_event.wait()
        self.cancelled_at_llm = True
        raise asyncio.CancelledError("LLM request cancelled")


class ValidationProvider(LLMProvider):
    def __init__(self):
        self.calls = 0

    async def chat(self, messages, temperature=0.8, max_tokens=8192):
        raise AssertionError("Empty request should not call the LLM")

    async def chat_json(self, messages, temperature=0.3, max_tokens=4096):
        raise AssertionError("Empty request should not call the LLM")

    async def chat_with_tools(self, messages, tools=None, temperature=0.3, max_tokens=4096):
        self.calls += 1
        raise AssertionError("Empty request should not call the LLM")


@pytest.mark.asyncio
async def test_run_react_agent_reports_progress_without_llm_call():
    events = []

    async def callback(node_name, output):
        events.append((node_name, output))

    provider = ValidationProvider()
    result = await react_graph.run_react_agent(
        "  ",
        session_id="progress-empty",
        provider=provider,
        progress_callback=callback,
    )

    assert result["status"] == "failed"
    assert provider.calls == 0
    assert [name for name, _output in events] == ["validate_input", "finalize"]


@pytest.mark.asyncio
async def test_react_agent_aborts_llm_call_on_cancellation():
    generation_id = "react-cancel-direct"
    cancellation.register(generation_id)
    provider = CancelledProvider()
    events = []

    async def callback(node_name, output):
        events.append(node_name)

    run_task = asyncio.create_task(
        react_graph.run_react_agent(
            "一个年轻修士听到了残稿说话",
            session_id=generation_id,
            generation_id=generation_id,
            provider=provider,
            progress_callback=callback,
        )
    )

    for _ in range(100):
        if provider.generation_id:
            break
        await asyncio.sleep(0.01)

    await asyncio.sleep(0)
    cancellation.cancel(generation_id)
    result = await run_task
    cancellation.unregister(generation_id)

    assert provider.cancelled_at_llm is True
    assert result["cancelled"] is True
    assert result["status"] == "cancelled"
    assert "agent" in events
    assert "finalize" in events


@pytest.mark.asyncio
async def test_cancel_endpoint_sets_registry_event(temp_db):
    session = OneSentenceSession(
        generation_id="react-cancel-api",
        user_request="test",
    )
    _register(session)
    transport = httpx.ASGITransport(app=create_app())
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/one-sentence/react-cancel-api/cancel")

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert cancellation.is_cancelled("react-cancel-api") is True
    finally:
        _unregister(session)
