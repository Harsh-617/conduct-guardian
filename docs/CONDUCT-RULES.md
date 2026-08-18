# Conduct Rules — source of truth for the screening prompt

**Answers PRD §12 open question #1.** Do not invent rules. Every rule the LLM screens against
must trace back to something on this page, and every rule below carries its source so it can be
defended on stage.

---

## The honest position on sourcing (say this to judges)

The Consumer Credit Commission (Suruhanjaya Kredit Pengguna, SKP) **has** issued
**Conduct Standards v1.0, dated 5 June 2026** — the document exists and is listed on
`skp.gov.my`. But it is classified **"Restricted (Terhad)"** and the PDF returns **HTTP 403**
to the public. We could not and did not retrieve it.

So the screening rules below are built from two **public, citable** sources instead:

1. **Consumer Credit Act 2025 (Act 873)** — in force 1 March 2026. **s.85(1)(g)** empowers
   regulations and guidelines imposing requirements for **fair debt collection practices**,
   ensuring credit providers and credit service providers treat borrowers fairly during debt
   recovery. Registered entities must follow conduct standards set by the Commission;
   non-compliance carries penalties up to RM5m and/or 5 years, plus mandatory compliance audit
   (ss. 49, 66).
2. **Bank Negara Malaysia's "Fair Debt Collection Practices" guidance** — the existing,
   publicly documented baseline for debt collection agent conduct in Malaysia.

**The line to use on stage:** *"The Commission's Conduct Standards v1.0 is a Restricted
document. We built against the Act's fair-debt-collection provisions and BNM's public guidance.
In production, a registered agency ingests the Restricted standards under its registration and
the rule pack swaps out — the engine doesn't change."* That is a stronger answer than pretending
to have a document we don't have, and it shows the rule pack is deliberately pluggable.

## Rule pack v1 (what `/screen` actually checks)

| ID | Rule | What the LLM looks for | Source |
|---|---|---|---|
| `R1_ABUSIVE_LANGUAGE` | No abusive, humiliating, or intimidating language | Insults, slurs, degrading characterisations of the borrower | BNM fair debt collection |
| `R2_THREATS` | No threats, scare tactics, or threatened illegal action | Threatened violence, arrest, property seizure without legal basis, trespass | BNM fair debt collection |
| `R3_FALSE_LEGAL_CLAIM` | No misrepresenting legal consequences or authority | Claiming imminent arrest/jail/court action that isn't real; implying police powers | Act 873 fair-dealing intent |
| `R4_THIRD_PARTY_DISCLOSURE` | Debt must not be disclosed to third parties | Naming/threatening to tell employer, family, neighbours, friends. Co-signers and guarantors are not third parties — contacting them is legitimate | BNM: deal with the borrower directly |
| `R5_CONTACT_FREQUENCY` | **Max 3 contacts per week** | Computed, not LLM-judged — see below | BNM: no more than 3 calls/week |
| `R6_IMPERSONATION` | No impersonating officials, lawyers, or law enforcement | "This is from the court", fake officer titles | Act 873 fair-dealing intent |
| `R7_PRIVACY` | Borrower privacy and dignity must be protected | Publicising the debt, shaming, sharing personal data | Act 873; BNM privacy/human-rights framing |
| `R8_HARDSHIP_IGNORED` | Genuine hardship must route to review, not escalation | Continued pressure after a clear hardship disclosure | Act 873 fair-treatment intent |

## ⚠️ Product change this forces (PRD §7)

The PRD's timeline pattern rule is an invented rule of thumb: **"≥5 contacts within 60 minutes."**

**The real, citable regulatory threshold is BNM's "no more than 3 calls per week."**

Use the real one as the primary flag (`R5_CONTACT_FREQUENCY`). Keep a burst rule
(many contacts in one hour) as a *secondary* signal labelled as such — it's a reasonable
harassment heuristic, just not a published limit. This is a straight upgrade: a judge who knows
the sector will recognise the 3-per-week figure, and an invented number invites the question
*"where does five-in-an-hour come from?"* which has no good answer.

`R5` is computed in SQL over the message history, **not** judged by the LLM — deterministic,
instant, and impossible to argue with.

## Rules for using this file

- Rule IDs are stable strings and go in `ScreeningResult.rule`. Never renumber.
- The rule pack is **data, not hardcoded prompt text** — keep it in one module so the
  "swap the pack for the Restricted standards" story is literally true.
- If the Conduct Standards v1.0 later becomes obtainable through SKP registration, that is a
  pack swap, not a rewrite.

## Sources

- [Latest Information on the Consumer Credit Act 2025 — Suruhanjaya Kredit Pengguna (SKP)](https://www.skp.gov.my/en/news/announcements/latest-information-on-the-consumer-credit-act-2025)
- [Conduct Standards v1.0, 5 June 2026 — SKP](https://www.skp.gov.my/clients/asset_491D1974-0435-41A4-B496-CE4A33AAED50/contentms/img/pdf/Conduct_Standards_v1.0.pdf) — **Restricted (Terhad), returns 403**
- [Malaysia: A Summary of the Consumer Credit Act 2025 — DFDL](https://www.dfdl.com/insights/content-hub/articles/malaysia-a-summary-of-the-consumer-credit-act-2025/)
- [Legal Brief: The Consumer Credit Act 2025 — Cheang & Ariff](https://www.cheangariff.com/knowledge/2025/07/legal-brief-the-consumer-credit-act-2025/)
- [FAQs — Harassment by Debt Collector, Bank Negara Malaysia](https://www.bnm.gov.my/faqs/banking/harassment-dca)
- [How To Deal With Debt Collectors In Malaysia — RinggitPlus](https://ringgitplus.com/en/blog/the-experts-corner/how-to-deal-with-debt-collectors-in-malaysia.html)
