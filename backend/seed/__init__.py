"""Seed data + seeding script for Conduct Guardian.

Everything the demo database is built from lives here: synthetic agencies,
collectors, accounts, a labelled message template bank, and the planner that
turns those templates into a timed message plan. See `seed.sample_data` for
the data and `seed.seed` for the script that drives it through the real
`/screen` endpoint.
"""

from __future__ import annotations
