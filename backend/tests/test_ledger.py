"""Tests for the tamper-evident evidence ledger (app/ledger.py).

The hash chain is the product's central claim, so these are written like a
technical judge would attack it: tamper with a stored payload, tamper with a
stored hash, delete a row outright, and confirm verify_chain() catches every
case and pinpoints exactly where the chain broke.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ledger import (
    GENESIS_PREV_HASH,
    append_entry,
    canonical_payload,
    compute_hash,
    verify_chain,
)
from app.models import EvidenceLedgerEntry


async def _append_n(session: AsyncSession, factory, n: int) -> list[EvidenceLedgerEntry]:
    """Append n ledger entries in order, commit once, and return them in order."""
    entries = []
    for i in range(n):
        seeded = await factory(explanation=f"entry {i}")
        entries.append(await append_entry(session, seeded.screening))
    await session.commit()
    return entries


async def test_first_entry_uses_genesis_prev_hash(session, factory):
    seeded = await factory()
    entry = await append_entry(session, seeded.screening)
    await session.commit()

    assert entry.prev_hash == GENESIS_PREV_HASH
    assert entry.prev_hash == "0" * 64


async def test_chain_links_each_entry_to_the_previous(session, factory):
    entries = await _append_n(session, factory, 5)

    for earlier, later in zip(entries, entries[1:]):
        assert later.prev_hash == earlier.entry_hash


async def test_verify_passes_on_an_untampered_chain(session, factory):
    await _append_n(session, factory, 5)

    verdict = await verify_chain(session)

    assert verdict.valid is True
    assert verdict.total == 5
    assert verdict.failed == 0
    assert verdict.first_broken_id is None
    assert all(row.ok for row in verdict.rows)


async def test_tampering_with_a_stored_payload_is_detected(session, factory):
    """THE HEADLINE TEST.

    Append 5 entries, then directly UPDATE entry #3's stored `payload` column
    — the exact move a corrupted agency or a buggy write path would make on a
    live table. verify_chain() rehashes from the (now tampered) stored
    payload, so it must see the recomputed hash no longer matches the stored
    entry_hash, mark the chain invalid, and name entry #3 — not #4 (cascade),
    not nothing (false negative) — as the first broken row.
    """
    entries = await _append_n(session, factory, 5)
    tampered = entries[2]  # entry #3, 1-indexed

    await session.execute(
        update(EvidenceLedgerEntry)
        .where(EvidenceLedgerEntry.id == tampered.id)
        .values(payload='{"screening_result_id":999,"tampered":true}')
    )
    await session.commit()

    verdict = await verify_chain(session)

    assert verdict.valid is False
    assert verdict.failed >= 1
    assert verdict.first_broken_id == tampered.id


async def test_tampering_with_a_stored_hash_is_detected(session, factory):
    entries = await _append_n(session, factory, 5)
    tampered = entries[1]  # entry #2

    await session.execute(
        update(EvidenceLedgerEntry)
        .where(EvidenceLedgerEntry.id == tampered.id)
        .values(entry_hash="f" * 64)
    )
    await session.commit()

    verdict = await verify_chain(session)

    assert verdict.valid is False
    row = next(r for r in verdict.rows if r.id == tampered.id)
    assert row.ok is False
    assert row.stored_hash == "f" * 64
    assert row.computed_hash != row.stored_hash


async def test_deleting_a_middle_entry_breaks_the_chain(session, factory):
    entries = await _append_n(session, factory, 5)
    victim = entries[2]  # entry #3
    following = entries[3]  # entry #4, whose stored prev_hash now points nowhere

    await session.execute(
        delete(EvidenceLedgerEntry).where(EvidenceLedgerEntry.id == victim.id)
    )
    await session.commit()

    verdict = await verify_chain(session)

    assert verdict.valid is False
    assert verdict.total == 4  # one entry gone
    row = next(r for r in verdict.rows if r.id == following.id)
    assert row.ok is False
    assert "prev_hash" in row.reason


def test_canonical_payload_is_stable():
    kwargs = dict(
        screening_result_id=1,
        message_id=2,
        violation=True,
        rule="R2_THREATS",
        quoted_phrase="we will come to your house",
        explanation="threatens property seizure without legal basis",
        suggested_rewrite="Please contact us to discuss repayment options.",
        created_at=dt.datetime(2026, 6, 1, 12, 0, 0, tzinfo=dt.UTC),
    )

    first = canonical_payload(**kwargs)
    second = canonical_payload(**kwargs)

    # Same inputs -> byte-identical output, every time.
    assert first == second
    assert compute_hash(GENESIS_PREV_HASH, first) == compute_hash(GENESIS_PREV_HASH, second)

    # Key order at the *call site* must not change the hash — canonical_payload
    # always sorts keys before serialising.
    reordered = canonical_payload(
        created_at=kwargs["created_at"],
        suggested_rewrite=kwargs["suggested_rewrite"],
        explanation=kwargs["explanation"],
        quoted_phrase=kwargs["quoted_phrase"],
        rule=kwargs["rule"],
        violation=kwargs["violation"],
        message_id=kwargs["message_id"],
        screening_result_id=kwargs["screening_result_id"],
    )
    assert reordered == first


def test_canonical_payload_normalises_naive_and_aware_datetimes():
    naive = dt.datetime(2026, 6, 1, 12, 0, 0)
    aware_utc = dt.datetime(2026, 6, 1, 12, 0, 0, tzinfo=dt.UTC)

    shared = dict(
        screening_result_id=1,
        message_id=2,
        violation=False,
        rule=None,
        quoted_phrase=None,
        explanation="ok",
        suggested_rewrite=None,
    )

    naive_payload = canonical_payload(created_at=naive, **shared)
    aware_payload = canonical_payload(created_at=aware_utc, **shared)

    # A naive datetime (e.g. round-tripped through SQLite, which drops tzinfo)
    # must hash identically to the equivalent explicit-UTC datetime.
    assert naive_payload == aware_payload
