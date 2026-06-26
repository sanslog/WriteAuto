from backend.config import MAX_CONTEXT_CHARS, RECENT_CHAPTERS_COUNT


async def build_context(
    db, novel_id: str, chapter_ids: list[str] | None = None
) -> str:
    if chapter_ids:
        chapters = []
        for cid in chapter_ids:
            ch = await db.get_chapter(cid)
            if ch and ch["status"] == "approved":
                chapters.append(ch)
    else:
        approved = await db.get_chapters_by_status(novel_id, "approved")
        chapters = approved[-RECENT_CHAPTERS_COUNT:]

    if not chapters:
        return ""

    parts = []
    total_chars = 0
    for ch in chapters:
        content = ch.get("content", "")
        if len(content) > MAX_CONTEXT_CHARS:
            content = content[:MAX_CONTEXT_CHARS] + "\n...(内容过长已截断)"
        if total_chars + len(content) > MAX_CONTEXT_CHARS:
            remaining = MAX_CONTEXT_CHARS - total_chars
            if remaining > 200:
                content = content[:remaining] + "\n...(内容过长已截断)"
            else:
                break
        parts.append(f"## {ch.get('title', '')}\n{content}")
        total_chars += len(content)

    return "\n\n".join(parts)
