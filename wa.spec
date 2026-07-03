# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for WriteAuto
#
# Build command:
#   pyinstaller wa.spec
#
# Or via uv:
#   uv run pyinstaller wa.spec

import sys
from pathlib import Path

block_cipher = None

# ---------------------------------------------------------------------------
# 收集所有需要传递依赖的包（子模块 + C扩展二进制 + 数据文件）
# ---------------------------------------------------------------------------
from PyInstaller.utils.hooks import collect_submodules, collect_all

_BINARIES = []
_DATAS = []
_HIDDEN_IMPORTS = []

_COLLECT_PACKAGES = [
    # 核心框架
    'langgraph',
    'langchain_core',
    'openai',
    # C 扩展包（必须收集 .pyd 二进制文件）
    'pydantic',
    'pydantic_core',
    'xxhash',
    'jiter',
    'aiosqlite',
    # 网络层
    'httpx',
    'httpcore',
    'sniffio',
    'anyio',
    'charset_normalizer',
    # multipart 表单解析
    'multipart',
    # 类型工具
    'typing_extensions',
]

for _pkg in _COLLECT_PACKAGES:
    _b, _d, _h = collect_all(_pkg)
    _BINARIES.extend(_b)
    _DATAS.extend(_d)
    _HIDDEN_IMPORTS.extend(_h)

# ---------------------------------------------------------------------------
# 1. Analysis — scan main.py and all its static imports, exclude test packages
# ---------------------------------------------------------------------------
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=_BINARIES,
    datas=_DATAS,
    hiddenimports=_HIDDEN_IMPORTS + [
        # FastAPI / uvicorn auto-discovery
        'uvicorn.logging',
        'uvicorn.loops.auto',
        'uvicorn.protocols.http.auto',
        # Backend modules (explicit to be safe)
        'backend.server',
        'backend.config',
        'backend.bridge',
        'backend.api.crud',
        'backend.api.common',
        'backend.api.generation',
        'backend.db.database',
        'backend.db.models',
        'backend.db.novel_repo',
        'backend.db.chapter_repo',
        'backend.db.outline_repo',
        'backend.db.character_repo',
        'backend.db.foreshadow_repo',
        'backend.storage.markdown',
        'backend.storage.file_manager',
        'backend.llm.factory',
        'backend.llm.provider',
        'backend.llm.openai_provider',
        'backend.llm.prompts',
        'backend.services.context',
        'backend.services.cursor',
        'backend.services.legality',
        'backend.services.style_extractor',
        'backend.agent.graph',
        'backend.agent.state',
        'backend.agent.cancellation',
        'backend.agent.nodes.init_check',
        'backend.agent.nodes.character_fetch',
        'backend.agent.nodes.injection_context',
        'backend.agent.nodes.injection_foreshadow',
        'backend.agent.nodes.content_generation',
        'backend.agent.nodes.content_judge',
        'backend.agent.nodes.modify_loop',
        # pywebview
        'webview.platforms.win32',
    ] + collect_submodules('langgraph')          # 兜底：langgraph 所有子模块
    + collect_submodules('langgraph.checkpoint')  # langgraph-checkpoint 所有子模块
    + collect_submodules('langchain_core')        # langchain-core 所有子模块
    + collect_submodules('openai'),               # openai SDK 所有子模块
    hookspath=[],
    hooksconfig={},
    excludes=[
        'pytest',
        'pytest_asyncio',
        '_pytest',
        'unittest',
        'unittest.mock',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ---------------------------------------------------------------------------
# 2. Include the pre-built frontend (Vue SPA) as static data
# ---------------------------------------------------------------------------
# The server resolves frontend/dist relative to the backend package location.
# PyInstaller extracts to a temp dir (_MEIPASS), so we mirror the same layout:
#   _MEIPASS/frontend/dist/index.html
#   _MEIPASS/frontend/dist/assets/...
frontend_dist = Tree(
    str(Path('frontend') / 'dist'),
    prefix=str(Path('frontend') / 'dist'),
)

# ---------------------------------------------------------------------------
# 3. PYZ — compressed bytecode archive
# ---------------------------------------------------------------------------
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ---------------------------------------------------------------------------
# 4. EXE — the main executable stub
# ---------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    frontend_dist,
    [],
    name='WriteAuto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,         # no console window for the GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['wa.ico'],
)
