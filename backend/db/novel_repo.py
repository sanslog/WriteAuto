from backend.db.database import Database


class NovelRepo:
    def __init__(self, db: Database):
        self.db = db

    async def get_all(self):
        return await self.db.get_all_novels()

    async def get(self, novel_id: str):
        return await self.db.get_novel(novel_id)

    async def create(self, data: dict):
        return await self.db.create_novel(data)

    async def update(self, novel_id: str, data: dict):
        return await self.db.update_novel(novel_id, data)

    async def delete(self, novel_id: str):
        return await self.db.delete_novel(novel_id)
