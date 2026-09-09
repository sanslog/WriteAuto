"""Sliding-window helpers for OpenAI-compatible chat messages."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _message_size(message: dict[str, Any]) -> int:
    content = message.get("content", "")
    size = len(content) if isinstance(content, str) else len(
        json.dumps(content, ensure_ascii=False, default=str)
    )
    tool_calls = message.get("tool_calls")
    if tool_calls:
        size += len(json.dumps(tool_calls, ensure_ascii=False, default=str))
    return size


def _message_groups(messages: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Group an assistant tool-call request with every tool response."""

    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] | None = None
    for message in messages:
        role = str(message.get("role", ""))
        is_tool_response = (
            role == "tool"
            and current is not None
            and bool(current[0].get("tool_calls"))
        )
        if is_tool_response and current is not None:
            current.append(message)
            continue

        current = [message]
        groups.append(current)
    return groups


def apply_chat_message_window(
    messages: list[dict[str, Any]] | None,
    *,
    max_messages: int = 32,
    max_chars: int = 0,
) -> list[dict[str, Any]]:
    """Return the provider-visible sliding window without splitting tool turns.

    The first user request is anchored because it carries the original writing
    task. The latest complete turn is always retained even when a single tool
    response is larger than the configured budget.
    """

    source = list(messages or [])
    if not source:
        return []

    system_messages: list[dict[str, Any]] = []
    conversation: list[dict[str, Any]] = []
    for message in source:
        if str(message.get("role", "")) == "system" and not conversation:
            system_messages.append(message)
        else:
            conversation.append(message)

    groups = _message_groups(conversation)
    if not groups:
        return system_messages

    message_limit = max(3, int(max_messages))
    char_limit = max(0, int(max_chars))
    system_size = sum(_message_size(message) for message in system_messages)
    anchor_index = 0 if groups[0][0].get("role") == "user" else None

    selected_indexes: list[int] = []
    selected_count = 0
    selected_size = 0
    for group_index in reversed(range(len(groups))):
        group = groups[group_index]
        group_count = len(group)
        group_size = sum(_message_size(message) for message in group)
        is_anchor = group_index == anchor_index

        if selected_indexes:
            reserved_count = 0 if is_anchor else (1 if anchor_index is not None else 0)
            reserved_size = (
                0
                if is_anchor
                else sum(
                    _message_size(message)
                    for message in groups[anchor_index]
                )
                if anchor_index is not None
                else 0
            )
            if (
                selected_count + group_count + len(system_messages) + reserved_count
                > message_limit
            ) or (
                char_limit
                and selected_size + group_size + system_size + reserved_size > char_limit
            ):
                break

        selected_indexes.insert(0, group_index)
        selected_count += group_count
        selected_size += group_size
        if is_anchor:
            break

    if anchor_index is not None and anchor_index not in selected_indexes:
        selected_indexes.insert(0, anchor_index)

    window = system_messages + [
        message for index in selected_indexes for message in groups[index]
    ]
    dropped = len(source) - len(window)
    if dropped > 0:
        logger.debug(
            "Trimmed ReAct chat context: input=%d output=%d dropped=%d",
            len(source),
            len(window),
            dropped,
        )
    return window
