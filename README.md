# Conduct Guardian

**Conduct-compliance screening for Malaysian debt collection, built against the Consumer Credit Act 2025 (Act 873).**

🔗 **Live app:** https://conduct-guardian.vercel.app
🔧 **API:** https://conduct-guardian-api-ue84.onrender.com ([docs](https://conduct-guardian-api-ue84.onrender.com/docs) · [health](https://conduct-guardian-api-ue84.onrender.com/health))

> **All data is synthetic.** No real borrower, collector, or agency data is used anywhere, ever.
>
> The API sleeps when idle (free tier). The first request can take 30–50 seconds — the UI shows a "waking up" state rather than an error.

---

## The problem

Act 873 came into force **1 March 2026**. Since **1 June 2026**, collection agencies must register with the Consumer Credit Commission and *prove* fair conduct. Non-compliance carries fines up to **RM5 million and/or 5 years**, plus a mandatory compliance audit under ss. 49 and 66.

Conduct happens across WhatsApp, SMS, phone and email. No agency can see across all of it — so none of them can prove anything.

## What it does

Screens every collector→customer message against a conduct rule pack, flags violations with the exact offending phrase and a compliant rewrite, merges all channels into one per-account timeline to catch cross-channel harassment, writes every verdict to a tamper-evident hash-chained evidence ledger, turns repeat violations into targeted coaching, and routes borrowers showing genuine hardship to human review instead of continued escalation.

## Architecture

```
Next.js (Vercel)  ──HTTPS/JSON──►  FastAPI (Render)
   7 screens                            │
                          Groq · openai/gpt-oss-20b
                                        │
                                Postgres (Neon, Singapore)
                         messages · screening_results
                         evidence_ledger (hash-chained)
```

**One real pipeline.** `POST /screen` is the only write path: message → LLM screening → stored with a chained ledger entry. The seed script drives that *same public endpoint over HTTP* rather than calling the code directly, so every verdict in the database is a genuine model output. Every dashboard number is a SQL aggregate over that one dataset.

**Evidence ledger.** Every screening verdict gets a chained hash entry (`evidence_ledger`) — each row's hash covers its own payload plus the previous row's hash, so any edit to historical data breaks every hash after it. `POST /ledger/verify` rehashes every stored row from its payload and reports the first row where the recomputed hash diverges from what's stored.

**Real email channel.** Alongside synthetic seed data, `app/channels/email_poller.py` runs an IMAP poller as a background task inside the FastAPI process, polling a real mailbox on an interval. It tells collector from customer by *which folder* a message came from (`INBOX` = customer-side, `[Gmail]/Sent Mail` = collector-side) rather than matching a hardcoded sender address, then screens each new message through the exact same `/screen` pipeline — no second LLM-calling code path.

## Measured results

Reproducible from scripts in this repo.

**⚠️** The model-specific rows below predate Groq deprecating
`llama-3.3-70b-versatile` / `llama-3.1-8b-instant`; the app now runs on
`openai/gpt-oss-120b` / `openai/gpt-oss-20b` (see `docs/DEPLOY.md`) and these
figures have not been re-measured against them.

| Metric | Result |
|---|---|
| Agreement with human labels | **96.6%** (llama-3.3-70b, deprecated, 59 messages) |
| Golden-set precision / recall / F1 | **91.7% / 100% / 95.7%** (llama-3.1-8b, deprecated, 20 curated cases) |
| **False negatives** | **0** — no real violation missed |
| Prompt-injection battery | **7 / 7 held** |
| Invalid rule IDs returned | **0** |
| Live screening latency | **680 ms** (deployed) |
| Evidence ledger | **valid**, 0 mismatches |
| Automated tests | **32 passing** |

## Where the rules come from

The Commission's **Conduct Standards v1.0 (5 June 2026)** exists but is classified **Restricted (Terhad)** and is not publicly retrievable. We did not use it.

The 8-rule pack derives from **Act 873 s.85(1)(g)** and **Bank Negara Malaysia's published Fair Debt Collection Practices** guidance. Every rule cites its source — see [`docs/CONDUCT-RULES.md`](docs/CONDUCT-RULES.md).

The pack is data, not prompt text. A registered agency swaps it for the Restricted standards; the engine is unchanged.

**The contact-frequency rule uses BNM's published maximum of 3 contacts per week**, computed deterministically in SQL rather than judged by the model. A separate same-hour burst check exists but is labelled everywhere as an internal heuristic, never as a regulatory limit.

## Tech stack

- **Frontend:** Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS 4, Recharts — deployed on Vercel.
- **Backend:** FastAPI, SQLAlchemy 2 (async) + Alembic migrations, Pydantic v2 — deployed on Render (single worker).
- **Database:** Postgres (Neon, Singapore region); SQLite is used as the local/test fallback with no `DATABASE_URL` set.
- **LLM:** Groq — `openai/gpt-oss-20b` for live screening, `openai/gpt-oss-120b` for bulk seeding.
- **Email channel:** IMAP polling (`imaplib`, stdlib) against a real mailbox.
- **Tests:** pytest + pytest-asyncio, in-memory SQLite, fake LLM client — no network or real API key required.

## API

| Endpoint | Method | Does |
|---|---|---|
| `/screen` | POST | Screens a message, stores it, chains a ledger entry, returns the verdict |
| `/dashboard/stats` | GET | Stat cards + 14-day chart, computed in SQL |
| `/timeline/{account_id}` | GET | All channels for one account, plus pattern flags |
| `/ledger` | GET | Paginated ledger (`?violations_only=true` for flags) |
| `/ledger/verify` | POST | Rehashes every entry from stored payloads, per-row pass/fail |
| `/coaching` | GET | Collectors ranked by flags, LLM pattern summary (cached) |
| `/hardship` | GET | Customer messages with detected hardship signals |
| `/agencies` | GET | Agencies ranked by computed compliance score |
| `/health` | GET | Liveness + honest configuration state |

## Local development

See **[`START-LOCAL.md`](START-LOCAL.md)** for the full walkthrough. Short version:

```bash
# Terminal 1 — backend
cd backend
python -m venv .venv && ./.venv/Scripts/python.exe -m pip install -r requirements.txt
cp .env.example .env        # fill in GROQ_API_KEY and DATABASE_URL
./.venv/Scripts/python.exe run_local.py

# Terminal 2 — frontend
npm install
npm run dev
```

Tests need no API key and no database — in-memory SQLite with an injected fake LLM:

```bash
cd backend && ./.venv/Scripts/python.exe -m pytest -q
```

## Documentation

| Doc | What's in it |
|---|---|
| [`docs/AI-HANDOFF.md`](docs/AI-HANDOFF.md) | Build map, decisions, status — read first |
| [`docs/CONDUCT-RULES.md`](docs/CONDUCT-RULES.md) | The 8 rules and their legal sources |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | Deployment runbook + the Groq token budget |
| [`docs/DEMO-SCRIPT.md`](docs/DEMO-SCRIPT.md) | Demo beats, likely questions, failure recovery |
| [`docs/JUDGE-ONEPAGER.md`](docs/JUDGE-ONEPAGER.md) | One-page summary (+ PDF) |
| [`docs/GIT-GUIDE.md`](docs/GIT-GUIDE.md) | Plain-language git workflow |
| [`START-LOCAL.md`](START-LOCAL.md) | Running both services locally |

## Honest limitations

Stated up front rather than discovered under questioning.

- **The hash chain proves internal consistency, not third-party non-repudiation.** Anyone with write access to the whole table could recompute it end to end. Production anchors the head hash where the agency cannot rewrite it — notarisation, a signed periodic head, or WORM storage. Deployment change, not a redesign.
- **The rate limiter is in-process** — it resets on restart and does not coordinate across replicas. The service runs a single worker deliberately, because the limiter and the coaching cache both live in memory.
- **Call transcripts are typed text "as if transcribed".** No audio ingestion.
- **No production auth, no multi-tenancy.** Both explicitly out of scope for this phase.
- **The real email channel has one hardcoded collector identity.** Folder-based detection (`INBOX` vs `Sent Mail`) tells collector from customer correctly, but every collector-side message is attributed to a single named collector rather than resolved per-sender — fine for a one-collector demo mailbox, not for a multi-collector agency.
- **The conduct rule pack is built from Act 873 and BNM's published guidance, not the Commission's actual Restricted (Terhad) Conduct Standards** — those aren't publicly retrievable, so the rules are a good-faith derivation pending real regulator text, not a certified implementation of it.
- **Groq's free tier caps both current models at 8,000 tokens/minute** (see `docs/DEPLOY.md`). Live screening runs on `openai/gpt-oss-20b`; bulk seeding uses `openai/gpt-oss-120b` — swapped from the original assignment once golden-set data showed `gpt-oss-20b` is both more accurate and faster on this task. See `docs/JUDGE-ONEPAGER.md` for current numbers. Every verdict records which model produced it.

## Credits

UI prototype by [@Harsh-617](https://github.com/Harsh-617). Backend, integration and deployment built on top of it.

Licensed for hackathon submission use.
