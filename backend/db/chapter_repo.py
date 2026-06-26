from backend.db.database import Database


class ChapterRepo:
    def __init__(self, db: Database):
        self.db = db

    async def get_by_novel(self, novel_id: str):
        return await self.db.get_chapters(novel_id)

    async def get(self, chapter_id: str):
        return await self.db.get_chapter(chapter_id)

    async def get_by_status(self, novel_id: str, status: str):
        return await self.db.get_chapters_by_status(novel_id, status)

    async def create(self, data: dict):
        return await self.db.create_chapter(data)

    async def update(self, chapter_id: str, data: dict):
        return await self.db.update_chapter(chapter_id, data)

    async def delete(self, chapter_id: str):
        return await self.db.delete_chapter(chapter_id)
