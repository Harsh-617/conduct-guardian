"""Score the screening prompt against the 20-case golden set.

The seed run reports agreement over ~75 loosely-labelled messages. This is the
sharper instrument: 20 hand-curated cases with deliberate coverage of every
LLM-judged rule plus three genuinely borderline ones, scored as a confusion
matrix so you can see WHICH way it errs.

That distinction matters for a compliance product and is worth saying out loud:
a false negative means a real violation shipped to a borrower; a false positive
means a collector is wrongly accused. They are not equally bad, and the right
trade-off is a product decision, not an accuracy number.

Run with the API up:

    ./.venv/Scripts/python.exe -m scripts.eval_golden_set
    ./.venv/Scripts/python.exe -m scripts.eval_golden_set --model llama-3.1-8b-instant
"""

from __future__ import annotations

import argparse
import asyncio
import os

import httpx

from app.config import get_settings
from app.platform_compat import asyncio_run
from tests.golden_set import GOLDEN_CASES

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
CONCURRENCY = 2


async def _run_case(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    case: dict,
    headers: dict[str, str],
    use_bulk: bool,
) -> dict:
    async with sem:
        for attempt in range(4):
            try:
                resp = await client.post(
                    "/screen",
                    json={
                        "text": case["text"],
                        "channel": "whatsapp",
                        "account_id": "GOLDEN",
                        "use_bulk_model": use_bulk,
                    },
                    headers=headers,
                    timeout=40.0,
                )
                resp.raise_for_status()
                body = resp.json()
                v = body["verdict"]
                return {
                    "id": case["id"],
                    "text": case["text"],
                    "expected_violation": case["expect_violation"],
                    "expected_rule": case.get("expect_rule"),
                    "actual_violation": v["violation"],
                    "actual_rule": v["rule"],
                    "quoted": v["quoted_phrase"],
                    "latency_ms": body["latency_ms"],
                    "note": case.get("note"),
                    "error": None,
                }
            except httpx.HTTPError as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if attempt == 3:
                    return {"id": case["id"], "error": str(exc)[:100], **{k: None for k in
                            ("actual_violation", "actual_rule", "quoted", "latency_ms")},
                            "text": case["text"],
                            "expected_violation": case["expect_violation"],
                            "expected_rule": case.get("expect_rule"),
                            "note": case.get("note")}
                await asyncio.sleep(65.0 if status in (429, 503) else 3.0)
    return {}


async def main(base_url: str, use_bulk: bool) -> None:
    settings = get_settings()
    headers = {"X-Seed-Token": settings.seed_token} if settings.seed_token else {}
    sem = asyncio.Semaphore(CONCURRENCY)

    async with httpx.AsyncClient(base_url=base_url) as client:
        results = await asyncio.gather(
            *(_run_case(client, sem, c, headers, use_bulk) for c in GOLDEN_CASES)
        )

    scored = [r for r in results if r.get("error") is None]
    errored = [r for r in results if r.get("error")]

    tp = sum(1 for r in scored if r["expected_violation"] and r["actual_violation"])
    tn = sum(1 for r in scored if not r["expected_violation"] and not r["actual_violation"])
    fp = sum(1 for r in scored if not r["expected_violation"] and r["actual_violation"])
    fn = sum(1 for r in scored if r["expected_violation"] and not r["actual_violation"])

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    rule_hits = sum(
        1 for r in scored
        if r["expected_violation"] and r["actual_violation"]
        and r["expected_rule"] == r["actual_rule"]
    )
    latencies = sorted(r["latency_ms"] for r in scored if r["latency_ms"])

    model_label = settings.groq_model_bulk if use_bulk else settings.groq_model
    print("\n" + "=" * 62)
    print(f"GOLDEN SET — {len(scored)}/{len(GOLDEN_CASES)} scored"
          + (f", {len(errored)} errored" if errored else ""))
    # Always print the model: a score quoted without naming the model that
    # produced it is not a claim anyone can check.
    print(f"MODEL: {model_label}")
    print("=" * 62)
    print(f"  true positives  {tp:>3}   false positives {fp:>3}  (collector wrongly accused)")
    print(f"  true negatives  {tn:>3}   false negatives {fn:>3}  (real violation missed)")
    print()
    print(f"  precision {precision:.1%}   recall {recall:.1%}   F1 {f1:.1%}")
    print(f"  correct rule on true positives: {rule_hits}/{tp}")
    if latencies:
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]
        print(f"  latency p50 {p50}ms   p95 {p95}ms   max {latencies[-1]}ms")

    misses = [r for r in scored if r["expected_violation"] != r["actual_violation"]]
    if misses:
        print("\nDISAGREEMENTS — read these, don't just quote the score:")
        for r in misses:
            kind = "FALSE NEG" if r["expected_violation"] else "FALSE POS"
            print(f"\n  [{kind}] {r['id']}  expected={r['expected_rule']} got={r['actual_rule']}")
            print(f"    {r['text'][:100]}")
            if r["note"]:
                print(f"    note: {r['note']}")

    if errored:
        print("\nERRORED:")
        for r in errored:
            print(f"  {r['id']}: {r['error']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("API_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument(
        "--bulk",
        action="store_true",
        help="Use GROQ_MODEL_BULK. Needed when the 70b daily token budget is spent.",
    )
    args = parser.parse_args()
    asyncio_run(main(args.base_url, args.bulk))
