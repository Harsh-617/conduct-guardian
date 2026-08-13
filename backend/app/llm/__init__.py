"""LLM screening layer — Groq-backed compliance judging.

Submodules:

* `client` — the only place the `groq` SDK is imported; defines the
  `LLMClient` protocol production and test callers depend on.
* `screening` — judges a collector's message against the rule pack.
* `hardship` — detects hardship disclosures in customer-side messages.
* `coaching` — summarises a collector's recurring conduct problem.
"""

from __future__ import annotations
