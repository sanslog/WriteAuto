"""Common abstractions for agent-callable backend tools."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Business domains used to route writing-agent tools."""

    NOVEL = "novel"
    OUTLINE = "outline"
    CHAPTER = "chapter"
    CHARACTER = "character"
    FORESHADOW = "foreshadow"
    SETTINGS = "settings"


class ToolInput(BaseModel):
    """Base input model that rejects unknown fields from the LLM."""

    model_config = ConfigDict(extra="forbid")


class ToolCallError(Exception):
    """Expected tool failure that can be returned as an observation."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _format_validation_error(exc: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(item) for item in error['loc'])}: {error['msg']}"
        for error in exc.errors(include_url=False)
    )


def _safe_arguments(name: str, arguments: dict[str, Any]) -> str:
    """Mask credentials while keeping the tool-call log reproducible."""

    safe_args: dict[str, Any] = dict(arguments)
    for key in list(safe_args):
        if "api_key" in key.lower() or key.lower() in {"token", "secret"}:
            safe_args[key] = "***"

    if name == "update_settings":
        fields = safe_args.get("fields", {})
        if isinstance(fields, dict):
            safe_args["fields"] = {
                key: ("***" if "api_key" in key.lower() else value)
                for key, value in fields.items()
            }

    try:
        return json.dumps(safe_args, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return repr(safe_args)


@dataclass(frozen=True)
class AgentTool:
    """A typed backend operation exposed to the ReAct loop."""

    name: str
    description: str
    category: ToolCategory
    input_model: type[ToolInput]
    handler: Callable[..., Awaitable[Any]]
    read_only: bool = False
    # Destructive/system-level operations stay callable in code, but are not
    # offered to the LLM by default.
    safe_for_agent: bool = True
    exclude_unset: bool = False

    def to_openai_tool(self) -> dict[str, Any]:
        """Return an OpenAI-compatible function-tool description."""

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_model.model_json_schema(),
            },
        }

    async def run(self, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Validate arguments, execute one DB-backed operation, and log it."""

        args = arguments or {}
        safe_args = _safe_arguments(self.name, args)
        logger.info(
            "Agent tool start: name=%s category=%s read_only=%s args=%s",
            self.name,
            self.category.value,
            self.read_only,
            safe_args,
        )

        try:
            parsed = self.input_model.model_validate(args)
            payload = parsed.model_dump(exclude_unset=self.exclude_unset)
            result = await self.handler(**payload)

            if isinstance(result, dict) and "success" in result:
                observation = result
            else:
                observation = {"success": True, "data": result}

            logger.info(
                "Agent tool success: name=%s result_keys=%s",
                self.name,
                sorted(observation.keys()) if isinstance(observation, dict) else [],
            )
            return observation
        except ToolCallError as exc:
            logger.warning(
                "Agent tool handled failure: name=%s error=%s", self.name, exc.message
            )
            return {"success": False, "error": exc.message, "error_type": "tool_error"}
        except ValidationError as exc:
            message = _format_validation_error(exc)
            logger.warning(
                "Agent tool invalid arguments: name=%s error=%s", self.name, message
            )
            return {
                "success": False,
                "error": message,
                "error_type": "invalid_arguments",
            }
        except Exception as exc:
            logger.exception("Agent tool unexpected failure: name=%s", self.name)
            return {
                "success": False,
                "error": f"Internal tool error: {exc}",
                "error_type": "internal_error",
            }

