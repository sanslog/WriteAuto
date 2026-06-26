from pathlib import Path

from backend.config import NOVELS_DIR


class FileManager:
    @staticmethod
    def novel_dir(novel_id: str) -> Path:
        p = NOVELS_DIR / novel_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    @staticmethod
    def chapters_dir(novel_id: str) -> Path:
        p = NOVELS_DIR / novel_id / "chapters"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @staticmethod
    def outline_path(novel_id: str) -> Path:
        return NOVELS_DIR / novel_id / "outline.md"

    @staticmethod
    def chapter_path(novel_id: str, chapter_id: str) -> Path:
        return NOVELS_DIR / novel_id / "chapters" / f"{chapter_id}.md"
