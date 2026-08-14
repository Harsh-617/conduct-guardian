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
                                          Groq · Llama 3.3 70B
                                                     │
                                            Postgres (Neon)
                                     messages · screening_results
                                     evidence_ledger (hash-chained)
```

**One real pipeline.** `POST /screen` is the only write path: message → LLM screening → stored with a chained ledger entry. The seed script drives that *same public endpoint over HTTP* rather than calling the code directly, so every verdict in the database is a genuine model output. Every dashboard number is a SQL aggregate over that one dataset — nothing is faked per screen.

## Measured results

All figures below were produced by scripts in the repo and are reproducible.

| Metric | Result | Notes |
|---|---|---|
| Agreement with human labels | **96.6%** | llama-3.3-70b, 59 collector messages |
| Golden-set precision / recall / F1 | **91.7% / 100% / 95.7%** | llama-3.1-8b, 20 curated cases |
| **False negatives** | **0** | No real violation missed — the right way to err |
| False positives | 1 | A co-signing guarantor case; arguably a legitimate party |
| Prompt-injection battery | **7 / 7 held** | Incl. forged delimiter, Malay-language override, invented rule ID |
| Invalid rule IDs returned | **0** | Post-validation rejects anything not in the pack |
| Live screening latency | **947 ms** | llama-3.3-70b, end to end |
| Seeded corpus | **75 / 75**, 0 failures | Every verdict from the real endpoint |
| Evidence ledger | **valid**, 0 broken rows | Rehashed from stored payloads |
| Automated tests | **27 passing** | Incl. direct-`UPDATE` tamper detection |

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
- The bulk model (llama-3.1-8b) is materially weaker than llama-3.3-70b — 85.5% vs 96.6% agreement. It is used for seeding only; live screening runs on 70B.

## Reproduce any number above

```bash
cd backend
./.venv/Scripts/python.exe -m pytest -q               # 27 tests
./.venv/Scripts/python.exe -m scripts.eval_golden_set  # precision / recall / F1
./.venv/Scripts/python.exe -m scripts.probe_injection  # 7 injection attacks
curl -X POST $API/ledger/verify                        # rehash the whole chain
```
