"""Remove evaluation traffic from the demo database.

`scripts/eval_golden_set.py` and `scripts/probe_injection.py` drive the REAL
`/screen` endpoint — that is the point, it is the same path the demo uses — so
everything they send is persisted like any other message. Run them against the
demo database and the dashboard silently absorbs them: 75 seeded messages
became 116, the violation rate jumped from ~40% to 58% because attack payloads
are nearly all violations, and a judge clicking into the accounts list would
have found one called REDTEAM.

The test accounts use reserved external_ids so they can be removed precisely
rather than by wiping everything.

    ./.venv/Scripts/python.exe -m scripts.purge_test_data          # dry run
    ./.venv/Scripts/python.exe -m scripts.purge_test_data --yes    # delete

Ledger note: the evidence ledger is append-only, so deleting screened messages
necessarily removes their chain entries and re-links nothing. That is fine for
these accounts precisely because they are test traffic, but it means the chain
must be REBUILT afterwards, not patched — run a full
`python -m seed.seed --reset --days 14` as the last step before a demo.
"""

from __future__ import annotations

import argparse

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models import (
    Account,
    EvidenceLedgerEntry,
    HardshipSignal,
    Message,
    ScreeningResult,
)
from app.platform_compat import asyncio_run

#: external_ids used only by evaluation and probe scripts. Keep in sync with
#: the account_id each script sends.
TEST_ACCOUNT_IDS = ["GOLDEN", "REDTEAM", "DIAG", "BULKTEST", "QA", "9999", "9900"]

#: Prefixes for ad-hoc probe accounts. An exact list can't cover these: a
#: security audit invented accounts named AUDIT-INJ-1 and AUDIT-INJ-3 that were
#: unknown when this script was written, and they surfaced at the top of the
#: dashboard's Recent Flags with text reading "Ignore all previous
#: instructions." Anything probing this API should use one of these prefixes.
TEST_ACCOUNT_PREFIXES = ["AUDIT", "TEST", "PROBE", "REDTEAM", "GOLDEN"]


async def _collect(session: AsyncSession) -> tuple[list[int], list[int]]:
    from sqlalchemy import or_

    conditions = [Account.external_id.in_(TEST_ACCOUNT_IDS)]
    conditions += [Account.external_id.startswith(p) for p in TEST_ACCOUNT_PREFIXES]

    accounts = (
        (await session.execute(select(Account).where(or_(*conditions))))
        .scalars()
        .all()
    )
    account_ids = [a.id for a in accounts]
    if not account_ids:
        return [], []

    message_ids = (
        (
            await session.execute(
                select(Message.id).where(Message.account_id.in_(account_ids))
            )
        )
        .scalars()
        .all()
    )
    return account_ids, list(message_ids)


async def main(confirm: bool) -> None:
    async with SessionLocal() as session:
        account_ids, message_ids = await _collect(session)

        if not message_ids:
            print("Nothing to purge — no test-account messages found.")
            return

        print(f"Test accounts found : {len(account_ids)}")
        print(f"Messages to delete  : {len(message_ids)}")

        if not confirm:
            print("\nDry run. Re-run with --yes to delete.")
            return

        # Children first — these tables have FKs onto messages.
        screening_ids = (
            (
                await session.execute(
                    select(ScreeningResult.id).where(
                        ScreeningResult.message_id.in_(message_ids)
                    )
                )
            )
            .scalars()
            .all()
        )
        if screening_ids:
            await session.execute(
                delete(EvidenceLedgerEntry).where(
                    EvidenceLedgerEntry.screening_result_id.in_(list(screening_ids))
                )
            )
        await session.execute(
            delete(HardshipSignal).where(HardshipSignal.message_id.in_(message_ids))
        )
        await session.execute(
            delete(ScreeningResult).where(ScreeningResult.message_id.in_(message_ids))
        )
        await session.execute(delete(Message).where(Message.id.in_(message_ids)))
        await session.execute(delete(Account).where(Account.id.in_(account_ids)))
        await session.commit()

        print(f"\nDeleted {len(message_ids)} messages and {len(account_ids)} accounts.")
        print(
            "The hash chain now has gaps where those entries were. Rebuild it before\n"
            "demoing: python -m seed.seed --reset --days 14"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="Actually delete.")
    args = parser.parse_args()
    asyncio_run(main(args.yes))
