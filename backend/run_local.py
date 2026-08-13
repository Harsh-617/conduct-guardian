"""Local dev server.

Use this instead of `uvicorn app.main:app` on Windows:

    py -3 run_local.py            # or ./.venv/Scripts/python.exe run_local.py

psycopg's async mode cannot use Windows' default ProactorEventLoop. Setting the
event-loop policy is NOT enough — uvicorn runs its own loop setup afterwards and
overrides it. So this builds the loop itself (`loop="none"` tells uvicorn to
leave loop creation alone) and hands `asyncio.run` an explicit
`SelectorEventLoop` factory.

On Linux (Render) none of this is needed; render.yaml uses plain uvicorn.
"""

from __future__ import annotations

import asyncio
import os

import uvicorn

from app.platform_compat import asyncio_run


def main() -> None:
    config = uvicorn.Config(
        "app.main:app",
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "8000")),
        log_level="info",
        # Leave loop creation to us — see the module docstring.
        loop="none",
    )
    server = uvicorn.Server(config)
    asyncio_run(server.serve())


if __name__ == "__main__":
    main()
