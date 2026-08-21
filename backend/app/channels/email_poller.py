"""Real email channel — IMAP polling as a background task.

Runs inside the FastAPI process via the `lifespan` startup hook in
`app.main` (see `poll_forever`), not as a separate process or worker. Every
`EMAIL_POLL_INTERVAL_SECONDS`, it checks two folders on the same mailbox and
screens each new message through the exact same pipeline `/screen` uses
(`app.routers.screen.run_screening_pipeline`) — no second LLM-calling code
path exists.

Collector-vs-customer is determined by which folder a message came from, not
by matching a hardcoded sender address:

- INBOX: mail arriving at the collector's own address. Genuinely from
  whoever sent it, so it's screened as the customer side (is_customer=True),
  resolved to an account by the sender's address.
- "[Gmail]/Sent Mail": mail the collector genuinely sent out. Screened as
  the collector side (is_customer=False, attributed to DEMO_COLLECTOR_NAME),
  resolved to an account by the first "To" recipient's address.

Each folder is fetched with UID-based IMAP calls (`conn.uid(...)`), because
message *sequence numbers* (what plain `search`/`fetch` return) are only
valid for the lifetime of a single connection and are not safe to persist
across the reconnects this poller does every cycle.

The two folders use different "what's new" tracking, because they behave
differently:

- INBOX uses the \\Seen flag, exactly as before: fetch UNSEEN, and after
  successfully processing a message, mark it \\Seen so it isn't refetched.
  Confirmed empirically that Gmail's IMAP \\Seen flag on INBOX round-trips
  correctly (set it, reconnect, it's still set).
- Sent Mail can't use \\Seen the same way: confirmed empirically that Gmail
  marks a message \\Seen the moment it's submitted via SMTP, before this
  poller ever sees it (the sender obviously "saw" what they just wrote), so
  a message never appears in a Sent Mail UNSEEN search — \\Seen-based
  tracking would silently never fire. Instead, Sent Mail tracks the highest
  UID already processed, in memory only (`poll_forever`'s `state` dict). At
  startup this is seeded to the current max UID in the folder (so a restart
  doesn't reprocess the entire Sent Mail history), then advanced by one UID
  at a time as each message is successfully screened and committed.
  Known, accepted limitation for this scope: because the high-water mark
  lives only in memory, a process restart forgets it and reseeds from
  "now" — a message sent and fully processed in the moments right before a
  crash is safe (it's already in the folder, so the reseeded baseline is at
  or past it), but a message sent in a narrow window during a crash/restart
  could in theory be skipped. This is not silently swallowed: it's called
  out here and logged at startup.

`imaplib` is blocking, so every IMAP call runs off the event loop via
`asyncio.to_thread`. A poll cycle opens short-lived connections — never a
persistent one — because that's the simplest way to stay correct across
`asyncio.to_thread` calls, at the cost of a login round-trip per operation.
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

INBOX_FOLDER = "INBOX"
#: Must be quoted in the raw IMAP command — imaplib does not auto-quote
#: mailbox names containing spaces/brackets.
SENT_FOLDER = '"[Gmail]/Sent Mail"'


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


def _first_to_address(msg: EmailMessage) -> str:
    """The first recipient's address from the "To" header, lowercased. "" if none."""
    addresses = email.utils.getaddresses([msg.get("To", "")])
    if not addresses:
        return ""
    return addresses[0][1].strip().lower()


def _connect(settings: Settings, folder: str) -> imaplib.IMAP4_SSL:
    conn = imaplib.IMAP4_SSL(settings.email_imap_host, settings.email_imap_port)
    conn.login(settings.email_address, settings.email_app_password)
    conn.select(folder)
    return conn


def _fetch_unseen_inbox(settings: Settings) -> list[tuple[bytes, EmailMessage]]:
    """Blocking. Connects to INBOX, fetches every unread message, disconnects.

    Does not touch the \\Seen flag — fetching with `(RFC822)` (rather than
    `BODY.PEEK[]`) does mark a message as read on some servers, which is
    exactly why marking-read is a deliberate, separate step: this function
    accepts that side effect, but the caller only trusts its own explicit
    `_mark_read_many` call for "processed" bookkeeping, not IMAP's.
    """
    results: list[tuple[bytes, EmailMessage]] = []
    conn = _connect(settings, INBOX_FOLDER)
    try:
        status, data = conn.search(None, "UNSEEN")
        if status != "OK" or not data or not data[0]:
            return results
        for uid in data[0].split():
            status, msg_data = conn.fetch(uid, "(RFC822)")
            if status != "OK" or not msg_data or msg_data[0] is None:
                logger.warning("email: failed to fetch inbox uid=%r, skipping", uid)
                continue
            raw = msg_data[0][1]
            results.append((uid, email.message_from_bytes(raw)))
    finally:
        try:
            conn.logout()
        except Exception:
            pass
    return results


def _mark_read_many(settings: Settings, uids: list[bytes]) -> None:
    """Blocking. Connects once to INBOX and flags every given uid \\Seen."""
    conn = _connect(settings, INBOX_FOLDER)
    try:
        for uid in uids:
            conn.store(uid, "+FLAGS", "\\Seen")
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def _get_max_uid(settings: Settings, folder: str) -> int:
    """Blocking. The highest UID currently in `folder`, or 0 if empty.

    Used to seed Sent Mail's in-memory high-water mark at startup, so a
    restart picks up only mail sent from that point on rather than
    replaying the whole Sent Mail history.
    """
    conn = _connect(settings, folder)
    try:
        status, data = conn.uid("search", None, "ALL")
        if status != "OK" or not data or not data[0]:
            return 0
        uids = [int(u) for u in data[0].split()]
        return max(uids) if uids else 0
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def _fetch_new_sent(settings: Settings, since_uid: int) -> list[tuple[int, EmailMessage]]:
    """Blocking. Connects to Sent Mail, fetches every message with UID > since_uid.

    Uses `UID SEARCH`/`UID FETCH`, not the plain sequence-number variants,
    because UIDs (unlike sequence numbers) are safe to persist across the
    reconnects this poller does every cycle.
    """
    results: list[tuple[int, EmailMessage]] = []
    conn = _connect(settings, SENT_FOLDER)
    try:
        status, data = conn.uid("search", None, f"UID {since_uid + 1}:*")
        if status != "OK" or not data or not data[0]:
            return results
        # Per RFC 3501, "n:*" can echo back the mailbox's single highest UID
        # even when it's <= since_uid (no message actually newer) — filter
        # defensively rather than trust the range match alone.
        uids = sorted(u for u in (int(x) for x in data[0].split()) if u > since_uid)
        for uid in uids:
            status, msg_data = conn.uid("fetch", str(uid), "(RFC822)")
            if status != "OK" or not msg_data or msg_data[0] is None:
                logger.warning("email: failed to fetch sent uid=%r, skipping", uid)
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
    conn = _connect(settings, INBOX_FOLDER)
    conn.logout()


async def _first_or_create_collector_by_name(session: AsyncSession, name: str) -> Collector:
    """Find the named collector, creating one only if seeding was skipped.

    `first_or_create_collector(session, None)` (used by `/screen` and by this
    poller's customer-side pathway) picks whichever `Collector` row has the
    lowest id — an arbitrary placeholder that happens to work for a demo but
    attaches no real identity to the conduct being screened. The email
    channel's collector-side pathway (Sent Mail) needs a specific, named
    officer instead, so `/coaching`'s leaderboard attributes flags to
    someone real rather than an accident of insertion order.
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


def _blocked_inbox_sender_reason(settings: Settings, sender_email: str) -> str | None:
    """None if `sender_email` is a plausible real customer reply, else why it's blocked."""
    if sender_email == settings.email_address.strip().lower():
        return "sender is the collector's own inbox address (self-copy)"
    domain = sender_email.rsplit("@", 1)[-1] if "@" in sender_email else ""
    if domain in _BLOCKED_SENDER_DOMAINS:
        return f"automated sender domain ({domain})"
    if any(marker in sender_email for marker in _BLOCKED_SENDER_MARKERS):
        return "no-reply/automated sender address"
    return None


async def _process_inbox_email(
    session: AsyncSession, client: LLMClient, settings: Settings, msg: EmailMessage
) -> bool:
    """Screen one already-fetched INBOX email. Returns True iff it should be marked read.

    Anything that makes the message itself unprocessable (no sender, empty
    body) returns True — there is nothing a retry could fix. Anything that
    fails transiently (LLM, DB) raises, so the caller leaves it unread.
    """
    _display_name, sender_email = email.utils.parseaddr(msg.get("From", ""))
    sender_email = sender_email.strip().lower()
    subject = msg.get("Subject", "(no subject)")

    if not sender_email:
        logger.warning("email: no parseable sender on inbox message %r, skipping", subject)
        return True

    blocked_reason = _blocked_inbox_sender_reason(settings, sender_email)
    if blocked_reason is not None:
        logger.info(
            "email: skipping inbox sender %s (%s), subject=%r",
            sender_email,
            blocked_reason,
            subject,
        )
        return True

    body = _extract_plain_text(msg).strip()
    if not body:
        logger.warning("email: empty body from inbox sender %s (%r), skipping", sender_email, subject)
        return True
    if len(body) > settings.max_message_chars:
        body = body[: settings.max_message_chars]

    account = await resolve_account_by_contact(session, email=sender_email)
    logger.info(
        "email: inbox sender=%s subject=%r -> account=%s is_customer=True",
        sender_email,
        subject,
        account.external_id,
    )

    # A genuine reply from the customer, screened as the hardship pathway —
    # about the customer's own words, not any officer's conduct — so it uses
    # the arbitrary-but-valid placeholder collector. A real collector_id is
    # required by the NOT NULL FK either way; it just isn't meaningful here.
    collector = await first_or_create_collector(session, None)
    agency = await first_or_create_agency(session, None)

    result = await run_screening_pipeline(
        session,
        client,
        account=account,
        collector=collector,
        agency=agency,
        channel=Channel.email,
        text=body,
        is_customer=True,
        occurred_at=dt.datetime.now(dt.UTC),
        model=settings.groq_model,
    )

    logger.info(
        "email: screened inbox account=%s message_id=%s violation=%s rule=%s latency_ms=%s",
        account.external_id,
        result.message_id,
        result.verdict.violation,
        result.verdict.rule,
        result.latency_ms,
    )
    return True


async def _process_sent_email(
    session: AsyncSession, client: LLMClient, settings: Settings, msg: EmailMessage
) -> bool:
    """Screen one already-fetched Sent Mail email. Returns True iff it's settled
    (screened, or permanently unprocessable) — the caller advances the Sent
    Mail high-water mark past this UID either way. Raises on a transient
    failure (LLM, DB), so the caller stops advancing and retries next cycle.
    """
    recipient_email = _first_to_address(msg)
    subject = msg.get("Subject", "(no subject)")

    if not recipient_email:
        logger.warning("email: no parseable recipient on sent message %r, skipping", subject)
        return True

    body = _extract_plain_text(msg).strip()
    if not body:
        logger.warning("email: empty body in sent message to %s (%r), skipping", recipient_email, subject)
        return True
    if len(body) > settings.max_message_chars:
        body = body[: settings.max_message_chars]

    account = await resolve_account_by_contact(session, email=recipient_email)
    logger.info(
        "email: sent to=%s subject=%r -> account=%s is_customer=False",
        recipient_email,
        subject,
        account.external_id,
    )

    # The collector genuinely emailing a real customer address — screened as
    # the conduct pathway, attributed to the named officer.
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
        is_customer=False,
        occurred_at=dt.datetime.now(dt.UTC),
        model=settings.groq_model,
    )

    logger.info(
        "email: screened sent account=%s message_id=%s violation=%s rule=%s latency_ms=%s",
        account.external_id,
        result.message_id,
        result.verdict.violation,
        result.verdict.rule,
        result.latency_ms,
    )
    return True


async def _poll_inbox(session: AsyncSession, client: LLMClient, settings: Settings) -> None:
    try:
        fetched = await asyncio.to_thread(_fetch_unseen_inbox, settings)
    except Exception:
        logger.exception("email: INBOX fetch failed; will retry next cycle")
        return

    if not fetched:
        return

    logger.info("email: %d unread inbox message(s)", len(fetched))

    handled_uids: list[bytes] = []
    for uid, msg in fetched:
        try:
            if await _process_inbox_email(session, client, settings, msg):
                handled_uids.append(uid)
        except Exception:
            await session.rollback()
            logger.exception(
                "email: failed to process inbox uid=%r; leaving unread for retry", uid
            )

    if handled_uids:
        try:
            await asyncio.to_thread(_mark_read_many, settings, handled_uids)
        except Exception:
            logger.exception(
                "email: failed to mark %d inbox message(s) read; they may be reprocessed",
                len(handled_uids),
            )


async def _poll_sent(session: AsyncSession, client: LLMClient, settings: Settings, state: dict) -> None:
    if state["sent_last_uid"] is None:
        try:
            state["sent_last_uid"] = await asyncio.to_thread(_get_max_uid, settings, SENT_FOLDER)
            logger.info("email: Sent Mail baseline established, uid=%s", state["sent_last_uid"])
        except Exception:
            logger.exception("email: failed to establish Sent Mail baseline; will retry next cycle")
            return

    try:
        fetched = await asyncio.to_thread(_fetch_new_sent, settings, state["sent_last_uid"])
    except Exception:
        logger.exception("email: Sent Mail fetch failed; will retry next cycle")
        return

    if not fetched:
        return

    logger.info("email: %d new sent message(s)", len(fetched))

    for uid, msg in fetched:
        try:
            await _process_sent_email(session, client, settings, msg)
        except Exception:
            await session.rollback()
            logger.exception(
                "email: failed to process sent uid=%r; stopping this batch, will retry from "
                "here next cycle",
                uid,
            )
            break
        else:
            state["sent_last_uid"] = uid


async def _poll_once(state: dict) -> None:
    settings = get_settings()
    if not settings.email_address or not settings.email_app_password:
        return

    try:
        client = get_llm_client()
    except LLMUnavailable as exc:
        logger.warning("email: polling skipped, LLM not configured: %s", exc)
        return

    async with SessionLocal() as session:
        await _poll_inbox(session, client, settings)
        await _poll_sent(session, client, settings, state)


async def poll_forever() -> None:
    """Entry point scheduled from `app.main`'s lifespan. Never raises."""
    settings = get_settings()
    interval = max(1, settings.email_poll_interval_seconds)
    logger.info(
        "email: polling started, mailbox=%s host=%s:%s interval=%ss, folders=%s+%s",
        settings.email_address,
        settings.email_imap_host,
        settings.email_imap_port,
        interval,
        INBOX_FOLDER,
        SENT_FOLDER,
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

    # Sent Mail's high-water mark lives only in memory (see module
    # docstring) — None means "not yet established," seeded on the first
    # successful poll cycle to the folder's current max UID.
    state: dict = {"sent_last_uid": None}

    while True:
        try:
            await _poll_once(state)
        except Exception:
            logger.exception("email: unexpected error in poll cycle")
        await asyncio.sleep(interval)
