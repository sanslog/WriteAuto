import aiosqlite

from backend.config import DB_PATH


async def get_db() -> "Database":
    db = Database(DB_PATH)
    await db.init()
    return db


class Database:
    def __init__(self, path: str):
        self.path = str(path)

    async def init(self):
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        await self.conn.close()

    async def _create_tables(self):
        await self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS novels (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '',
            base_prompt TEXT NOT NULL DEFAULT '',
            style_of_writing TEXT NOT NULL DEFAULT '',
            world_outlook TEXT NOT NULL DEFAULT '',
            cursor_position INTEGER NOT NULL DEFAULT 0,
            is_done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS plot_nodes (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
            sort_order INTEGER NOT NULL DEFAULT 0,
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            detailed_outline TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'planned',
            chapter_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS chapters (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
            title TEXT NOT NULL DEFAULT '',
            content TEXT NOT NULL DEFAULT '',
            file_path TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'draft',
            sort_order INTEGER NOT NULL DEFAULT 0,
            word_count INTEGER NOT NULL DEFAULT 0,
            generation_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
            name TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS character_states (
            id TEXT PRIMARY KEY,
            character_id TEXT NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
            chapter_id TEXT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
            state_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS foreshadows (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
            title TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'unused',
            chapter_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS generation_logs (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
            generation_id TEXT NOT NULL DEFAULT '',
            prompt TEXT NOT NULL DEFAULT '',
            result TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            tokens_used INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );
        """)
        await self.conn.commit()

    # ── novels ──

    async def get_all_novels(self):
        cursor = await self.conn.execute(
            "SELECT * FROM novels ORDER BY updated_at DESC")
        return [dict(row) for row in await cursor.fetchall()]

    async def get_novel(self, novel_id: str):
        cursor = await self.conn.execute(
            "SELECT * FROM novels WHERE id = ?", (novel_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def create_novel(self, data: dict):
        import uuid
        novel_id = data.get("id", str(uuid.uuid4()))
        await self.conn.execute(
            """INSERT INTO novels (id, title, base_prompt, style_of_writing, world_outlook)
               VALUES (?, ?, ?, ?, ?)""",
            (novel_id, data.get("title", ""), data.get("base_prompt", ""),
             data.get("style_of_writing", ""), data.get("world_outlook", "")))
        await self.conn.commit()
        return await self.get_novel(novel_id)

    async def update_novel(self, novel_id: str, data: dict):
        fields = []
        values = []
        for k in ("title", "base_prompt", "style_of_writing", "world_outlook",
                  "cursor_position", "is_done"):
            if k in data:
                fields.append(f"{k} = ?")
                values.append(data[k])
        if not fields:
            return await self.get_novel(novel_id)
        fields.append("updated_at = datetime('now')")
        values.append(novel_id)
        await self.conn.execute(
            f"UPDATE novels SET {', '.join(fields)} WHERE id = ?", values)
        await self.conn.commit()
        return await self.get_novel(novel_id)

    async def delete_novel(self, novel_id: str):
        await self.conn.execute("DELETE FROM novels WHERE id = ?", (novel_id,))
        await self.conn.commit()

    # ── plot_nodes ──

    async def get_plot_nodes(self, novel_id: str):
        cursor = await self.conn.execute(
            "SELECT * FROM plot_nodes WHERE novel_id = ? ORDER BY sort_order",
            (novel_id,))
        return [dict(row) for row in await cursor.fetchall()]

    async def create_plot_node(self, data: dict):
        import uuid
        node_id = data.get("id", str(uuid.uuid4()))
        await self.conn.execute(
            """INSERT INTO plot_nodes (id, novel_id, sort_order, title, summary, detailed_outline, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (node_id, data["novel_id"], data.get("sort_order", 0),
             data.get("title", ""), data.get("summary", ""),
             data.get("detailed_outline", ""), data.get("status", "planned")))
        await self.conn.commit()
        return await self._get_plot_node(node_id)

    async def update_plot_node(self, node_id: str, data: dict):
        fields = []
        values = []
        for k in ("title", "summary", "detailed_outline", "status", "sort_order",
                  "chapter_id"):
            if k in data:
                fields.append(f"{k} = ?")
                values.append(data[k])
        if not fields:
            return await self._get_plot_node(node_id)
        fields.append("updated_at = datetime('now')")
        values.append(node_id)
        await self.conn.execute(
            f"UPDATE plot_nodes SET {', '.join(fields)} WHERE id = ?", values)
        await self.conn.commit()
        return await self._get_plot_node(node_id)

    async def delete_plot_node(self, node_id: str):
        await self.conn.execute("DELETE FROM plot_nodes WHERE id = ?", (node_id,))
        await self.conn.commit()

    async def _get_plot_node(self, node_id: str):
        cursor = await self.conn.execute(
            "SELECT * FROM plot_nodes WHERE id = ?", (node_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    # ── chapters ──

    async def get_chapters(self, novel_id: str):
        cursor = await self.conn.execute(
            "SELECT * FROM chapters WHERE novel_id = ? ORDER BY sort_order",
            (novel_id,))
        return [dict(row) for row in await cursor.fetchall()]

    async def get_chapter(self, chapter_id: str):
        cursor = await self.conn.execute(
            "SELECT * FROM chapters WHERE id = ?", (chapter_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_chapters_by_status(self, novel_id: str, status: str):
        cursor = await self.conn.execute(
            "SELECT * FROM chapters WHERE novel_id = ? AND status = ? ORDER BY sort_order",
            (novel_id, status))
        return [dict(row) for row in await cursor.fetchall()]

    async def create_chapter(self, data: dict):
        import uuid
        ch_id = data.get("id", str(uuid.uuid4()))
        await self.conn.execute(
            """INSERT INTO chapters (id, novel_id, title, content, file_path, status, sort_order, word_count, generation_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ch_id, data["novel_id"], data.get("title", ""),
             data.get("content", ""), data.get("file_path", ""),
             data.get("status", "draft"), data.get("sort_order", 0),
             data.get("word_count", 0), data.get("generation_id", "")))
        await self.conn.commit()
        return await self.get_chapter(ch_id)

    async def update_chapter(self, chapter_id: str, data: dict):
        fields = []
        values = []
        for k in ("title", "content", "file_path", "status", "sort_order",
                  "word_count", "generation_id"):
            if k in data:
                fields.append(f"{k} = ?")
                values.append(data[k])
        if not fields:
            return await self.get_chapter(chapter_id)
        fields.append("updated_at = datetime('now')")
        values.append(chapter_id)
        await self.conn.execute(
            f"UPDATE chapters SET {', '.join(fields)} WHERE id = ?", values)
        await self.conn.commit()
        return await self.get_chapter(chapter_id)

    async def delete_chapter(self, chapter_id: str):
        await self.conn.execute("DELETE FROM chapters WHERE id = ?", (chapter_id,))
        await self.conn.commit()

    # ── characters ──

    async def get_characters(self, novel_id: str):
        cursor = await self.conn.execute(
            "SELECT * FROM characters WHERE novel_id = ?", (novel_id,))
        return [dict(row) for row in await cursor.fetchall()]

    async def create_character(self, data: dict):
        import uuid
        char_id = data.get("id", str(uuid.uuid4()))
        await self.conn.execute(
            """INSERT INTO characters (id, novel_id, name, description, role)
               VALUES (?, ?, ?, ?, ?)""",
            (char_id, data["novel_id"], data.get("name", ""),
             data.get("description", ""), data.get("role", "")))
        await self.conn.commit()
        return await self._get_character(char_id)

    async def update_character(self, char_id: str, data: dict):
        fields = []
        values = []
        for k in ("name", "description", "role"):
            if k in data:
                fields.append(f"{k} = ?")
                values.append(data[k])
        if not fields:
            return await self._get_character(char_id)
        fields.append("updated_at = datetime('now')")
        values.append(char_id)
        await self.conn.execute(
            f"UPDATE characters SET {', '.join(fields)} WHERE id = ?", values)
        await self.conn.commit()
        return await self._get_character(char_id)

    async def delete_character(self, char_id: str):
        await self.conn.execute("DELETE FROM characters WHERE id = ?", (char_id,))
        await self.conn.commit()

    async def _get_character(self, char_id: str):
        cursor = await self.conn.execute(
            "SELECT * FROM characters WHERE id = ?", (char_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    # ── character_states ──

    async def get_character_states(self, character_id: str):
        cursor = await self.conn.execute(
            "SELECT * FROM character_states WHERE character_id = ? ORDER BY created_at",
            (character_id,))
        return [dict(row) for row in await cursor.fetchall()]

    async def create_character_state(self, data: dict):
        import uuid
        cs_id = data.get("id", str(uuid.uuid4()))
        await self.conn.execute(
            """INSERT INTO character_states (id, character_id, chapter_id, state_json)
               VALUES (?, ?, ?, ?)""",
            (cs_id, data["character_id"], data["chapter_id"],
             data.get("state_json", "{}")))
        await self.conn.commit()
        return {"id": cs_id, **data}

    # ── foreshadows ──

    async def get_foreshadows(self, novel_id: str):
        cursor = await self.conn.execute(
            "SELECT * FROM foreshadows WHERE novel_id = ?", (novel_id,))
        return [dict(row) for row in await cursor.fetchall()]

    async def create_foreshadow(self, data: dict):
        import uuid
        fid = data.get("id", str(uuid.uuid4()))
        await self.conn.execute(
            """INSERT INTO foreshadows (id, novel_id, title, description, status)
               VALUES (?, ?, ?, ?, ?)""",
            (fid, data["novel_id"], data.get("title", ""),
             data.get("description", ""), data.get("status", "unused")))
        await self.conn.commit()
        return await self._get_foreshadow(fid)

    async def update_foreshadow(self, fid: str, data: dict):
        fields = []
        values = []
        for k in ("title", "description", "status", "chapter_id"):
            if k in data:
                fields.append(f"{k} = ?")
                values.append(data[k])
        if not fields:
            return await self._get_foreshadow(fid)
        fields.append("updated_at = datetime('now')")
        values.append(fid)
        await self.conn.execute(
            f"UPDATE foreshadows SET {', '.join(fields)} WHERE id = ?", values)
        await self.conn.commit()
        return await self._get_foreshadow(fid)

    async def delete_foreshadow(self, fid: str):
        await self.conn.execute("DELETE FROM foreshadows WHERE id = ?", (fid,))
        await self.conn.commit()

    async def _get_foreshadow(self, fid: str):
        cursor = await self.conn.execute(
            "SELECT * FROM foreshadows WHERE id = ?", (fid,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    # ── generation_logs ──

    async def create_generation_log(self, data: dict):
        import uuid
        log_id = data.get("id", str(uuid.uuid4()))
        await self.conn.execute(
            """INSERT INTO generation_logs (id, novel_id, generation_id, prompt, result, model, tokens_used)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (log_id, data["novel_id"], data["generation_id"],
             data.get("prompt", ""), data.get("result", ""),
             data.get("model", ""), data.get("tokens_used", 0)))
        await self.conn.commit()
        return {"id": log_id, **data}

    # ── app_settings ──

    async def get_settings(self):
        cursor = await self.conn.execute("SELECT * FROM app_settings")
        rows = await cursor.fetchall()
        return {row["key"]: row["value"] for row in rows}

    async def update_settings(self, data: dict):
        for k, v in data.items():
            await self.conn.execute(
                "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
                (k, str(v)))
        await self.conn.commit()
        return await self.get_settings()
