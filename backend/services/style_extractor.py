async def extract_characters_from_content(
    llm, content: str, existing_characters: list[dict]
) -> list[dict]:
    from backend.llm.prompts import build_character_extraction_prompt

    existing_text = "\n".join(
        f"- {c['name']}: {c.get('description', '')}" for c in existing_characters
    )
    system, user = build_character_extraction_prompt(content, existing_text)

    result = await llm.chat_json([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ], temperature=0.3)
    return result.get("characters", [])


async def extract_character_states(llm, content: str, characters: list[dict]) -> list[dict]:
    from backend.llm.prompts import build_character_state_prompt

    chars_text = "\n".join(
        f"- {c['name']}: {c.get('description', '')}" for c in characters
    )
    system, user = build_character_state_prompt(content, chars_text)

    result = await llm.chat_json([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ], temperature=0.3)
    return result.get("states", [])
