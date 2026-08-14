# Conduct Guardian — Product Requirements Document (Phase 2: Real Build)

**Purpose of this document:** move from the UI mockup (Track 2 preliminary round) to a genuinely
working prototype for the final submission.

**Repo:** same repo as the UI mockup, on a new branch (`real-backend`) until tested, then merged
to `main`. See "Environment & Secrets" before starting.

---

## 1. Context

Malaysia's Consumer Credit Act 2025 (Act 873) came into force 1 March 2026. Since 1 June 2026,
debt collection agencies must register with the new Consumer Credit Commission and prove fair
conduct — non-compliance carries fines up to RM5 million and/or 5 years imprisonment, plus a
mandatory compliance audit under sections 49 and 66 of the Act. Agencies currently have no way
to review their own conduct across scattered channels (calls, WhatsApp, SMS, email).

**Conduct Guardian** screens every collector-customer interaction against conduct rules, flags
violations with the exact offending phrase and a suggested rewrite, merges every channel into
one per-account timeline to catch cross-channel harassment patterns, keeps a tamper-evident
evidence ledger for audits, turns repeated violations into targeted collector coaching, and
routes customers showing genuine hardship to human review instead of continued escalation.

**What already exists:** a fully built, polished UI — 7 screens (Dashboard, Live Screening,
Case Timeline, Evidence Ledger, Coaching, Hardship Queue, Agency Oversight), Next.js/Tailwind/
shadcn, deployed on Vercel. Every screen currently runs on hardcoded data. **This phase replaces
the hardcoded data with a real pipeline — the UI itself barely needs to change.**

---

## 2. Goal for This Phase

Turn the mockup into a system where:
- Typing an arbitrary message into Live Screening gets a real, live compliance judgment from an
  LLM — not one of 4 canned responses.
- Every number on every screen (dashboard stats, ledger entries, coaching flag counts, agency
  scores) is a real aggregate computed from real stored data — not a hardcoded array.
- The evidence ledger's "Verify Chain Integrity" button actually recomputes and checks hashes —
  not a scripted animation.

This is not a production SaaS build. It's a prototype that needs to survive a judge's technical
questions and a live, unscripted demo.

---

## 3. Scope: What Gets Built Real vs. What Stays Simulated

Priority tiers so trade-off calls are easy to make if needed. **P0 = must ship. P1 = should ship.
P2 = stretch, cut first if behind.**

| Feature | Tier | What "real" means here |
|---|---|---|
| Live Screening | **P0** | Real Groq API call, analyzes arbitrary typed input, returns structured verdict |
| Evidence Ledger + hash chain | **P0** | Real hash-chaining on write; "Verify" recomputes hashes live |
| Dashboard stats + chart | **P0** | Real SQL aggregates over stored messages, not hardcoded numbers |
| Case Timeline | **P0** | Real per-account query across channels, real pattern-detection rule |
| Coaching Leaderboard | **P1** | Real aggregate by collector; pattern description LLM-generated from real flagged messages |
| Hardship Queue | **P1** | Real second LLM pass detecting hardship signals in customer-side text |
| Agency Oversight | **P1** | Real aggregate scores, computed from seeded-but-real screening results per agency |
| Role-based access gate | **P2** | Simple token-based gate, not full production RBAC |
| Real audio ingestion (Whisper) | **P2** | Call transcripts stay as typed text "as if transcribed" — low demo value for the effort |
| GSAP/Lenis scroll story | **P2** | Visual polish, not core functionality |

**Design decision:** rather than making each screen "real" independently, this builds **one real
pipeline** (message in → LLM screens it → stored with hash chain) and seeds it with a realistic
synthetic dataset. Every screen becomes a genuine read view over that one real dataset — less
total work, and a much stronger demo story, since nothing is independently faked per screen.

---

## 4. System Architecture

```
Seed script / Live input
        │
        ▼
FastAPI  /screen  ──►  Groq API (Llama 3.3 70B) ──►  structured verdict
        │
        ▼
Postgres: messages + screening_results + evidence_ledger (hash-chained)
        │
        ▼
FastAPI read endpoints (dashboard, timeline, ledger, coaching, hardship, agencies)
        │
        ▼
Next.js frontend (already built — now fetching real data instead of arrays)
```

Two deployable pieces: the existing **Next.js frontend** (Vercel) and a new **Python/FastAPI
backend** (separate host), talking over HTTPS/JSON. This matches the architecture already shown
in the pitch deck exactly — Python + FastAPI + Postgres + hash-chaining — no gap between what
was pitched and what's built.

---

## 5. Tech Stack

### Already built (do not change)
- **Next.js 15** (App Router, TypeScript, `src/` dir)
- **Tailwind CSS v4** + **shadcn/ui**
- **Framer Motion**, **lucide-react**, **recharts**
- Deployed on **Vercel**

### New for this phase

| Layer | Choice | Why |
|---|---|---|
| Backend | **Python + FastAPI** | Matches the architecture already in the pitch deck; async-friendly for LLM calls; clean, fast to write |
| Database | **Postgres via Neon** (neon.tech) | Serverless Postgres, free tier, no credit card needed |
| ORM | **SQLAlchemy 2.0** + **Alembic** for migrations | Standard, well-documented Python pairing with Postgres |
| Validation | **Pydantic** (built into FastAPI) | Request/response schemas, type safety |
| LLM | **Groq API — Llama 3.3 70B Versatile** for screening and coaching summaries | Free tier needs no credit card (14,400 requests/day, 30K tokens/minute — comfortably enough for prototyping and a live demo), and Groq's LPU hardware returns answers in well under a second, which matters for a live on-stage demo. Llama 3.1 8B Instant is available as a faster/cheaper fallback if needed for bulk seeding. |
| LLM client | **`groq` Python SDK** | Official client, OpenAI-compatible chat completions interface |
| Backend hosting | **Render** (or Railway as an alternative) | Free/hobby tier suited to a persistent FastAPI app with a database connection, simple GitHub-based deploy |
| Hash chaining | **Python `hashlib` (sha256)** | Standard library, no dependency needed |
| Auth (P2 only) | Simple bearer-token gate in FastAPI | Enough for a demo role split, not a production auth system |

### What NOT to introduce
No Docker/Kubernetes, no microservices split beyond the two pieces above, no separate message
queue. Keep this to two deployable services: the Next.js frontend and the FastAPI backend.

---

## 6. Data Model (plain terms — SQLAlchemy models)

```
Account
  id, external_id (e.g. "4471"), created_at

Collector
  id, name, role

Agency
  id, name

Message
  id, account_id (FK), collector_id (FK), agency_id (FK),
  channel (enum: whatsapp | sms | call | email),
  raw_text, occurred_at, created_at

ScreeningResult
  id, message_id (FK, unique),
  violation (bool), rule (string, nullable),
  quoted_phrase (string, nullable), explanation (string),
  suggested_rewrite (string, nullable),
  created_at

EvidenceLedgerEntry
  id, screening_result_id (FK, unique),
  entry_hash (string), prev_hash (string, nullable),
  created_at
  // append-only — never update or delete rows

HardshipSignal
  id, message_id (FK), signal_type (enum: job_loss | health_crisis |
  bereavement | financial_distress), quoted_text, detected_at
```

Coaching data and Agency scores are computed on read (SQL aggregates), not stored — simpler,
and always accurate to the underlying data.

---

## 7. API Endpoints (FastAPI, separate service from the Next.js frontend)

| Endpoint | Method | Does |
|---|---|---|
| `/screen` | POST | Takes `{text, channel, account_id, collector_id}`, calls Groq, stores Message + ScreeningResult + chains a new EvidenceLedgerEntry, returns the verdict. Powers Live Screening for real. |
| `/dashboard/stats` | GET | Stat card numbers + 14-day chart data, computed from stored messages/results |
| `/timeline/{account_id}` | GET | All messages for an account, all channels, chronological, plus a computed pattern flag (rule of thumb: ≥5 contacts within 60 minutes) |
| `/ledger` | GET | Paginated ledger entries |
| `/ledger/verify` | POST | **Recomputes every hash from stored data and compares to what's stored** — returns per-row pass/fail. This is the real "Verify Chain Integrity" logic. |
| `/coaching` | GET | Collectors ranked by flag count (real `GROUP BY`); pattern description generated by asking the LLM to summarize that collector's actual flagged messages |
| `/hardship` | GET | Messages with detected hardship signals |
| `/agencies` | GET | Agencies ranked by computed compliance score from their real screening results |

The Next.js frontend calls these via a configured base URL (see Environment & Secrets) instead
of using its own `/api` routes.

---

## 8. Seeding Strategy

No real proprietary data exists (and none should be used even if it did). A seed script should:

1. Create a handful of accounts, collectors, and agencies (reuse the same sample data already in
   the UI mockup for continuity — e.g. Account #4471, collector "Ravi," etc.)
2. Generate ~60–100 synthetic messages across channels — mix of clean, clearly violating (reuse
   the 4 original sample phrases), and borderline ones for realistic variety
3. **Run every seeded message through the real `/screen` endpoint** — so the database ends up
   full of genuine LLM verdicts, not hand-written fake ones

This is the design choice that makes the whole demo defensible: nothing in the seed data is a
human pretending to be the AI's output. It's all real, just generated in bulk ahead of time
instead of live on stage.

---

## 9. Non-Functional Requirements

- **Cost control:** Groq's free tier requires no credit card and covers prototyping and a live
  demo comfortably (14,400 requests/day is far more than this project needs). Still, cap input
  length server-side and keep responses reasonably short.
- **Abuse protection:** once deployed, `/screen` is a public endpoint. Add a simple rate limit
  (a handful of requests per minute per IP) so it can't be hammered before the actual pitch.
- **Error handling:** if the Groq API call fails or returns malformed JSON, the UI should show a
  clear retry state, not a blank crash.
- **CORS:** the FastAPI backend needs to explicitly allow requests from the deployed Vercel
  frontend's origin.
- **Latency:** should stay well under a couple of seconds per screening call — Groq's inference
  speed makes this comfortable even live on stage.

---

## 10. Environment & Secrets

**Backend (FastAPI host):**
- `GROQ_API_KEY` — from console.groq.com, free, no credit card required
- `DATABASE_URL` — from neon.tech after creating a free project
- `FRONTEND_ORIGIN` — the deployed Vercel URL, for CORS

**Frontend (Vercel):**
- `NEXT_PUBLIC_API_BASE_URL` — the deployed FastAPI backend's URL

None of these get committed to git — set them in `.env` locally (gitignored) and in each
platform's environment variable settings for production.

---

## 11. Explicitly Out of Scope

- Full production authentication/authorization system
- Multi-tenancy (multiple banks/agencies as genuinely separate customers)
- Real audio file upload + transcription
- Any real customer or agency data — synthetic only, always
- Automated test suite beyond manual QA before each deploy

---

## 12. Open Questions

- Are the actual published detailed conduct standards from the Consumer Credit Commission
  available yet, or is the screening prompt still working from general codes-of-conduct language
  in public reporting? This affects how confidently the rule wording can be phrased.
- Is the P2 role-based access gate worth building, or better spent on rehearsal and polish?
