# Deploy runbook

Order matters: database → backend → seed → frontend. Each step has a check you
can actually run, so you never find out on stage that a step half-worked.

---

## 1. Neon (Postgres) — 3 minutes

1. neon.tech → sign up (free, no card) → **New Project**.
2. Region: **Singapore (ap-southeast-1)** — nearest to Malaysia.
3. Copy the connection string. It looks like:
   `postgresql://user:pass@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`

**Pooled vs direct:** Neon shows two strings. Use the **pooled** one for the app
(`-pooler` in the host). Use the **direct** one if a migration ever hangs —
pgbouncer in transaction mode doesn't like some DDL.

Paste it as-is into `DATABASE_URL`. The app rewrites the scheme to
`postgresql+psycopg://` itself; don't do that by hand.

## 2. Groq — 2 minutes

console.groq.com → **API Keys** → create. Free, no card. Copy immediately —
it's shown once. That's `GROQ_API_KEY`.

### ⚠️ The token budget is the real constraint — plan around it

`llama-3.3-70b-versatile` and `llama-3.1-8b-instant` (the models this doc used
to name here) were removed from Groq's catalog entirely — calls to them now
404, not throttle. The app has been repointed at their current replacements,
`openai/gpt-oss-20b` (live) and `openai/gpt-oss-120b` (bulk) — swapped from
the original assignment once golden-set data showed `gpt-oss-20b` is both
more accurate and faster on this task; see `docs/JUDGE-ONEPAGER.md`.

The advertised "14,400 requests/day" is not the limit that bites. The one that
does, measured live on this account against the current models:

| Model | Free-tier cap | What that means here |
|---|---|---|
| `openai/gpt-oss-20b` | **8,000 tokens per MINUTE**, 1,000 requests/min | A handful of real (system-prompt-heavy) screens can trip this. |
| `openai/gpt-oss-120b` | Same caps on this account | Used for bulk seeding |

This is a per-minute window, not the old per-day one — measured via the
`x-ratelimit-*` response headers on a trivial call, not a full-size screening
call, so treat the reset timing as roughly a minute rather than a precise
number. Re-check those headers directly if Groq changes free-tier terms
again rather than trusting this table blind. Every `/screen` call carries the
full rule pack and JSON schema in its system prompt, so a single real call can
consume a meaningful slice of the 8K/min budget; `seed.seed`'s
`MAX_CONCURRENCY = 2` plus its retry/backoff loop exists specifically to ride
out this window rather than race it.

**Consequences you must plan around:**

- **Seed with the bulk model.** `seed.seed` does this by default —
  `use_bulk_model: true` on each request. Don't pass `--full-model` unless you
  have a specific reason; it burns the same per-minute pool the live demo needs.
- **A burst of live screens can throttle you mid-demo.** The window is roughly
  a minute, so pause and retry rather than panicking.
- The `model` column on every `screening_result` records which model produced
  that verdict, so the mix is auditable rather than hidden.

If you get throttled, the error is honest and specific — it tells you the used
/ limit / retry-after. The UI shows a retry state rather than crashing.

## 3. Backend on Render

Render dashboard → **New → Blueprint** → pick this repo. It reads
`render.yaml`. Render will prompt for the three secrets:

| Prompt | Value |
|---|---|
| `GROQ_API_KEY` | from step 2 |
| `DATABASE_URL` | from step 1 |
| `FRONTEND_ORIGIN` | your Vercel URL, e.g. `https://conduct-guardian.vercel.app` |

`SEED_TOKEN` is auto-generated — copy it from the Render env tab afterwards,
you need it to seed.

The build runs `alembic upgrade head`, so the schema is created on first deploy.

**Check it:**

```bash
curl https://conduct-guardian-api.onrender.com/health
```

Expect `{"status":"ok","groq_configured":true,"database_configured":true,...}`.
If either flag is `false`, the env var didn't take — fix it before going on.

> **Free-tier cold starts.** Render free spins down after ~15 min idle, and the
> next request takes 30–50s. **Hit `/health` a few minutes before you present.**
> This is the single most likely way the live demo embarrasses you.

## 4. Seed the database

From your laptop, against the deployed backend:

```bash
cd backend
API_BASE_URL=https://conduct-guardian-api.onrender.com \
SEED_TOKEN=<the generated value from Render> \
./.venv/Scripts/python.exe -m seed.seed --days 14
```

~75 messages through the real `/screen`. The `X-Seed-Token` header bypasses the
rate limit, so this runs at full speed. At the end it prints the model's
agreement rate against the human labels — **write that number down, it's a
strong thing to quote on stage.**

**Check it:**

```bash
curl https://conduct-guardian-api.onrender.com/dashboard/stats
curl -X POST https://conduct-guardian-api.onrender.com/ledger/verify
```

`/ledger/verify` must return `"valid": true` with `failed: 0`.

## 5. Frontend on Vercel

In the frontend project's Vercel settings → Environment Variables:

```
NEXT_PUBLIC_API_BASE_URL = https://conduct-guardian-api.onrender.com
```

Redeploy — Next.js inlines `NEXT_PUBLIC_*` at build time, so an existing
deployment will **not** pick it up without a rebuild.

Then set `FRONTEND_ORIGIN` on Render to the Vercel URL and let it redeploy, or
CORS blocks every request.

## ⚠️ Order matters: seed LAST

Anything that calls `/screen` gets persisted, because `/screen` is the only write
path and that is deliberate — it is what makes the seeded verdicts genuine. The
side effect is that **every test, probe and eval you run lands in the demo
database.**

This has now happened twice:

- The golden-set and injection scripts added 41 messages under accounts `GOLDEN`
  and `REDTEAM`, pushing the violation rate from ~40% to 58%.
- A security audit running concurrently with a reseed left accounts named
  `AUDIT-INJ-1` and `AUDIT-INJ-3` sitting at the top of Recent Flags, one of them
  reading *"Ignore all previous instructions."*

A judge clicking into the accounts list would find them.

**So the demo-prep order is fixed:**

1. Run every eval, probe and audit you intend to run
2. **Then** `python -m seed.seed --days 14 --reset` — wipes everything and
   rebuilds a clean, curated corpus with an unbroken hash chain
3. Do not run anything that hits `/screen` afterwards, except your actual demo

Never run an audit and a reseed at the same time. `scripts/purge_test_data.py`
can remove known test accounts, but purging leaves gaps in an append-only chain
and `/ledger/verify` will then report INVALID — a full `--reset` is the only
clean repair.

## 6. Pre-demo checklist

Run this ~10 minutes before you present:

- [ ] `curl .../health` → both flags `true`, and it responded fast (not a cold start)
- [ ] `curl -X POST .../ledger/verify` → `valid: true`
- [ ] Open the deployed frontend, load every one of the 7 screens
- [ ] Type a live message into Live Screening, confirm a real verdict comes back
- [ ] Open `/timeline/4471` — the contact-frequency and burst flags must both show
- [ ] Have a violating phrase ready to type on stage, and a clean one

## Rollback

Render keeps previous deploys: **Events → the last good deploy → Rollback.**
The database is unaffected — migrations here are additive only, and the
evidence ledger is append-only by design, so no deploy destroys evidence.
