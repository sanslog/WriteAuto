async def check_legality(llm, content: str) -> tuple[bool, str]:
    from backend.llm.prompts import build_legality_check_prompt

    system, user = build_legality_check_prompt(content)
    result = await llm.chat_json([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ], temperature=0.0)
    unlawful = result.get("unlawful", False)
    reason = result.get("reason", "")
    return unlawful, reason
