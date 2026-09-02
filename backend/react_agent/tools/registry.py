"""Central registry and category-based routing for writing-agent tools."""

from __future__ import annotations

import json
import logging

from backend.react_agent.tools.base import AgentTool, ToolCategory, ToolInput
from backend.react_agent.tools.chapter import (
    ChapterIdInput,
    CreateChapterInput,
    ListChaptersInput,
    UpdateChapterInput,
    create_chapter,
    delete_chapter,
    get_chapter,
    list_chapters,
    update_chapter,
)
from backend.react_agent.tools.character import (
    CharacterIdInput,
    CreateCharacterInput,
    ListCharactersInput,
    UpdateCharacterInput,
    create_character,
    delete_character,
    list_characters,
    update_character,
)
from backend.react_agent.tools.foreshadow import (
    CreateForeshadowInput,
    ForeshadowIdInput,
    ListForeshadowsInput,
    UpdateForeshadowInput,
    create_foreshadow,
    delete_foreshadow,
    list_foreshadows,
    update_foreshadow,
)
from backend.react_agent.tools.novel import (
    CreateNovelInput,
    ListNovelsInput,
    NovelIdInput as NovelIdOnlyInput,
    UpdateNovelInput,
    create_novel,
    delete_novel,
    get_novel,
    list_novels,
    update_novel,
)
from backend.react_agent.tools.outline import (
    CreatePlotNodeInput,
    DeletePlotNodeInput,
    MoveCursorInput,
    NovelIdInput as OutlineNovelIdInput,
    UpdatePlotNodeInput,
    create_plot_node,
    delete_plot_node,
    list_plot_nodes,
    move_plot_cursor,
    update_plot_node,
)
from backend.react_agent.tools.settings import (
    GetSettingsInput,
    UpdateSettingsInput,
    get_settings,
    update_settings,
)

logger = logging.getLogger(__name__)


def _tool(
    name: str,
    description: str,
    category: ToolCategory,
    input_model: type[ToolInput],
    handler,
    *,
    read_only: bool = False,
    safe_for_agent: bool = True,
) -> AgentTool:
    return AgentTool(
        name=name,
        description=description,
        category=category,
        input_model=input_model,
        handler=handler,
        read_only=read_only,
        safe_for_agent=safe_for_agent,
    )


ALL_TOOLS: tuple[AgentTool, ...] = (
    # Novel project and global premise.
    _tool(
        "list_novels",
        "读取小说项目列表，用于选择要续写或查询的 novel_id。",
        ToolCategory.NOVEL,
        ListNovelsInput,
        list_novels,
        read_only=True,
    ),
    _tool(
        "get_novel",
        "读取小说标题、剧情梗概、文风、世界观和当前写作位置。",
        ToolCategory.NOVEL,
        NovelIdOnlyInput,
        get_novel,
        read_only=True,
    ),
    _tool(
        "create_novel",
        "根据用户的一句话题材、主角或剧情梗概创建新小说项目。",
        ToolCategory.NOVEL,
        CreateNovelInput,
        create_novel,
    ),
    _tool(
        "update_novel",
        "修改小说标题、剧情梗概、文风或世界观设定。",
        ToolCategory.NOVEL,
        UpdateNovelInput,
        update_novel,
    ),
    _tool(
        "delete_novel",
        "删除小说项目及其关联数据。",
        ToolCategory.NOVEL,
        NovelIdOnlyInput,
        delete_novel,
        safe_for_agent=False,
    ),
    # Plot outline and writing cursor.
    _tool(
        "list_plot_nodes",
        "读取完整剧情大纲节点和排列顺序。",
        ToolCategory.OUTLINE,
        OutlineNovelIdInput,
        list_plot_nodes,
        read_only=True,
    ),
    _tool(
        "create_plot_node",
        "新增剧情大纲节点，用于规划后续章节情节。",
        ToolCategory.OUTLINE,
        CreatePlotNodeInput,
        create_plot_node,
    ),
    _tool(
        "update_plot_node",
        "修订剧情节点标题、摘要、详细大纲或状态。",
        ToolCategory.OUTLINE,
        UpdatePlotNodeInput,
        update_plot_node,
    ),
    _tool(
        "move_plot_cursor",
        "设置当前要写作的剧情节点位置。",
        ToolCategory.OUTLINE,
        MoveCursorInput,
        move_plot_cursor,
    ),
    _tool(
        "delete_plot_node",
        "删除剧情大纲节点并自动修正写作位置。",
        ToolCategory.OUTLINE,
        DeletePlotNodeInput,
        delete_plot_node,
        safe_for_agent=False,
    ),
    # Generated novel text.
    _tool(
        "list_chapters",
        "读取小说章节列表及其状态、标题和排序。",
        ToolCategory.CHAPTER,
        ListChaptersInput,
        list_chapters,
        read_only=True,
    ),
    _tool(
        "get_chapter",
        "读取章节正文，用于续写前回顾已有内容。",
        ToolCategory.CHAPTER,
        ChapterIdInput,
        get_chapter,
        read_only=True,
    ),
    _tool(
        "create_chapter",
        "保存新生成的章节正文。",
        ToolCategory.CHAPTER,
        CreateChapterInput,
        create_chapter,
    ),
    _tool(
        "update_chapter",
        "修改已有章节标题、正文或状态。",
        ToolCategory.CHAPTER,
        UpdateChapterInput,
        update_chapter,
    ),
    _tool(
        "delete_chapter",
        "删除章节正文记录。",
        ToolCategory.CHAPTER,
        ChapterIdInput,
        delete_chapter,
        safe_for_agent=False,
    ),
    # Character continuity.
    _tool(
        "list_characters",
        "读取小说的角色档案。",
        ToolCategory.CHARACTER,
        ListCharactersInput,
        list_characters,
        read_only=True,
    ),
    _tool(
        "create_character",
        "新增角色档案，记录性格、背景和叙事定位。",
        ToolCategory.CHARACTER,
        CreateCharacterInput,
        create_character,
    ),
    _tool(
        "update_character",
        "更新角色名称、设定或叙事定位。",
        ToolCategory.CHARACTER,
        CharacterIdInput,
        update_character,
    ),
    _tool(
        "delete_character",
        "删除角色档案。",
        ToolCategory.CHARACTER,
        CharacterIdInput,
        delete_character,
        safe_for_agent=False,
    ),
    # Long-range plot setup and payoff.
    _tool(
        "list_foreshadows",
        "读取小说的伏笔清单和回收状态。",
        ToolCategory.FORESHADOW,
        ListForeshadowsInput,
        list_foreshadows,
        read_only=True,
    ),
    _tool(
        "create_foreshadow",
        "登记新伏笔，供后续章节保持剧情连续性。",
        ToolCategory.FORESHADOW,
        CreateForeshadowInput,
        create_foreshadow,
    ),
    _tool(
        "update_foreshadow",
        "更新伏笔内容、关联章节或回收状态。",
        ToolCategory.FORESHADOW,
        UpdateForeshadowInput,
        update_foreshadow,
    ),
    _tool(
        "delete_foreshadow",
        "删除伏笔记录。",
        ToolCategory.FORESHADOW,
        ForeshadowIdInput,
        delete_foreshadow,
        safe_for_agent=False,
    ),
    # Runtime model/writing configuration.
    _tool(
        "get_settings",
        "读取全局写作和模型配置。",
        ToolCategory.SETTINGS,
        GetSettingsInput,
        get_settings,
        read_only=True,
    ),
    _tool(
        "update_settings",
        "更新全局写作和模型配置。",
        ToolCategory.SETTINGS,
        UpdateSettingsInput,
        update_settings,
        safe_for_agent=False,
    ),
)

TOOL_BY_NAME: dict[str, AgentTool] = {tool.name: tool for tool in ALL_TOOLS}


def get_all_tools() -> tuple[AgentTool, ...]:
    return ALL_TOOLS


def get_agent_tools() -> tuple[AgentTool, ...]:
    """Return the safe tool subset for an autonomous LLM loop."""

    return tuple(tool for tool in ALL_TOOLS if tool.safe_for_agent)


def get_tools_by_category(category: ToolCategory) -> tuple[AgentTool, ...]:
    """Route tools by writing-workflow domain."""

    return tuple(tool for tool in ALL_TOOLS if tool.category == category)


def find_tool(name: str) -> AgentTool | None:
    return TOOL_BY_NAME.get(name)


def build_openai_tools() -> list[dict]:
    """Build the safe tool manifest for an OpenAI-compatible LLM call."""

    return [tool.to_openai_tool() for tool in get_agent_tools()]


def _parse_tool_call(call: dict, index: int) -> tuple[str, str, dict]:
    function = call.get("function", {})
    if not isinstance(function, dict):
        function = {}

    tool_name = str(call.get("name") or function.get("name") or "")
    tool_call_id = str(call.get("id") or f"call_{index}")
    raw_arguments = call.get("arguments", function.get("arguments", {}))

    if raw_arguments is None or raw_arguments == "":
        arguments = {}
    elif isinstance(raw_arguments, str):
        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Arguments for {tool_name} are not valid JSON: {exc}") from exc
    elif isinstance(raw_arguments, dict):
        arguments = raw_arguments
    else:
        raise ValueError(f"Arguments for {tool_name} must be a JSON object")

    if not isinstance(arguments, dict):
        raise ValueError(f"Arguments for {tool_name} must be a JSON object")
    if not tool_name:
        raise ValueError("Tool call is missing function.name")

    return tool_name, tool_call_id, arguments


async def execute_tool_calls(tool_calls: list[dict]) -> list[dict]:
    """Parse, route, and sequentially execute LLM tool calls.

    MVP intentionally executes sequentially; each observation preserves the
    caller's tool_call_id so it can be fed back into an OpenAI-style message
    list by the ReAct loop.
    """

    observations: list[dict] = []
    for index, call in enumerate(tool_calls):
        try:
            tool_name, tool_call_id, arguments = _parse_tool_call(call, index)
        except (TypeError, ValueError) as exc:
            logger.warning("Invalid agent tool call at index %d: %s", index, exc)
            observations.append(
                {
                    "tool_call_id": call.get("id", f"call_{index}"),
                    "tool_name": "",
                    "result": {
                        "success": False,
                        "error": str(exc),
                        "error_type": "invalid_tool_call",
                    },
                }
            )
            continue

        tool = find_tool(tool_name)
        if tool is None:
            logger.warning("Unknown agent tool requested: %s", tool_name)
            observations.append(
                {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "result": {
                        "success": False,
                        "error": f"Unknown tool: {tool_name}",
                        "error_type": "unknown_tool",
                    },
                }
            )
            continue

        result = await tool.run(arguments)
        logger.info(
            "Agent tool routed: tool_call_id=%s name=%s category=%s success=%s",
            tool_call_id,
            tool_name,
            tool.category.value,
            result.get("success", False),
        )
        observations.append(
            {
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "result": result,
            }
        )

    return observations
