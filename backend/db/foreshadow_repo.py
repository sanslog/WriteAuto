from backend.db.database import Database


class ForeshadowRepo:
    def __init__(self, db: Database):
        self.db = db

    async def get_by_novel(self, novel_id: str):
        return await self.db.get_foreshadows(novel_id)

    async def create(self, data: dict):
        return await self.db.create_foreshadow(data)

    async def update(self, fid: str, data: dict):
        return await self.db.update_foreshadow(fid, data)

    async def delete(self, fid: str):
        return await self.db.delete_foreshadow(fid)
