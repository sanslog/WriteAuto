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
# 1. Analysis — scan main.py and all its static imports, exclude test packages
# ---------------------------------------------------------------------------
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # FastAPI auto-discovery
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
    ],
    hookspath=[],
    hooksconfig={},
    # Exclude test packages — not needed in the bundled .exe
    excludes=[
        'pytest',
        'pytest_asyncio',
        '_pytest',
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
