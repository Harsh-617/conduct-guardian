"""Real email channel — IMAP polling as a background task.

Runs inside the FastAPI process via the `lifespan` startup hook in
`app.main` (see `poll_forever`), not as a separate process or worker. Every
`EMAIL_POLL_INTERVAL_SECONDS`, it checks the inbox for unread mail, resolves
each sender to an account by their real contact info (never a manually-typed
tag — see `app.accounts.resolve_account_by_contact`), and screens the body
through the exact same pipeline `/screen` uses
(`app.routers.screen.run_screening_pipeline`) — no second LLM-calling code
path exists.

`imaplib` is blocking, so every IMAP call runs off the event loop via
`asyncio.to_thread`. A poll cycle opens two short-lived connections: one to
fetch unread mail, and — only after successfully screening a message — a
second to mark exactly the messages that were fully processed as read. A
message is left unread (and retried next cycle) if anything about processing
it fails, so a transient LLM or DB hiccup self-heals; a message that can
never be processed (no parseable sender, empty body) is marked read anyway,
since retrying it changes nothing.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import email
import email.utils
import imaplib
import logging
from email.message import Message as EmailMessage

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts import resolve_account_by_contact
from app.config import Settings, get_settings
from app.db import SessionLocal
from app.llm.client import LLMClient, LLMUnavailable, get_llm_client
from app.models import Channel, Collector
from app.routers.screen import (
    first_or_create_agency,
    first_or_create_collector,
    run_screening_pipeline,
)

logger = logging.getLogger("conduct_guardian.email")


def _extract_plain_text(msg: EmailMessage) -> str:
    """Best-effort plain-text body. Skips attachments; ignores HTML-only mail."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(charset, errors="replace")
        return ""
    if msg.get_content_type() == "text/plain":
        charset = msg.get_content_charset() or "utf-8"
        payload = msg.get_payload(decode=True)
        return payload.decode(charset, errors="replace") if payload else ""
    return ""


def _connect(settings: Settings) -> imaplib.IMAP4_SSL:
    conn = imaplib.IMAP4_SSL(settings.email_imap_host, settings.email_imap_port)
    conn.login(settings.email_address, settings.email_app_password)
    conn.select("INBOX")
    return conn


def _fetch_unseen(settings: Settings) -> list[tuple[bytes, EmailMessage]]:
    """Blocking. Connects, fetches every unread message, disconnects.

    Does not touch the \\Seen flag — fetching with `(RFC822)` (rather than
    `BODY.PEEK[]`) does mark a message as read on some servers, which is
    exactly why marking-read is a deliberate, separate step: this function
    accepts that side effect, but the caller only trusts its own explicit
    `_mark_read_many` call for "processed" bookkeeping, not IMAP's.
    """
    results: list[tuple[bytes, EmailMessage]] = []
    conn = _connect(settings)
    try:
        status, data = conn.search(None, "UNSEEN")
        if status != "OK" or not data or not data[0]:
            return results
        for uid in data[0].split():
            status, msg_data = conn.fetch(uid, "(RFC822)")
            if status != "OK" or not msg_data or msg_data[0] is None:
                logger.warning("email: failed to fetch uid=%r, skipping", uid)
                continue
            raw = msg_data[0][1]
            results.append((uid, email.message_from_bytes(raw)))
    finally:
        try:
            conn.logout()
        except Exception:
            pass
    return results


def _test_connection(settings: Settings) -> None:
    """Blocking. Connect, login, logout — no fetch. Raises on any failure.

    Run once at poller startup so a bad EMAIL_ADDRESS/EMAIL_APP_PASSWORD (the
    single most likely live-demo failure — Gmail rejects a regular password
    over IMAP and requires an App Password) is loud within the first second,
    not discovered by silence 15 seconds later on the first real poll cycle.
    """
    conn = _connect(settings)
    conn.logout()


def _mark_read_many(settings: Settings, uids: list[bytes]) -> None:
    """Blocking. Connects once and flags every given uid \\Seen."""
    conn = _connect(settings)
    try:
        for uid in uids:
            conn.store(uid, "+FLAGS", "\\Seen")
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def _classify_sender(settings: Settings, sender_email: str) -> bool:
    """Is this sender the demo customer? False (collector/other) otherwise."""
    if settings.demo_customer_email and sender_email == settings.demo_customer_email.strip().lower():
        return True
    return False


async def _first_or_create_collector_by_name(session: AsyncSession, name: str) -> Collector:
    """Find the named collector, creating one only if seeding was skipped.

    `first_or_create_collector(session, None)` (used by `/screen` and by this
    poller's hardship pathway) picks whichever `Collector` row has the lowest
    id — an arbitrary placeholder that happens to work for a demo but attaches
    no real identity to the conduct being screened. The email channel's
    collector-side pathway needs a specific, named officer instead, so
    `/coaching`'s leaderboard attributes flags to someone real rather than an
    accident of insertion order.
    """
    found = await session.execute(
        select(Collector).where(Collector.name == name).order_by(Collector.id).limit(1)
    )
    collector = found.scalars().first()
    if collector is None:
        collector = Collector(name=name, role="collector")
        session.add(collector)
        await session.flush()
    return collector


#: The inbox being polled also receives Google's own automated
#: account-security mail ("App password created", "2-Step Verification
#: turned on", "New passkey added", "Recovery email changed", ...) — these
#: are not a collector or customer speaking and must never become a
#: screened message or an auto-created account. Sender-based, not
#: subject-based: subject wording is Google's to change, the sending
#: domain/address pattern is not.
_BLOCKED_SENDER_DOMAINS = {"accounts.google.com"}
_BLOCKED_SENDER_MARKERS = ("noreply", "no-reply")


def _blocked_sender_reason(settings: Settings, sender_email: str) -> str | None:
    """None if `sender_email` is a plausible real demo participant, else why it's blocked.

    A configured DEMO_COLLECTOR_EMAIL/DEMO_CUSTOMER_EMAIL is always allowed
    even if it happens to also match a marker below — an explicit demo
    address is definitionally a real participant, deny-listing is only for
    everything else.
    """
    if sender_email in {
        (settings.demo_collector_email or "").strip().lower(),
        (settings.demo_customer_email or "").strip().lower(),
    } - {""}:
        return None

    domain = sender_email.rsplit("@", 1)[-1] if "@" in sender_email else ""
    if domain in _BLOCKED_SENDER_DOMAINS:
        return f"automated sender domain ({domain})"
    if any(marker in sender_email for marker in _BLOCKED_SENDER_MARKERS):
        return "no-reply/automated sender address"
    return None


async def _process_email(
    session: AsyncSession, client: LLMClient, settings: Settings, msg: EmailMessage
) -> bool:
    """Screen one already-fetched email. Returns True iff it should be marked read.

    Anything that makes the message itself unprocessable (no sender, empty
    body) returns True — there is nothing a retry could fix. Anything that
    fails transiently (LLM, DB) raises, so the caller leaves it unread.
    """
    _display_name, sender_email = email.utils.parseaddr(msg.get("From", ""))
    sender_email = sender_email.strip().lower()
    subject = msg.get("Subject", "(no subject)")

    if not sender_email:
        logger.warning("email: no parseable sender on message %r, skipping", subject)
        return True

    blocked_reason = _blocked_sender_reason(settings, sender_email)
    if blocked_reason is not None:
        logger.info(
            "email: skipping %s (%s), subject=%r — not a demo participant",
            sender_email,
            blocked_reason,
            subject,
        )
        return True

    body = _extract_plain_text(msg).strip()
    if not body:
        logger.warning("email: empty body from %s (%r), skipping", sender_email, subject)
        return True
    if len(body) > settings.max_message_chars:
        body = body[: settings.max_message_chars]

    is_customer = _classify_sender(settings, sender_email)

    account = await resolve_account_by_contact(session, email=sender_email)
    logger.info(
        "email: sender=%s subject=%r -> account=%s is_customer=%s",
        sender_email,
        subject,
        account.external_id,
        is_customer,
    )

    # Collector-side messages get attributed to a specific named officer, so
    # /coaching's per-collector counts mean something; the hardship pathway is
    # about the customer's own words, not any officer's conduct, so it keeps
    # the arbitrary-but-valid placeholder — a real collector_id is required by
    # the NOT NULL FK either way, it just isn't meaningful here.
    if is_customer:
        collector = await first_or_create_collector(session, None)
    else:
        collector = await _first_or_create_collector_by_name(session, settings.demo_collector_name)
    agency = await first_or_create_agency(session, None)

    result = await run_screening_pipeline(
        session,
        client,
        account=account,
        collector=collector,
        agency=agency,
        channel=Channel.email,
        text=body,
        is_customer=is_customer,
        occurred_at=dt.datetime.now(dt.UTC),
        model=settings.groq_model,
    )

    logger.info(
        "email: screened account=%s message_id=%s violation=%s rule=%s latency_ms=%s",
        account.external_id,
        result.message_id,
        result.verdict.violation,
        result.verdict.rule,
        result.latency_ms,
    )
    return True


async def _poll_once() -> None:
    settings = get_settings()
    if not settings.email_address or not settings.email_app_password:
        return

    try:
        client = get_llm_client()
    except LLMUnavailable as exc:
        logger.warning("email: polling skipped, LLM not configured: %s", exc)
        return

    try:
        fetched = await asyncio.to_thread(_fetch_unseen, settings)
    except Exception:
        logger.exception("email: IMAP fetch failed; will retry next cycle")
        return

    if not fetched:
        return

    logger.info("email: %d unread message(s)", len(fetched))

    handled_uids: list[bytes] = []
    async with SessionLocal() as session:
        for uid, msg in fetched:
            try:
                if await _process_email(session, client, settings, msg):
                    handled_uids.append(uid)
            except Exception:
                await session.rollback()
                logger.exception(
                    "email: failed to process uid=%r; leaving unread for retry", uid
                )

    if handled_uids:
        try:
            await asyncio.to_thread(_mark_read_many, settings, handled_uids)
        except Exception:
            logger.exception(
                "email: failed to mark %d message(s) read; they may be reprocessed",
                len(handled_uids),
            )


async def poll_forever() -> None:
    """Entry point scheduled from `app.main`'s lifespan. Never raises."""
    settings = get_settings()
    interval = max(1, settings.email_poll_interval_seconds)
    logger.info(
        "email: polling started, mailbox=%s host=%s:%s interval=%ss",
        settings.email_address,
        settings.email_imap_host,
        settings.email_imap_port,
        interval,
    )

    try:
        await asyncio.to_thread(_test_connection, settings)
    except Exception:
        logger.exception(
            "email: STARTUP IMAP LOGIN FAILED for %s @ %s:%s — check "
            "EMAIL_ADDRESS/EMAIL_APP_PASSWORD (Gmail requires an App "
            "Password, not the account's regular password). Polling will "
            "keep retrying every %ss.",
            settings.email_address,
            settings.email_imap_host,
            settings.email_imap_port,
            interval,
        )
    else:
        logger.info("email: IMAP login OK")

    while True:
        try:
            await _poll_once()
        except Exception:
            logger.exception("email: unexpected error in poll cycle")
        await asyncio.sleep(interval)
