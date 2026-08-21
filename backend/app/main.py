"""FastAPI application entrypoint.

Two deployable services, per the PRD: this backend and the Next.js frontend.
Nothing else — no queue, no workers, no container orchestration.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.channels.email_poller import poll_forever
from app.config import get_settings
from app.db import engine
from app.routers import accounts, agencies, coaching, dashboard, hardship, ledger, screen, timeline

logger = logging.getLogger("conduct_guardian")

# uvicorn's default logging config (see uvicorn.config.LOGGING_CONFIG) only
# configures its own "uvicorn"/"uvicorn.access" loggers and leaves the root
# logger untouched, which defaults to WARNING with no handlers. Without a
# handler of our own, every logger.info() call on this logger (and its
# children, e.g. "conduct_guardian.email") falls through to Python's
# logging.lastResort — a hidden fallback handler that has its OWN hardcoded
# WARNING threshold, so INFO logs vanish silently even if this logger's level
# is set to INFO. A live demo debugged over warnings-and-errors-only is not
# debuggable, so this app owns its own logger explicitly instead of trusting
# uvicorn's or Python's defaults.
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    )
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

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

    # Confirm what was actually read from the environment — never the secret
    # value itself, just whether it's present — so a misconfigured .env (or a
    # server started from the wrong working directory, which silently yields
    # empty settings rather than an error) is visible at a glance in the logs
    # instead of manifesting as "the poller just doesn't seem to do anything."
    logger.info(
        "email config: EMAIL_ADDRESS=%s EMAIL_APP_PASSWORD=%s DEMO_COLLECTOR_NAME=%s",
        "set" if settings.email_address else "MISSING",
        "set" if settings.email_app_password else "MISSING",
        settings.demo_collector_name,
    )

    email_task: asyncio.Task | None = None
    if settings.email_address and settings.email_app_password:
        email_task = asyncio.create_task(poll_forever())
    else:
        logger.warning(
            "EMAIL_ADDRESS/EMAIL_APP_PASSWORD not set — email channel disabled."
        )

    yield

    if email_task is not None:
        email_task.cancel()
        with suppress(asyncio.CancelledError):
            await email_task
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


for module in (screen, dashboard, timeline, ledger, coaching, hardship, agencies, accounts):
    app.include_router(module.router, tags=[module.__name__.rsplit(".", 1)[-1]])
