from backend.agent.state import State


async def character_fetch_node(state: State) -> dict:
    from backend.db.database import Database
    from backend.config import DB_PATH
    from backend.services.legality import check_legality

    novel_id = state["novel_id"]
    detailed_outline = state.get("detailed_outline", "")

    db = Database(DB_PATH)
    await db.init()
    try:
        # 这个功能没有必要，多余且浪费token
        # ── 1. 合法性检查 ──
        # approved = await db.get_chapters_by_status(novel_id, "approved")
        # if approved:
        #     recent = approved[-RECENT_CHAPTERS_COUNT:]
        #     content_parts = []
        #     for ch in recent:
        #         text = ch.get("content", "")
        #         if len(text) > RECENT_CHAPTER_CHAR_LIMIT:
        #             text = text[:RECENT_CHAPTER_CHAR_LIMIT]
        #         content_parts.append(text)
        #     combined = "\n\n".join(content_parts)

        #     llm = create_llm_provider()
        #     unlawful, reason = await check_legality(llm, combined)
        #     if unlawful:
        #         return {
        #             "unlawful": True,
        #             "unlaw_reason": reason,
        #         }

        # ── 2. 从细纲(outline)中匹配角色 ──
        # 细纲为空 → 不提供角色信息
        if not detailed_outline.strip():
            return {
                "main_character_design": "",
                "unlawful": False,
                "unlaw_reason": "",
            }

        characters = await db.get_characters(novel_id)

        # 精准匹配：角色名出现在细纲文本中
        matched = [c for c in characters if c.get("name") and c["name"] in detailed_outline]

        # 无匹配 → 说明是新角色尚未入库，交由用户管理
        if not matched:
            return {
                "main_character_design": "",
                "unlawful": False,
                "unlaw_reason": "",
            }

        char_design = "\n".join(
            f"- {c['name']}（{c.get('role', '')}）: {c.get('description', '')}"
            for c in matched
        )

        return {
            "main_character_design": char_design,
            "unlawful": False,
            "unlaw_reason": "",
        }
    finally:
        await db.close()

