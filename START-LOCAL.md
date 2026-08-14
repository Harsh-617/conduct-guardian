# Running Conduct Guardian on your laptop

Two things have to be running at once: the **backend** (the brain) and the
**frontend** (the screens). Open two terminal windows.

## Terminal 1 — backend

```bash
cd ~/conduct-guardian-ui/backend
~/conduct-guardian/backend/.venv/Scripts/python.exe run_local.py
```

Wait until it says `Application startup complete`. Leave this window open.

Check it: open http://127.0.0.1:8000/health — you want
`"groq_configured": true, "database_configured": true`. If either says `false`,
`backend/.env` is missing a key.

## Terminal 2 — frontend

```bash
cd ~/conduct-guardian-ui
npx next start -p 3000
```

Then open **http://127.0.0.1:3000/dashboard**.

Use `127.0.0.1`, not `localhost`. They look the same but a browser treats them
as different sites, and the backend only allows the ones listed in
`FRONTEND_ORIGIN`. Both are allowed locally, but stay consistent.

## If you changed frontend code

`next start` serves a pre-built copy, so your change will not appear until you
rebuild:

```bash
npx next build
```

Then restart Terminal 2. (While actively editing, `npx next dev` instead skips
the rebuild step and reloads automatically — slower, but no build needed.)

## Common problems

**"address already in use" / EADDRINUSE**
An old copy is still running and holding the port. Closing the terminal window
does not always kill it. In PowerShell:

```powershell
Get-NetTCPConnection -LocalPort 3000 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

Change `3000` to `8000` for the backend.

**Every screen says "Service waking up"**
The frontend cannot reach the backend. Terminal 1 is not running, or it crashed
— look at that window for the error.

**Screens load but numbers are all zero**
The database is empty. Re-seed:

```bash
cd ~/conduct-guardian-ui/backend
~/conduct-guardian/backend/.venv/Scripts/python.exe -m seed.seed --days 14 --reset
```

Takes a few minutes; it sends every message through the real screening endpoint.

**Live Screening returns an error about rate limits**
Groq's free tier allows about 100,000 tokens per day on the big model, which is
roughly 70 screenings. If you have been rehearsing, you may have used them up.
It resets on a rolling basis, so waiting helps. See `docs/DEPLOY.md`.

## Before a demo

Run through `docs/DEMO-SCRIPT.md`. The short version:

1. Start both terminals, load all 7 screens once so nothing is cold
2. Open http://127.0.0.1:8000/health and confirm both flags are `true`
3. Press **Verify Chain Integrity** on the Evidence Ledger — expect
   "Chain verified"
4. Type one message into Live Screening and confirm a real verdict comes back
