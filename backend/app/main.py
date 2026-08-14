"""FastAPI application entrypoint.

Two deployable services, per the PRD: this backend and the Next.js frontend.
Nothing else — no queue, no workers, no container orchestration.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import engine
from app.routers import agencies, coaching, dashboard, hardship, ledger, screen, timeline

logger = logging.getLogger("conduct_guardian")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup warnings, not failures. The app must boot so /health answers and
    # the frontend can show a clear "backend not configured" state rather than
    # a dead host.
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY is not set — /screen will return 503.")
    if not settings.database_url:
        logger.warning("DATABASE_URL is not set — falling back to local SQLite.")
    yield
    await engine.dispose()


app = FastAPI(
    title="Conduct Guardian API",
    version="0.1.0",
    description=(
        "Screens debt-collection messages against Malaysian Consumer Credit Act "
        "2025 conduct rules, with a hash-chained evidence ledger."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Uniform error body so the UI renders a retry state, never a blank crash (PRD §9)."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "code": "internal_error",
            "message": "Something went wrong handling that request.",
            "retryable": True,
        },
    )


@app.get("/health")
async def health() -> dict[str, object]:
    """Liveness plus honest configuration state — used by /canary after deploy."""
    return {
        "status": "ok",
        "groq_configured": bool(settings.groq_api_key),
        "database_configured": bool(settings.database_url),
        "model": settings.groq_model,
    }


for module in (screen, dashboard, timeline, ledger, coaching, hardship, agencies):
    app.include_router(module.router, tags=[module.__name__.rsplit(".", 1)[-1]])
