# Plainlode

**The signal, mined plain.**

A live market-intelligence engine that returns a plain-language decision — not a
dashboard — for small WooCommerce owners.

**Live app:** https://plainlode-production.up.railway.app
**Backend API:** https://web-production-a8e17.up.railway.app

---

## Built for

**AMD Developer Hackathon: ACT II — Track 3 (Unicorn).**
Plainlode runs its inference on **Fireworks AI, served on AMD Instinct GPUs.**
Every scan makes two model calls on Fireworks/AMD: a cheap-tier scan filter and
the plain-language briefing engine.

## What it does

Type a store category (e.g. `back to school`). Plainlode pulls live demand
signal, reasons over it on AMD-hosted models, and hands back one decision: what
to stock, and the single live signal that would reverse that call.

## How it works

```
typed category
  → live demand pull        Scrapingdog Google Trends (interest-over-time)
  → cheap-tier scan filter  Fireworks AI / AMD Instinct — keep decision-relevant terms
  → slope-ranked findings   rising/falling by trend slope, with a volume floor
  → briefing engine         Fireworks AI / AMD Instinct — Findings / Options / Recommended
  → a decision              the call + the one live signal that would kill it
```

- **Facts are retrieved live, not recalled from training.** The demand numbers
  come from a real-time Google Trends pull on each scan.
- **Snapshot fallback.** If a live pull fails (rate limit, upstream hiccup),
  Plainlode serves the most recent *real* pull from disk and labels it a
  snapshot. It never fabricates data — with no live data and no snapshot, it
  says so plainly.
- **Volume floor.** Near-dead terms are held out of the ranking so noise can't
  masquerade as an opportunity.

## The novel behavior

Plainlode's recommendation **argues against itself.** Every briefing ends by
naming the one concrete, live signal that would reverse the call — the "kill
signal" — so the owner knows exactly what to watch for, and when to stop.

---

## Architecture

- **Backend** — FastAPI (`backend/`). The scan engine lives in `backend/scan/`:
  live pull (`trends_client.py`), slope ranker (`ranker.py`), model filter
  (`filter.py`), briefing + explainer (`briefing.py`), orchestrator (`scan.py`),
  and the Fireworks HTTP client (`fireworks_client.py`).
- **Frontend** — React + Vite (`frontend/`). Three states: input → scanning →
  result.
- **Deployment** — two services on Railway (backend + static frontend). See
  [DEPLOY.md](DEPLOY.md).

The backend talks to Scrapingdog and Fireworks over plain HTTP, so the deployed
image carries no heavy SDKs.

## Run locally

Requires Python 3.11+ and Node 18+.

**1. Backend**

```bash
git clone https://github.com/eschaq/plainlode.git
cd plainlode

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env           # then fill in your keys (see below)
set -a; source .env; set +a    # .env is sourced (no python-dotenv)

uvicorn backend.app:app        # http://127.0.0.1:8000
```

**2. Frontend** (second terminal)

```bash
cd frontend
npm install

# point the app at your local backend (default if unset: http://127.0.0.1:8000)
echo "VITE_API_BASE_URL=http://127.0.0.1:8000" > .env   # see frontend/.env.example

npm run dev                    # http://localhost:5173
```

Open http://localhost:5173, type a category, and mine the signal.

### Environment variables

| Variable | Where | Purpose |
|----------|-------|---------|
| `SCRAPINGDOG_API_KEY` | backend | Scrapingdog Google Trends key |
| `FIREWORKS_API_KEY` | backend | Fireworks AI key |
| `FIREWORKS_MODEL` | backend | e.g. `accounts/fireworks/models/gpt-oss-20b` |
| `CORS_ORIGINS` | backend (prod) | comma-separated allowed origins; localhost always allowed |
| `VITE_API_BASE_URL` | frontend (build-time) | backend base URL the frontend calls |

Templates: [`.env.example`](.env.example) (backend) and
[`frontend/.env.example`](frontend/.env.example).

---

## Fine-tuned voice

A custom report-voice model was fine-tuned on **Fireworks / AMD** to teach the
plain-language briefing format (proven end to end; the training-set builder is
in `finetune/`). The live app currently serves a **prompt-engineered voice on
Fireworks serverless** for always-on reliability with no cold start. Serving the
dedicated fine-tuned model is on the roadmap.

## License

MIT — see [LICENSE](LICENSE).
