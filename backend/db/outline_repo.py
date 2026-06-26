from backend.db.database import Database


class OutlineRepo:
    def __init__(self, db: Database):
        self.db = db

    async def get_by_novel(self, novel_id: str):
        return await self.db.get_plot_nodes(novel_id)

    async def get(self, node_id: str):
        return await self.db._get_plot_node(node_id)

    async def create(self, data: dict):
        return await self.db.create_plot_node(data)

    async def update(self, node_id: str, data: dict):
        return await self.db.update_plot_node(node_id, data)

    async def delete(self, node_id: str):
        return await self.db.delete_plot_node(node_id)
