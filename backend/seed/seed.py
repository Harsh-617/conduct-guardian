"""Runnable seed script — drives the demo database through the real /screen endpoint.

Why HTTP and not calling `screen_message()` directly: the PRD's whole
credibility argument (docs/Conduct_Guardian_PRD_Phase2.md §8) is that seeded
verdicts come from the same code path a live demo uses. Nothing in the seed
data is a human pretending to be the AI's output.

Run from `backend/`, with the API already running:

    python -m seed.seed --dry-run
    python -m seed.seed --days 14
    python -m seed.seed --days 14 --limit 20

Requires a live app on API_BASE_URL (default http://127.0.0.1:8000) with a
reachable database and GROQ_API_KEY configured — this script does not start
the app or a database itself.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import os
import sys
from dataclasses import dataclass, field

if sys.stdout.encoding is not None and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import httpx
from sqlalchemy import select

from app.config import get_settings
from app.platform_compat import asyncio_run
from app.db import Base, SessionLocal, engine
from app.models import Account, Agency, Collector
from seed.sample_data import ACCOUNTS, AGENCIES, COLLECTORS, PlannedMessage, build_message_plan

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
# 2, not 4: the screening system prompt carries the full rule pack plus the
# JSON schema, so each call is token-heavy relative to Groq's free-tier cap
# (8,000 tokens/minute on openai/gpt-oss-120b, measured live — see
# docs/DEPLOY.md). Higher concurrency trips it and messages start failing.
MAX_CONCURRENCY = 2
MAX_RETRIES = 4
BASE_BACKOFF_SECONDS = 2.0
# Groq's rate-limit window is a minute, so exponential backoff starting at 2s
# gives up long before the window clears. Throttling responses get a flat wait
# past the window instead.
RATE_LIMIT_BACKOFF_SECONDS = 65.0


async def ensure_schema() -> None:
    """Create any missing tables. Safe to run repeatedly — CREATE TABLE IF NOT EXISTS."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def reset_data() -> None:
    """Delete all demo data so a re-seed starts from a clean chain.

    The evidence ledger is append-only by design, so there is no supported way
    to "fix" a chain in place — and recomputing one would defeat the point of
    having it. When a seed run half-fails, the honest move on synthetic data is
    to wipe and rebuild. Never point this at anything real.
    """
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    print("Reset: all demo data deleted.")


async def upsert_reference_data() -> tuple[dict[str, int], dict[str, int]]:
    """Idempotently insert agencies/collectors/accounts (skip rows that already exist).

    Returns name -> id maps for agencies and collectors, needed to translate
    the plan's human-readable names into the IDs `/screen` expects. Accounts
    aren't returned here — `/screen` resolves them by external_id itself.
    """
    async with SessionLocal() as session:
        agency_ids: dict[str, int] = {}
        for row in AGENCIES:
            found = await session.execute(select(Agency).where(Agency.name == row["name"]))
            agency = found.scalars().first()
            if agency is None:
                agency = Agency(name=row["name"])
                session.add(agency)
                await session.flush()
            agency_ids[row["name"]] = agency.id

        collector_ids: dict[str, int] = {}
        for row in COLLECTORS:
            found = await session.execute(select(Collector).where(Collector.name == row["name"]))
            collector = found.scalars().first()
            if collector is None:
                collector = Collector(name=row["name"], role=row["role"])
                session.add(collector)
                await session.flush()
            collector_ids[row["name"]] = collector.id

        for row in ACCOUNTS:
            found = await session.execute(
                select(Account).where(Account.external_id == row["external_id"])
            )
            if found.scalars().first() is None:
                session.add(Account(external_id=row["external_id"]))

        await session.commit()

    return agency_ids, collector_ids


@dataclass
class SeedOutcome:
    succeeded: int = 0
    failed: int = 0
    failures: list[str] = field(default_factory=list)
    #: (expected_rule, actual_rule) for every collector message that screened
    #: successfully. Scored at the end into an agreement rate — real model
    #: verdicts against human labels, over the whole corpus.
    labelled: list[tuple[str | None, str | None]] = field(default_factory=list)

    @property
    def completed(self) -> int:
        return self.succeeded + self.failed

    def agreement(self) -> tuple[int, int, int, int]:
        """Return (exact_rule_matches, binary_matches, scored, disagreements).

        `binary` is the looser and more honest headline: did the model agree
        on WHETHER this was a violation, regardless of which rule it picked.
        Rule-level disagreement between two defensible labels (is a given
        message R2_THREATS or R3_FALSE_LEGAL_CLAIM?) is not really an error,
        so reporting only exact match would understate accuracy.
        """
        exact = binary = 0
        for expected, actual in self.labelled:
            if expected == actual:
                exact += 1
            if (expected is None) == (actual is None):
                binary += 1
        scored = len(self.labelled)
        return exact, binary, scored, scored - binary


def _print_plan(plan: list[PlannedMessage]) -> None:
    print(f"Plan: {len(plan)} messages (dry run — sending nothing)\n")
    for i, msg in enumerate(plan, start=1):
        speaker = "CUST" if msg["is_customer"] else "COLL"
        print(
            f"{i:>3}. [{msg['occurred_at'].isoformat()}] "
            f"acct={msg['account_external_id']:<6} {msg['channel']:<8} {speaker} "
            f"{msg['collector_name']:<18} {msg['text'][:70]}"
        )


async def _send_one(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    payload: dict[str, object],
    headers: dict[str, str],
    total: int,
    outcome: SeedOutcome,
    expected_rule: str | None = None,
    score_it: bool = False,
) -> None:
    async with sem:
        delay = BASE_BACKOFF_SECONDS
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await client.post("/screen", json=payload, headers=headers, timeout=30.0)
                resp.raise_for_status()
                verdict = resp.json().get("verdict", {})
                outcome.succeeded += 1
                actual_rule = verdict.get("rule")
                if score_it:
                    outcome.labelled.append((expected_rule, actual_rule))
                agree = "" if not score_it else (
                    "  ✓" if (expected_rule is None) == (actual_rule is None)
                    else f"  ✗ expected={expected_rule}"
                )
                print(
                    f"[{outcome.completed}/{total}] ok    "
                    f"acct={payload['account_id']} rule={actual_rule}{agree}"
                )
                return
            except httpx.HTTPError as exc:
                if attempt == MAX_RETRIES:
                    outcome.failed += 1
                    outcome.failures.append(f"acct={payload['account_id']}: {exc}")
                    print(
                        f"[{outcome.completed}/{total}] FAILED "
                        f"acct={payload['account_id']} after {MAX_RETRIES} attempts — {exc}"
                    )
                    return
                # A 503 here is the app surfacing LLMUnavailable, which during
                # a bulk run is nearly always Groq throttling. Waiting past the
                # provider's one-minute window is the only retry that helps.
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status in (429, 503):
                    wait = RATE_LIMIT_BACKOFF_SECONDS
                    reason = "provider throttling — waiting out the rate-limit window"
                else:
                    wait = delay
                    delay *= 2
                    reason = str(exc)[:80]
                print(
                    f"      retry {attempt}/{MAX_RETRIES} in {wait:.0f}s "
                    f"acct={payload['account_id']} — {reason}"
                )
                await asyncio.sleep(wait)


async def run_seed(
    days: int,
    limit: int | None,
    dry_run: bool,
    reset: bool = False,
    use_bulk: bool = True,
) -> None:
    now = dt.datetime.now(dt.UTC)
    plan = build_message_plan(now=now, days=days)
    if limit is not None:
        plan = plan[:limit]

    if dry_run:
        _print_plan(plan)
        return

    settings = get_settings()
    base_url = os.environ.get("API_BASE_URL", DEFAULT_BASE_URL)

    await ensure_schema()
    if reset:
        await reset_data()
    agency_ids, collector_ids = await upsert_reference_data()

    model_label = settings.groq_model_bulk if use_bulk else settings.groq_model
    print(f"Seeding {len(plan)} messages via {base_url} using {model_label}\n")
    headers = {"X-Seed-Token": settings.seed_token}
    outcome = SeedOutcome()
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async with httpx.AsyncClient(base_url=base_url) as client:
        tasks = []
        for msg in plan:
            payload = {
                "text": msg["text"],
                "channel": msg["channel"],
                "account_id": msg["account_external_id"],
                "collector_id": collector_ids[msg["collector_name"]],
                "agency_id": agency_ids[msg["agency_name"]],
                "is_customer": msg["is_customer"],
                "occurred_at": msg["occurred_at"].isoformat(),
                "use_bulk_model": use_bulk,
            }
            tasks.append(
                _send_one(
                    client,
                    sem,
                    payload,
                    headers,
                    len(plan),
                    outcome,
                    expected_rule=msg["expected_rule"],
                    # Customer-side messages aren't screened for conduct, so
                    # there is no verdict to score them against.
                    score_it=not msg["is_customer"],
                )
            )
        await asyncio.gather(*tasks)

    print(
        f"\nDone: {outcome.succeeded} succeeded, {outcome.failed} failed "
        f"(of {len(plan)} planned)."
    )

    exact, binary, scored, disagreements = outcome.agreement()
    if scored:
        print(
            f"\nModel vs human labels over {scored} collector messages:\n"
            f"  violation / no-violation agreement: {binary}/{scored} "
            f"({100 * binary / scored:.1f}%)\n"
            f"  exact rule-ID match:                {exact}/{scored} "
            f"({100 * exact / scored:.1f}%)\n"
            f"  disagreements to eyeball:           {disagreements}"
        )
        print(
            "  (Rule-level disagreement between two defensible labels is not\n"
            "   necessarily an error — the binary rate is the honest headline.)"
        )

    if outcome.failures:
        print("Failures:")
        for line in outcome.failures:
            print(f"  - {line}")
        sys.exit(1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed Conduct Guardian by driving planned messages through the real /screen endpoint."
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the plan; send nothing.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete ALL existing demo data first, so the hash chain rebuilds clean.",
    )
    parser.add_argument("--days", type=int, default=14, help="Spread messages over the last N days.")
    parser.add_argument(
        "--limit", type=int, default=None, help="Only send the first N planned messages."
    )
    parser.add_argument(
        "--full-model",
        action="store_true",
        help=(
            "Seed with GROQ_MODEL (openai/gpt-oss-20b) instead of the bulk model. "
            "Groq's free tier caps it at 8,000 tokens PER MINUTE, so a seed run "
            "can starve the live demo of budget. Rarely what you want."
        ),
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    asyncio_run(
        run_seed(
            days=args.days,
            limit=args.limit,
            dry_run=args.dry_run,
            reset=args.reset,
            use_bulk=not args.full_model,
        )
    )


if __name__ == "__main__":
    main()
