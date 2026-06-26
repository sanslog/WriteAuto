from backend.db.database import Database


class CharacterRepo:
    def __init__(self, db: Database):
        self.db = db

    async def get_by_novel(self, novel_id: str):
        return await self.db.get_characters(novel_id)

    async def create(self, data: dict):
        return await self.db.create_character(data)

    async def update(self, char_id: str, data: dict):
        return await self.db.update_character(char_id, data)

    async def delete(self, char_id: str):
        return await self.db.delete_character(char_id)

    async def get_states(self, character_id: str):
        return await self.db.get_character_states(character_id)

    async def create_state(self, data: dict):
        return await self.db.create_character_state(data)
