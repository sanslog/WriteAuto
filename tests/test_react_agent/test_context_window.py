from backend.react_agent.nodes.context_window import apply_chat_message_window


def _tool_group(index: int) -> list[dict]:
    call_id = f"call-{index}"
    return [
        {"role": "user", "content": f"continue-{index}"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": "list_novels", "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "tool_call_id": call_id, "content": f"result-{index}"},
    ]


def test_context_window_keeps_anchor_and_latest_tool_group():
    messages = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "original writing request"},
    ]
    for index in range(1, 6):
        messages.extend(_tool_group(index))

    window = apply_chat_message_window(messages, max_messages=8, max_chars=0)

    assert [message["role"] for message in window] == [
        "system",
        "user",
        "user",
        "assistant",
        "tool",
        "user",
        "assistant",
        "tool",
    ]
    assert window[1]["content"] == "original writing request"
    assert window[-1]["tool_call_id"] == "call-5"
    assert window[-2]["tool_calls"][0]["id"] == "call-5"


def test_context_window_applies_character_budget_without_dropping_latest_group():
    messages = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "original writing request"},
    ]
    for index in range(1, 7):
        group = _tool_group(index)
        group[0]["content"] = f"continue-{index}: " + "x" * (index * 100)
        messages.extend(group)

    window = apply_chat_message_window(messages, max_messages=32, max_chars=350)
    latest_call_id = "call-6"

    assert window[0]["role"] == "system"
    assert window[1]["content"] == "original writing request"
    assert window[-1]["tool_call_id"] == latest_call_id
    assert any(
        message.get("tool_calls", [{}])[0].get("id") == latest_call_id
        for message in window
    )
    assert len(window) < len(messages)
