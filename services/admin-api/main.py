"""Admin API — Quiz Bot tizim boshqaruvi."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text

from deps import engine, AsyncSessionLocal
from routers import router

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "info").upper(), logging.INFO)
)
logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = os.getenv(
    "ADMIN_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173",
).split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Admin API ishga tushdi")
    yield
    await engine.dispose()
    logger.info("Admin API to'xtatildi")


app = FastAPI(
    title="Quiz Bot Admin API",
    version="1.0.0",
    description="Quiz Bot tizimini boshqarish uchun REST API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# ── Static frontend ──────────────────────────────────────────────
_FRONTEND = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.isdir(_FRONTEND):
    app.mount(
        "/static", StaticFiles(directory=os.path.join(_FRONTEND, "src")), name="static"
    )

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(os.path.join(_FRONTEND, "index.html"))


@app.get("/health", tags=["system"])
async def health():
    db_status = "ok"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "healthy",
        "service": "admin-api",
        "version": "1.0.0",
        "checks": {"database": db_status},
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("ADMIN_API_PORT", "8004"))
    uvicorn.run(app, host="0.0.0.0", port=port)
