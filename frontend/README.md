# Plainlode frontend

Vite + React app for the Plainlode briefing UI. Ported from the Claude Design
project `Plainlode.dc.html` (exact layout, branding, and the scanning-state
motion), then wired to the real FastAPI backend. It renders only data returned
by the API — no placeholder content.

## Run

```bash
# 1. Backend (from repo root, in another terminal)
set -a; source .env; set +a
uvicorn backend.app:app --port 8000

# 2. Frontend
cd frontend
npm install
npm run dev          # http://localhost:5173
```

The API base URL is read from `VITE_API_BASE_URL` (see `.env.example`), and
defaults to `http://127.0.0.1:8000`. Point it at the deployed backend for prod.

## Flow

Three states: **input → scanning → result**. Type a store category (e.g. "back
to school") and Mine the signal. The scanning motion runs for the real duration
of the request (live pull + two model calls), driven off the fetch promise, then
transitions to the briefing.

- Briefing string is parsed into Findings / Options / Recommended; the
  kill-signal sentence is pulled into its own highlighted sub-block.
- Findings strip: rising terms in gold, falling terms muted and struck-through.
- Source indicator: "Live signal" (`scrapingdog_live`) or "Recent snapshot"
  (`scrapingdog_snapshot`).
- Honest empty state when `has_data` is false — nothing fabricated.
- Fetch errors show a graceful retry.

## Layout

- `src/App.jsx` — state machine (input/scanning/result/error), drives scanning
  off the real request promise.
- `src/components/` — Header, Idle, Scanning, Result, ErrorView.
- `src/lib/api.js` — `runScan(category)` → `POST /api/scan`.
- `src/lib/parseBriefing.js` — briefing string → structured sections.
- `src/lib/theme.js` — the palette lifted from the design.
- `src/styles.css` — the six keyframes ported verbatim, plus interactive states.
