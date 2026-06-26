import json
from typing import Any

from backend.db.database import get_db


class Bridge:
    """pywebview JS Bridge — synchronous CRUD operations exposed to frontend."""

    def get_novels(self) -> str:
        return self._json_result(self._sync(get_db().get_all_novels()))

    def get_novel(self, novel_id: str) -> str:
        return self._json_result(self._sync(get_db().get_novel(novel_id)))

    def create_novel(self, data: dict) -> str:
        return self._json_result(self._sync(get_db().create_novel(data)))

    def update_novel(self, novel_id: str, data: dict) -> str:
        return self._json_result(self._sync(get_db().update_novel(novel_id, data)))

    def delete_novel(self, novel_id: str) -> str:
        return self._json_result(self._sync(get_db().delete_novel(novel_id)))

    def get_plot_nodes(self, novel_id: str) -> str:
        return self._json_result(self._sync(get_db().get_plot_nodes(novel_id)))

    def create_plot_node(self, data: dict) -> str:
        return self._json_result(self._sync(get_db().create_plot_node(data)))

    def update_plot_node(self, node_id: str, data: dict) -> str:
        return self._json_result(self._sync(get_db().update_plot_node(node_id, data)))

    def delete_plot_node(self, node_id: str) -> str:
        return self._json_result(self._sync(get_db().delete_plot_node(node_id)))

    def get_chapters(self, novel_id: str) -> str:
        return self._json_result(self._sync(get_db().get_chapters(novel_id)))

    def get_chapter(self, chapter_id: str) -> str:
        return self._json_result(self._sync(get_db().get_chapter(chapter_id)))

    def create_chapter(self, data: dict) -> str:
        return self._json_result(self._sync(get_db().create_chapter(data)))

    def update_chapter(self, chapter_id: str, data: dict) -> str:
        return self._json_result(self._sync(get_db().update_chapter(chapter_id, data)))

    def delete_chapter(self, chapter_id: str) -> str:
        return self._json_result(self._sync(get_db().delete_chapter(chapter_id)))

    def get_characters(self, novel_id: str) -> str:
        return self._json_result(self._sync(get_db().get_characters(novel_id)))

    def create_character(self, data: dict) -> str:
        return self._json_result(self._sync(get_db().create_character(data)))

    def update_character(self, char_id: str, data: dict) -> str:
        return self._json_result(self._sync(get_db().update_character(char_id, data)))

    def delete_character(self, char_id: str) -> str:
        return self._json_result(self._sync(get_db().delete_character(char_id)))

    def get_foreshadows(self, novel_id: str) -> str:
        return self._json_result(self._sync(get_db().get_foreshadows(novel_id)))

    def create_foreshadow(self, data: dict) -> str:
        return self._json_result(self._sync(get_db().create_foreshadow(data)))

    def update_foreshadow(self, fid: str, data: dict) -> str:
        return self._json_result(self._sync(get_db().update_foreshadow(fid, data)))

    def delete_foreshadow(self, fid: str) -> str:
        return self._json_result(self._sync(get_db().delete_foreshadow(fid)))

    def get_settings(self) -> str:
        return self._json_result(self._sync(get_db().get_settings()))

    def update_settings(self, data: dict) -> str:
        return self._json_result(self._sync(get_db().update_settings(data)))

    @staticmethod
    def _json_result(data: Any) -> str:
        return json.dumps({"success": True, "data": data}, ensure_ascii=False)

    @staticmethod
    def _sync(coro):
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        import concurrent.futures

        future = concurrent.futures.Future()

        async def run():
            try:
                result = await coro
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)

        loop.call_soon_threadsafe(lambda: asyncio.create_task(run()))
        return future.result()
