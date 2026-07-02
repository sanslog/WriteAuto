import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# frozen是pyinstaller打包后会自动生成的属性，如果处于非打包状态将会直接启动项目
RUN_DIRECT = not getattr(sys, "frozen", False)

def _default_data_dir() -> Path:
    """Determine data directory.

    Direct run   → project_root/data
    Packaged .exe → exe所在目录/data（固定位置，与原始 BASE_DIR/data 逻辑一致）
    """
    if RUN_DIRECT:
        return BASE_DIR / "data"
    # 打包后：exe 父目录就是用户放置 .exe 的位置，data 文件夹固定在其旁边
    return Path(sys.executable).parent / "data"

DATA_DIR = Path(os.getenv("WRITEAUTO_DATA_DIR", _default_data_dir()))
NOVELS_DIR = DATA_DIR / "novels"
DB_PATH = Path(os.getenv("WRITEAUTO_DB_PATH", DATA_DIR / "writeauto.db"))

# LLM configuration (defaults — overridden from DB via load_llm_config())
LLM_PROVIDER = "openai"
LLM_API_KEY = "sk-xxxxxxxx"
LLM_BASE_URL = "https://api.deepseek.com/v1"
LLM_MODEL = "deepseek-chat"
LLM_MAX_TOKENS = 8192
LLM_GENERATION_MAX_TOKENS = 65536  # 小说内容生成专用，远大于提取/分类场景
LLM_TEMPERATURE = 0.8


_LLM_KEY_MAP = {
    "llm_provider": "LLM_PROVIDER",
    "llm_api_key": "LLM_API_KEY",
    "llm_base_url": "LLM_BASE_URL",
    "llm_model": "LLM_MODEL",
    "llm_max_tokens": "LLM_MAX_TOKENS",
    "llm_temperature": "LLM_TEMPERATURE",
}


async def load_llm_config():
    """Load LLM config from the app_settings table into module-level variables."""
    from backend.db.database import Database

    db = Database(DB_PATH)
    await db.init()
    try:
        settings = await db.get_settings()
        _apply_settings(settings)
    finally:
        await db.close()


def update_llm_config(key: str, value: str):
    """Update a single in-memory LLM config value (called after PUT /settings)."""
    var_name = _LLM_KEY_MAP.get(key)
    if var_name is None:
        return
    g = globals()
    if var_name == "LLM_MAX_TOKENS":
        g[var_name] = int(value)
    elif var_name == "LLM_TEMPERATURE":
        g[var_name] = float(value)
    else:
        g[var_name] = value


def _apply_settings(settings: dict):
    for key, value in settings.items():
        update_llm_config(key, value)

# Server
API_HOST = "127.0.0.1"
API_PORT = 21278

# Generation limits
MAX_MODIFICATION_COUNT = 20
MAX_CONTEXT_CHARS = 15000
MIN_CHAPTER_CHARS = 2000
SPLIT_THRESHOLD_CHARS = 4000
RECENT_CHAPTERS_COUNT = 3
RECENT_CHAPTER_CHAR_LIMIT = 5000
