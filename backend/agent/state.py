from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class State(TypedDict):
    # ── Writing config ──
    base_prompt: str
    style_of_writing: str
    world_outlook: str

    # ── Outline & cursor ──
    outline: str
    detailed_outline: str
    cursor_position: int
    plot_nodes_count: int
    next_node_title: str

    # ── Characters & foreshadows ──
    main_character_design: str
    foreshadow: str

    # ── Context ──
    context: str
    chapter_ids: list[str]
    foreshadow_ids: list[str]

    # ── Generation results ──
    generated_text: str
    chapter_titles: list[str]
    character_states_json: str

    # ── Loop control ──
    enter_loop: bool
    should_end: bool
    modification_count: int
    user_input_text: str

    # ── Legality ──
    unlawful: bool
    unlaw_reason: str

    # ── Messages ──
    messages: Annotated[list, add_messages]

    # ── Metadata ──
    novel_id: str
    generation_id: str

    # ── Internal (not exposed to frontend) ──
    _saved_chapters: list[dict]
    _cancelled: bool
