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

The advertised "14,400 requests/day" is not the limit that bites. The one that
does, measured live on this account:

| Model | Free-tier cap | What that means here |
|---|---|---|
| `llama-3.3-70b-versatile` | **100,000 tokens per DAY** | ~70 screening calls/day. **One 75-message seed run exhausts it.** |
| `llama-3.1-8b-instant` | Much larger budget | Used for bulk seeding |

We hit this for real: `Rate limit reached ... on tokens per day (TPD): Limit
100000, Used 99175`. Every `/screen` call carries the full rule pack and JSON
schema in its system prompt, so calls are token-heavy.

**Consequences you must plan around:**

- **Seed with the bulk model.** `seed.seed` does this by default —
  `use_bulk_model: true` on each request. Don't pass `--full-model` unless you
  have a specific reason; it will eat the day's 70B budget in one run.
- **Budget ~70 live 70B screens per day.** Rehearsal burns the same pool as the
  pitch. If you rehearse hard in the morning you can be throttled by afternoon.
- **Seed the day BEFORE if you can**, or early enough that the rolling window
  recovers.
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
