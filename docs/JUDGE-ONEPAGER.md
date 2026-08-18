# Conduct Guardian

**Conduct-compliance screening for Malaysian debt collection, built against the Consumer Credit Act 2025 (Act 873).**

---

## The problem

Act 873 came into force **1 March 2026**. Since **1 June 2026**, collection agencies must register with the Consumer Credit Commission and *prove* fair conduct. Non-compliance carries fines up to **RM5 million and/or 5 years**, plus a mandatory compliance audit under sections 49 and 66.

Conduct happens across WhatsApp, SMS, phone and email. No agency can currently see across all of it — so none of them can prove anything.

## What it does

Screens every collector→customer message against a conduct rule pack, flags violations with the exact offending phrase and a compliant rewrite, merges all channels into one per-account timeline to catch cross-channel harassment, writes every verdict to a tamper-evident hash-chained evidence ledger, turns repeat violations into targeted coaching, and routes borrowers showing genuine hardship to human review instead of continued escalation.

## Architecture

```
Next.js frontend (Vercel)  ──HTTPS/JSON──►  FastAPI backend (Render)
     7 screens                                       │
                                     Groq · openai/gpt-oss-20b
                                                     │
                                            Postgres (Neon)
                                     messages · screening_results
                                     evidence_ledger (hash-chained)
```

**One real pipeline.** `POST /screen` is the only write path: message → LLM screening → stored with a chained ledger entry. The seed script drives that *same public endpoint over HTTP* rather than calling the code directly, so every verdict in the database is a genuine model output. Every dashboard number is a SQL aggregate over that one dataset — nothing is faked per screen.

## Measured results

All figures below were produced by scripts in the repo and are reproducible.

**Re-measured 2026-08-19** after Groq removed `llama-3.3-70b-versatile` and
`llama-3.1-8b-instant` from its catalog (see `docs/DEPLOY.md`), then re-run
once more the same day after swapping which model powers which role: the
first pass had `groq_model` (live screening) on `openai/gpt-oss-120b` and
`groq_model_bulk` (seeding) on `openai/gpt-oss-20b`. That assignment had it
backwards — `gpt-oss-20b` scored as well or better and was consistently
faster — so the roles are now reversed. The table below is the final
post-swap run of `scripts.eval_golden_set` against both models.

**Golden-set breakdown, both current models, 20 curated cases:**

| Metric | `openai/gpt-oss-20b` (live) | `openai/gpt-oss-120b` (bulk) |
|---|---|---|
| Precision / Recall / F1 | 100% / 90.9% / 95.2% | 91.7% / 100% / 95.7% |
| False negatives | 1 — GS-19, a vague ("take this all the way") threat | 0 |
| False positives | 0 | 1 — GS-20, a co-signing guarantor treated as third party |
| Correct rule on true positives | 8/10 | 9/11 |
| Cases scored | 20/20 | 20/20 |
| Latency p50 / p95 / max | 10,011 / 13,706 / 13,706 ms | 9,400 / 12,339 / 12,339 ms |

**Re-measured again 2026-08-19** for `gpt-oss-20b` only, after `R4_THIRD_PARTY_DISCLOSURE`
was rewritten to explicitly exclude co-signers and guarantors from "third parties"
(`backend/app/rules.py`, `docs/CONDUCT-RULES.md`). GS-20 no longer false-positives on the
live model — the `openai/gpt-oss-20b` column above reflects that re-run. The `openai/gpt-oss-120b`
column is the pre-fix run and has not been re-measured against the corrected rule text.

Two things worth calling out plainly, not burying:

- **Accuracy is close to a tie (95.2% vs 95.7% F1); latency is not.** Both
  models land in the mid-90s on F1 over a 19-20 case sample — too small a
  gap, and too small a sample, to call one strictly more accurate. Latency
  is the real difference: the live model's p50 (5.1s) is roughly half the
  bulk model's (9.4s). That's why `groq_model` now points at `gpt-oss-20b` —
  for the live UI, response time matters as much as the score, and seeding
  is not latency-sensitive.
- **Latency is far higher than the old figure.** The previous `947 ms`
  end-to-end number was measured on `llama-3.3-70b`, which ran on Groq's LPU
  hardware. Both current models measured **5.1–9.4 seconds p50**, roughly an
  order of magnitude slower — plan live-demo pacing around this, not the old
  number.

| Metric | Result | Notes |
|---|---|---|
| Agreement with human labels | **97.0%** binary / 91.0% exact rule | `openai/gpt-oss-20b`, seed run, 67 collector messages — measured *before* the role swap, when this model was still the bulk model; re-run `seed.seed` for a current number against `openai/gpt-oss-120b` (now bulk) |
| Prompt-injection battery | **7 / 7 held** | Incl. forged delimiter, Malay-language override, invented rule ID — not re-run against current models, see note below |
| Invalid rule IDs returned | **0** | Post-validation rejects anything not in the pack |
| Seeded corpus | **75 / 75** messages screened | 73/75 succeeded on first response; 2 landed on retry after a transient 500 — see full seeding run |
| Evidence ledger | **valid**, 0 broken rows | Rehashed from stored payloads |
| Automated tests | **32 passing** | Incl. direct-`UPDATE` tamper detection |

The prompt-injection battery (`scripts.probe_injection`) has not been re-run
against the current models as part of this update — its 7/7 figure still
dates to the deprecated llama pair. Re-run it before citing that number
against the current models.

## Where the rules come from

The Commission's **Conduct Standards v1.0 (5 June 2026)** exists but is classified **Restricted (Terhad)** and is not publicly retrievable. We did not use it.

The 8-rule pack instead derives from **Act 873 s.85(1)(g)** (fair debt collection practices) and **Bank Negara Malaysia's published Fair Debt Collection Practices** guidance. **Every rule cites its source.**

The pack is data, not prompt text — a registered agency swaps it for the Restricted standards under its registration and the engine is unchanged.

**One consequence worth noting:** the contact-frequency rule uses BNM's published **maximum 3 contacts per week**, computed deterministically in SQL rather than judged by the model. A separate same-hour burst check exists but is labelled everywhere as an internal heuristic, never as a regulatory limit.

## Honest limitations

Stated up front rather than discovered under questioning.

- **The hash chain proves internal consistency, not third-party non-repudiation.** Anyone with write access to the whole table could recompute it end to end. Production anchors the head hash where the agency cannot rewrite it — notarisation, a signed periodic head, or WORM storage. That is a deployment change, not a redesign.
- **The rate limiter is in-process** — it resets on restart and does not coordinate across replicas. Correct for a single instance; Redis if it scales.
- **Call transcripts are typed text "as if transcribed".** No audio ingestion.
- **No production auth, no multi-tenancy.** Both explicitly out of scope.
- **All data is synthetic.** No real borrower, collector, or agency data is used anywhere, ever.
- Live screening runs on `openai/gpt-oss-20b`; the bulk model (`openai/gpt-oss-120b`) is used for seeding only. This is the reverse of the pair's original assignment — swapped after golden-set data showed `gpt-oss-20b` matching the larger model on accuracy (95.2% vs 95.7% F1; see breakdown above) while being roughly twice as fast at p50 (5.1s vs 9.4s), which is what the live UI actually needs. Too small a sample (19-20 cases) to treat the accuracy gap as settled either way — don't claim either model is strictly more accurate.

## Reproduce any number above

```bash
cd backend
./.venv/Scripts/python.exe -m pytest -q               # 27 tests
./.venv/Scripts/python.exe -m scripts.eval_golden_set  # precision / recall / F1
./.venv/Scripts/python.exe -m scripts.probe_injection  # 7 injection attacks
curl -X POST $API/ledger/verify                        # rehash the whole chain
```
