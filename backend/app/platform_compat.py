"""Windows event-loop compatibility for psycopg's async mode.

psycopg 3 cannot run async on Windows' default `ProactorEventLoop` and raises
`InterfaceError: Psycopg cannot use the 'ProactorEventLoop'`. Any entry point
that opens an async database connection on Windows has to start a
`SelectorEventLoop` instead.

This is a local-development concern only — Render runs Linux, where the default
loop is already compatible and both helpers below are no-ops. It lives in one
module so the three entry points (Alembic, the seeder, the local server) can't
drift apart on the fix.
"""

from __future__ import annotations

import asyncio
import sys
import warnings
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")

IS_WINDOWS = sys.platform == "win32"


def asyncio_run(coro: Coroutine[Any, Any, T]) -> T:
    """`asyncio.run` that psycopg can use on Windows.

    Uses `loop_factory` (Python 3.12+) rather than the event-loop policy API,
    which is deprecated from 3.14 — this stays warning-free.
    """
    if IS_WINDOWS:
        return asyncio.run(coro, loop_factory=asyncio.SelectorEventLoop)
    return asyncio.run(coro)


def ensure_selector_event_loop_policy() -> None:
    """Force a selector loop for libraries that build their own (uvicorn).

    Uvicorn calls `asyncio.run` itself, so there's no `loop_factory` to pass —
    the policy is the only lever. The policy API emits a DeprecationWarning on
    3.14+, suppressed here because on Windows the alternative isn't a cleaner
    API, it's a server that cannot reach the database at all.
    """
    if not IS_WINDOWS:
        return
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
