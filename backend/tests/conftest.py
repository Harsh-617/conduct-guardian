"""Shared fixtures: an isolated in-memory SQLite database per test.

`Base.metadata.create_all` is used instead of running the Alembic migration,
since that's faster and keeps the unit suite independent of alembic being
installed/configured — 0001_initial.py is exercised separately (e.g. by
running it against a real Postgres instance), not by this suite.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass

import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Account, Agency, Channel, Collector, Message, ScreeningResult


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """A fresh in-memory SQLite AsyncSession, isolated per test.

    StaticPool + check_same_thread=False keeps the same in-memory database
    alive across the several connections SQLAlchemy's async engine opens
    within a single test — a plain in-memory SQLite database is otherwise
    dropped the instant its one connection closes.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session

    await engine.dispose()


@dataclass
class Seeded:
    """Everything a factory() call just inserted, by name."""

    agency: Agency
    collector: Collector
    account: Account
    message: Message
    screening: ScreeningResult


@pytest_asyncio.fixture
async def factory(
    session: AsyncSession,
) -> Callable[..., Awaitable[Seeded]]:
    """Factory fixture: `await factory()` inserts an Agency, Collector,
    Account, Message, and ScreeningResult in one call, flushed so every row
    has an id.

    The Agency/Collector/Account are created once (on the first call) and
    reused on later calls within the same test, so repeated calls build up a
    realistic list of messages/screening results against one account —
    exactly the shape the ledger chain tests need.
    """
    shared: dict[str, object] = {}

    async def _make(
        *,
        violation: bool = False,
        rule: str | None = None,
        quoted_phrase: str | None = None,
        explanation: str = "test explanation",
        suggested_rewrite: str | None = None,
        occurred_at: dt.datetime | None = None,
    ) -> Seeded:
        if "account" not in shared:
            agency = Agency(name="Test Agency")
            collector = Collector(name="Test Collector", role="collector")
            account = Account(external_id="4471")
            session.add_all([agency, collector, account])
            await session.flush()
            shared["agency"] = agency
            shared["collector"] = collector
            shared["account"] = account

        message = Message(
            account_id=shared["account"].id,
            collector_id=shared["collector"].id,
            agency_id=shared["agency"].id,
            channel=Channel.whatsapp,
            raw_text="Pay now or we will escalate this.",
            is_customer=False,
            occurred_at=occurred_at or dt.datetime.now(dt.UTC),
        )
        session.add(message)
        await session.flush()

        screening = ScreeningResult(
            message_id=message.id,
            violation=violation,
            rule=rule,
            quoted_phrase=quoted_phrase,
            explanation=explanation,
            suggested_rewrite=suggested_rewrite,
            model="test-model",
            latency_ms=1,
        )
        session.add(screening)
        await session.flush()

        return Seeded(
            agency=shared["agency"],
            collector=shared["collector"],
            account=shared["account"],
            message=message,
            screening=screening,
        )

    return _make
