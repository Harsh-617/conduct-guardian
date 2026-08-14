"""Tamper-evident evidence ledger — hash chaining and verification.

This is the module a technical judge will attack, so the design is deliberate:

* Each entry hashes `prev_hash + canonical(payload)`. Changing any earlier
  entry changes every hash after it, so tampering can't be localised.
* The exact bytes that were hashed are stored in `payload`. Verification
  rehashes that frozen copy — it never re-derives the payload from live rows.
  Re-deriving would mean an edit to a `screening_results` row also changes what
  gets hashed, and the chain would silently still "pass". Storing the payload is
  what makes an edit detectable.
* `payload` is canonical JSON: sorted keys, no insignificant whitespace, UTF-8.
  Two runs on the same data must produce byte-identical input to the hash.

Honest limitation, and the right answer if asked on stage: this proves internal
consistency, not third-party non-repudiation. Anyone with write access to the
whole table could recompute the entire chain. Production would anchor the head
hash somewhere the agency cannot rewrite — a notarisation service, a periodic
signed head, or an append-only WORM store. That's a deployment change, not a
redesign.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EvidenceLedgerEntry, ScreeningResult

#: prev_hash of the very first entry. 64 zeroes keeps the column width uniform.
GENESIS_PREV_HASH = "0" * 64

#: Serialises appends within this process. Read-then-write on the chain head is
#: a classic race: two concurrent /screen calls both read head N, both chain
#: onto it, and the second one's prev_hash no longer matches its predecessor —
#: verification then reports the chain broken on data nobody tampered with.
#: This is not hypothetical; the 4-way-concurrent seeder produced exactly that.
_append_lock = asyncio.Lock()

#: Arbitrary constant key for the Postgres transaction-level advisory lock that
#: guards appends across processes. The in-process lock above is enough for the
#: single-worker deployment in render.yaml, but the advisory lock means adding a
#: worker can't silently start corrupting the chain.
_LEDGER_ADVISORY_LOCK_KEY = 8_912_004_471


def canonical_payload(
    *,
    screening_result_id: int,
    message_id: int,
    violation: bool,
    rule: str | None,
    quoted_phrase: str | None,
    explanation: str,
    suggested_rewrite: str | None,
    created_at: dt.datetime,
) -> str:
    """Serialise the facts being attested, deterministically.

    Timestamps are normalised to UTC and rendered with an explicit offset so a
    round-trip through a database that returns naive datetimes still hashes
    identically.
    """
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=dt.UTC)
    payload = {
        "screening_result_id": screening_result_id,
        "message_id": message_id,
        "violation": violation,
        "rule": rule,
        "quoted_phrase": quoted_phrase,
        "explanation": explanation,
        "suggested_rewrite": suggested_rewrite,
        "created_at": created_at.astimezone(dt.UTC).isoformat(),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_hash(prev_hash: str, payload: str) -> str:
    return hashlib.sha256(f"{prev_hash}{payload}".encode()).hexdigest()


async def get_head(session: AsyncSession) -> EvidenceLedgerEntry | None:
    """Most recent entry, which the next one chains onto."""
    result = await session.execute(
        select(EvidenceLedgerEntry).order_by(EvidenceLedgerEntry.id.desc()).limit(1)
    )
    return result.scalars().first()


async def append_entry(
    session: AsyncSession, screening_result: ScreeningResult
) -> EvidenceLedgerEntry:
    """Chain a new entry onto the head. Caller commits.

    Appends are serialised on two levels — an in-process lock, and a Postgres
    transaction-level advisory lock for the multi-process case. Read-then-write
    on the head is otherwise racy, and a race here doesn't corrupt data, it
    does something worse: it makes the integrity check report tampering that
    never happened, which is the one thing this feature exists to be trusted
    about.

    The advisory lock is held until the caller's transaction ends, so the
    caller must commit (or roll back) promptly after this returns.
    """
    async with _append_lock:
        if session.bind is not None and session.bind.dialect.name == "postgresql":
            await session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": _LEDGER_ADVISORY_LOCK_KEY},
            )

        head = await get_head(session)
        prev_hash = head.entry_hash if head else GENESIS_PREV_HASH

        payload = canonical_payload(
            screening_result_id=screening_result.id,
            message_id=screening_result.message_id,
            violation=screening_result.violation,
            rule=screening_result.rule,
            quoted_phrase=screening_result.quoted_phrase,
            explanation=screening_result.explanation,
            suggested_rewrite=screening_result.suggested_rewrite,
            created_at=screening_result.created_at,
        )
        entry = EvidenceLedgerEntry(
            screening_result_id=screening_result.id,
            entry_hash=compute_hash(prev_hash, payload),
            prev_hash=prev_hash,
            payload=payload,
        )
        session.add(entry)
        # Flush inside the lock so the row (and its id) exists before another
        # appender can read the head. Releasing the lock before the INSERT
        # lands would reintroduce the exact race this guards against.
        await session.flush()
        return entry


@dataclass
class RowVerdict:
    id: int
    screening_result_id: int
    stored_hash: str
    computed_hash: str
    ok: bool
    reason: str | None


@dataclass
class ChainVerdict:
    valid: bool
    total: int
    failed: int
    first_broken_id: int | None
    rows: list[RowVerdict]


async def verify_chain(session: AsyncSession) -> ChainVerdict:
    """Recompute every hash from stored payloads and compare to what's stored.

    This is the real logic behind the UI's "Verify Chain Integrity" button. It
    checks two independent things per row: that the row's own hash matches its
    payload, and that its `prev_hash` actually points at the previous row's
    hash — so both a mutated row and a removed/reordered row are caught.
    """
    result = await session.execute(
        select(EvidenceLedgerEntry).order_by(EvidenceLedgerEntry.id.asc())
    )
    entries = list(result.scalars().all())

    rows: list[RowVerdict] = []
    expected_prev = GENESIS_PREV_HASH
    first_broken: int | None = None

    for entry in entries:
        reasons: list[str] = []

        if (entry.prev_hash or GENESIS_PREV_HASH) != expected_prev:
            reasons.append("prev_hash does not match the previous entry's hash")

        computed = compute_hash(entry.prev_hash or GENESIS_PREV_HASH, entry.payload)
        if computed != entry.entry_hash:
            reasons.append("entry_hash does not match a rehash of the stored payload")

        ok = not reasons
        if not ok and first_broken is None:
            first_broken = entry.id

        rows.append(
            RowVerdict(
                id=entry.id,
                screening_result_id=entry.screening_result_id,
                stored_hash=entry.entry_hash,
                computed_hash=computed,
                ok=ok,
                reason="; ".join(reasons) if reasons else None,
            )
        )
        # Walk with the STORED hash, not the recomputed one, so a single broken
        # row is reported once rather than cascading a failure into every row
        # after it.
        expected_prev = entry.entry_hash

    failed = sum(1 for r in rows if not r.ok)
    return ChainVerdict(
        valid=failed == 0,
        total=len(rows),
        failed=failed,
        first_broken_id=first_broken,
        rows=rows,
    )
