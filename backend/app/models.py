"""SQLAlchemy 2.0 models.

Portable across Postgres (production, Neon) and SQLite (tests). Enums are
mapped with `native_enum=False` so they become VARCHAR + CHECK on both backends
rather than a Postgres-only ENUM type — that keeps the test suite runnable with
no database server.
"""

from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db import Base


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Channel(str, enum.Enum):
    whatsapp = "whatsapp"
    sms = "sms"
    call = "call"
    email = "email"


class HardshipType(str, enum.Enum):
    job_loss = "job_loss"
    health_crisis = "health_crisis"
    bereavement = "bereavement"
    financial_distress = "financial_distress"


ChannelType = Enum(Channel, native_enum=False, length=16, validate_strings=True)
HardshipEnumType = Enum(
    HardshipType, native_enum=False, length=24, validate_strings=True
)


class UTCDateTime(TypeDecorator):
    """`DateTime(timezone=True)` that guarantees a tz-aware UTC value on read.

    Postgres (production) round-trips `timestamptz` correctly on its own —
    this is a no-op there. SQLite (local dev) has no real timezone-aware
    column type: SQLAlchemy's sqlite dialect silently drops tzinfo on write
    and hands back a naive `datetime` on read, even though the column is
    declared `timezone=True`. A naive `datetime` serializes to JSON with no
    UTC offset (`"...T16:54:30"` instead of `"...T16:54:30+00:00"`), and the
    frontend's `new Date(iso)` then parses that as *local* time per the
    ECMAScript date-string spec — silently misreading a UTC instant as
    already being in the viewer's timezone. For Malaysia (UTC+8) that's
    exactly an 8-hour, sometimes date-shifting, display error. Every value
    written here is already UTC (see `run_screening_pipeline`), so fixing the
    read side alone is sufficient — no data migration needed.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: dt.datetime | None, dialect) -> dt.datetime | None:
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(dt.UTC)
        return value

    def process_result_value(self, value: dt.datetime | None, dialect) -> dt.datetime | None:
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=dt.UTC)
        return value


TimestampTZ = UTCDateTime()


class Agency(Base):
    __tablename__ = "agencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        TimestampTZ, server_default=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(back_populates="agency")


class Collector(Base):
    __tablename__ = "collectors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(60), default="collector")
    created_at: Mapped[dt.datetime] = mapped_column(
        TimestampTZ, server_default=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(back_populates="collector")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    # The customer-facing reference, e.g. "4471" — matches the UI mockup.
    external_id: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    # Real channel identity, used to resolve an inbound email/SMS to its
    # account by who actually sent it — never by a manually-typed tag. Null
    # until the sender's first message; unique so one contact never splits
    # across two accounts.
    contact_email: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    contact_phone: Mapped[str | None] = mapped_column(
        String(32), unique=True, index=True, nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        TimestampTZ, server_default=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(back_populates="account")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    collector_id: Mapped[int] = mapped_column(ForeignKey("collectors.id"), index=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)

    channel: Mapped[Channel] = mapped_column(ChannelType)
    raw_text: Mapped[str] = mapped_column(Text)
    # True when the text is the borrower speaking, not the collector. Hardship
    # detection only ever runs on customer-side text.
    is_customer: Mapped[bool] = mapped_column(Boolean, default=False)

    occurred_at: Mapped[dt.datetime] = mapped_column(TimestampTZ, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        TimestampTZ, server_default=func.now()
    )

    account: Mapped["Account"] = relationship(back_populates="messages")
    collector: Mapped["Collector"] = relationship(back_populates="messages")
    agency: Mapped["Agency"] = relationship(back_populates="messages")
    screening: Mapped["ScreeningResult | None"] = relationship(
        back_populates="message", uselist=False
    )
    hardship_signals: Mapped[list["HardshipSignal"]] = relationship(
        back_populates="message"
    )


# Powers the R5 contacts-per-week check and the timeline burst heuristic.
Index("ix_messages_account_occurred", Message.account_id, Message.occurred_at)


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id"), unique=True, index=True
    )

    violation: Mapped[bool] = mapped_column(Boolean, index=True)
    rule: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    quoted_phrase: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str] = mapped_column(Text)
    suggested_rewrite: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Provenance: which model produced this verdict. A judge asking "is this
    # real?" gets a per-row answer.
    model: Mapped[str] = mapped_column(String(60), default="")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[dt.datetime] = mapped_column(
        TimestampTZ, server_default=func.now()
    )

    message: Mapped["Message"] = relationship(back_populates="screening")
    ledger_entry: Mapped["EvidenceLedgerEntry | None"] = relationship(
        back_populates="screening_result", uselist=False
    )


class EvidenceLedgerEntry(Base):
    """Append-only, hash-chained audit record.

    Never UPDATE or DELETE a row in this table. The chain is what makes the
    ledger tamper-evident, and `/ledger/verify` recomputes it from scratch.
    """

    __tablename__ = "evidence_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    screening_result_id: Mapped[int] = mapped_column(
        ForeignKey("screening_results.id"), unique=True, index=True
    )

    entry_hash: Mapped[str] = mapped_column(String(64), index=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Frozen copy of exactly what was hashed. Without this, verification would
    # re-derive the payload from live rows and a later edit elsewhere would
    # silently "fix" the chain instead of breaking it.
    payload: Mapped[str] = mapped_column(Text)

    created_at: Mapped[dt.datetime] = mapped_column(
        TimestampTZ, server_default=func.now()
    )

    screening_result: Mapped["ScreeningResult"] = relationship(
        back_populates="ledger_entry"
    )


class HardshipSignal(Base):
    __tablename__ = "hardship_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), index=True)
    signal_type: Mapped[HardshipType] = mapped_column(HardshipEnumType, index=True)
    quoted_text: Mapped[str] = mapped_column(Text)
    detected_at: Mapped[dt.datetime] = mapped_column(
        TimestampTZ, server_default=func.now()
    )

    message: Mapped["Message"] = relationship(back_populates="hardship_signals")
