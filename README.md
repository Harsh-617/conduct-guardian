# Conduct Guardian

**Conduct-compliance screening for Malaysian debt collection, built against the Consumer Credit Act 2025 (Act 873).**

🔗 **Live app:** https://conduct-guardian-mu.vercel.app
🔧 **API:** https://conduct-guardian-api.onrender.com ([docs](https://conduct-guardian-api.onrender.com/docs) · [health](https://conduct-guardian-api.onrender.com/health))

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
                              Groq · Llama 3.3 70B
                                        │
                                Postgres (Neon, Singapore)
                         messages · screening_results
                         evidence_ledger (hash-chained)
```

**One real pipeline.** `POST /screen` is the only write path: message → LLM screening → stored with a chained ledger entry. The seed script drives that *same public endpoint over HTTP* rather than calling the code directly, so every verdict in the database is a genuine model output. Every dashboard number is a SQL aggregate over that one dataset.

## Measured results

Reproducible from scripts in this repo.

| Metric | Result |
|---|---|
| Agreement with human labels | **96.6%** (llama-3.3-70b, 59 messages) |
| Golden-set precision / recall / F1 | **91.7% / 100% / 95.7%** (20 curated cases) |
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
- **Groq's free tier caps llama-3.3-70b at ~100k tokens/day**, roughly 70 screenings. Bulk seeding uses llama-3.1-8b-instant, which is materially weaker (85.5% vs 96.6% agreement). Every verdict records which model produced it.

## Credits

UI prototype by [@Harsh-617](https://github.com/Harsh-617). Backend, integration and deployment built on top of it.

Licensed for hackathon submission use.
