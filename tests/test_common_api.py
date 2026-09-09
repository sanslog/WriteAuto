from types import SimpleNamespace

import pytest

from backend.api.common import PingRequest, ping_OpenAI


@pytest.mark.asyncio
async def test_ping_openai_rejects_missing_fields(monkeypatch):
    create_spy = SimpleNamespace(calls=[])

    class StubClient:
        def __init__(self, *args, **kwargs):
            create_spy.calls.append((args, kwargs))

    monkeypatch.setattr("backend.api.common.AsyncOpenAI", StubClient)

    result = await ping_OpenAI(
        PingRequest(api_key="", baseurl="https://example.com", model_name="test-model")
    )

    assert result["success"] is False
    assert result["status_code"] == 400
    assert create_spy.calls == []


@pytest.mark.asyncio
async def test_ping_openai_returns_llm_response(monkeypatch):
    class StubCompletions:
        async def create(self, **kwargs):
            return SimpleNamespace(
                model_dump=lambda: {"model": kwargs["model"], "text": "Hi"}
            )

    class StubClient:
        def __init__(self, *args, **kwargs):
            self.chat = SimpleNamespace(completions=StubCompletions())

    monkeypatch.setattr("backend.api.common.AsyncOpenAI", StubClient)

    result = await ping_OpenAI(
        PingRequest(
            api_key="test-key",
            baseurl="https://example.com/",
            model_name="test-model",
        )
    )

    assert result["success"] is True
    assert result["status_code"] == 200
    assert result["data"]["text"] == "Hi"
