"""Async engine, session factory, and the FastAPI session dependency."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(AsyncAttrs, DeclarativeBase):
    """Declarative base for all models.

    AsyncAttrs gives every model an `.awaitable_attrs` accessor, which avoids
    accidental lazy-load IO in async context.
    """


_settings = get_settings()

engine = create_async_engine(
    _settings.async_database_url,
    echo=False,
    pool_pre_ping=True,
    # Neon closes idle connections; recycling well inside that avoids the
    # "server closed the connection unexpectedly" that bites free-tier apps
    # that have been sitting idle between demo runs.
    pool_recycle=280,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
