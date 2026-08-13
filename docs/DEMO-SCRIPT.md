# Demo script

For a live, unscripted-questions pitch. Every claim here is one the build can
actually back — nothing in this document overstates what exists.

**Before you start, run the pre-demo checklist in `docs/DEPLOY.md`.** The single
most likely failure is Render's free-tier cold start (30–50s), and it is
entirely preventable by hitting `/health` ten minutes early.

---

## The 20-second frame

> "Malaysia's Consumer Credit Act came into force this March. Since June,
> collection agencies must register and *prove* fair conduct — RM5 million or
> five years if they can't, plus a mandatory audit. But conduct happens across
> WhatsApp, SMS, calls and email, and no agency can see across all of it.
> Conduct Guardian screens every message, and keeps the evidence."

## Beat 1 — Live Screening (the "it's real" moment)

Open Live Screening. **Type this fresh, don't paste a saved example:**

> `Pay up today you worthless deadbeat or I will call your boss and your neighbours.`

Expected, in about a second:

- **flagged R1_ABUSIVE_LANGUAGE**
- quoted phrase `worthless deadbeat` highlighted in your text
- a compliant rewrite that still pursues the debt

Say: *"That's a live call to Llama 3.3 on Groq — about 950 milliseconds. It
quotes the exact offending phrase, and it writes the compliant version, because
the collector still needs to collect."*

**Then invite a judge to type their own.** This is the strongest thing you can
do; it is not a canned demo and it will hold.

## Beat 2 — Case Timeline (the cross-channel insight)

Open account **4471**.

Say: *"One collector on WhatsApp looks fine. The pattern only appears when you
merge the channels."*

Point at the **contact-frequency flag**: more than three contacts in a rolling
seven-day window.

> "Three per week is Bank Negara's published limit, not a number we invented.
> It's computed in SQL from the message timestamps — no model involved, so it's
> deterministic and you can check it by hand."

If the burst flag also shows, note explicitly: *"That second one is our own
heuristic, not a published limit — we label it differently on purpose."*
**Volunteering that distinction buys more credibility than hiding it.**

## Beat 3 — Evidence Ledger (the audit story)

Open the Evidence Ledger, press **Verify Chain Integrity**.

> "Every verdict is hash-chained. Verify recomputes every hash from the stored
> payload and compares. Change one row and the check names that exact row."

**If a judge pushes — and a good one will:**

> "It proves internal consistency, not third-party non-repudiation. Someone with
> write access to the whole table could recompute the chain end to end. In
> production you anchor the head hash somewhere the agency can't rewrite —
> notarisation, a signed periodic head, WORM storage. That's a deployment
> change, not a redesign."

Owning that limit is worth more than pretending it isn't there.

## Beat 4 — Dashboard, Coaching, Hardship (scale + the human turn)

Sweep the Dashboard: *"Every number is a SQL aggregate over the same dataset.
Nothing on any screen is hardcoded."*

Coaching: *"Repeat violations become targeted coaching, and the pattern
description is written from that collector's real flagged messages."*

Finish on **Hardship Queue** — this is the emotional close:

> "When a borrower discloses job loss or a hospital bill, the system stops
> escalating and routes them to a human. The Act is about fair treatment, not
> just avoiding fines."

## The three questions you will get

**"How accurate is it?"**
> "Twenty hand-labelled cases as a golden set, plus every seeded message scored
> against a human label. We measure precision and recall separately because
> they're not symmetric here — a false negative ships a real violation to a
> borrower, a false positive wrongly accuses a collector."

Quote your actual numbers from `scripts/eval_golden_set.py`. **Re-run it the
morning of, and quote what it prints — never a remembered figure.**

**"Couldn't a collector just trick the AI?"**
> "We tested that." Show `scripts/probe_injection.py` output — seven injection
> attacks, including forged delimiters and a non-English override. Untrusted
> text is delimited as data, and we validate the model's answer afterwards: an
> invented rule ID is rejected, and a quote that isn't verbatim in the message
> is dropped rather than shown.

**"Where do the rules come from?"**
> "The Commission's Conduct Standards v1.0 exists but is a Restricted document —
> we can't get it. So we built against Act 873 section 85(1)(g) and Bank
> Negara's published fair debt collection guidance, and every rule cites its
> source. A registered agency swaps the rule pack for the Restricted standards;
> the engine doesn't change."

That answer is *better* than having the document, because it demonstrates the
rule pack is deliberately pluggable.

## Do not say

- "It's production ready" — it isn't, and one follow-up question exposes that.
- "100% accurate" — you have measured numbers; use them.
- "Blockchain" — it's a hash chain. Calling it a blockchain invites a question
  you'll lose.
- Anything implying the data is real. **It is synthetic, always say so.**

## If something breaks on stage

- **Screening spins** → cold start or Groq throttling. Say "we're rate-limited
  on the free tier" and move to the Timeline, which is pure SQL and always fast.
- **A screen shows zeroes** → the frontend lost the backend. Check
  `/health` in a tab. Keep one open before you start.
- **Verify shows invalid** → do not improvise. Say you'll follow up. (It is
  valid as of the last check; re-run the checklist beforehand so this can't
  surprise you.)
