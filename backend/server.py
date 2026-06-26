from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.api.crud import router as crud_router
from backend.api.generation import router as generation_router
from backend.config import load_llm_config

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await load_llm_config()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="WriteAuto API", version="2.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes registered first so they take priority over SPA fallback
    app.include_router(crud_router)
    app.include_router(generation_router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    if FRONTEND_DIST.is_dir():
        # Serve static assets (JS, CSS, images)
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        # SPA fallback: serve index.html for all other paths (Vue Router handles them)
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_frontend(full_path: str):
            path = FRONTEND_DIST / full_path
            if path.suffix and path.is_file():
                return FileResponse(path)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app
