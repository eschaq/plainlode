# Deploying Plainlode to Railway

Two services from the **same GitHub repo**:

- **Backend** (`plainlode-api`) — FastAPI, root directory `/`
- **Frontend** (`plainlode-web`) — Vite/React static build, root directory `frontend`

Secrets are set in Railway, never committed (`.env` is gitignored). The
committed `data/snapshots/back-to-school.json` ships with the repo so the demo
survives when Scrapingdog is out of credits.

There is a deliberate ordering: the frontend build needs the backend URL, and
the backend CORS needs the frontend URL. So: **backend first → frontend →
back-fill backend CORS.**

---

## 0. Push the repo to GitHub

```bash
git add -A
git commit -m "Deploy-ready: Railway config for backend + frontend"
git push        # to eschaq/plainlode (or your fork)
```

Confirm these are committed: `Procfile`, `requirements.txt`, `.python-version`,
`frontend/package.json` (with the `start` script), and
`data/snapshots/back-to-school.json`.

---

## 1. Create the Railway project

1. railway.app → **New Project** → **Deploy from GitHub repo** → pick the repo.
2. Railway creates the first service. Make it the **backend** (next step).

---

## 2. Backend service (`plainlode-api`)

1. In the service **Settings**:
   - **Root Directory**: `/` (repo root — the `backend` package must be
     importable, and `Procfile` + `requirements.txt` live here).
   - Railway auto-detects Python (`requirements.txt`) and uses the `Procfile`
     start command: `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`.
   - (Optional) **Healthcheck Path**: `/api/health`.
2. **Variables** — add:
   | Key | Value |
   |-----|-------|
   | `SCRAPINGDOG_API_KEY` | your Scrapingdog key |
   | `FIREWORKS_API_KEY` | your Fireworks key |
   | `FIREWORKS_MODEL` | `accounts/fireworks/models/gpt-oss-20b` |
   | `CORS_ORIGINS` | leave empty for now (set in step 4) |
3. **Settings → Networking → Generate Domain**. Copy the URL, e.g.
   `https://plainlode-api.up.railway.app` — call it `<BACKEND_URL>`.
4. Verify once it's live:
   ```bash
   curl https://<BACKEND_URL>/api/health
   # -> {"status":"ok"}
   ```

---

## 3. Frontend service (`plainlode-web`)

1. In the project: **New → GitHub Repo** → the **same** repo (adds a 2nd service).
2. In the service **Settings**:
   - **Root Directory**: `frontend`.
   - Railway auto-detects Node: runs `npm ci` → `npm run build` → `npm start`
     (the `start` script serves `dist/` on `0.0.0.0:$PORT`).
3. **Variables** — add the backend URL as a **build-time** var (Vite inlines it):
   | Key | Value |
   |-----|-------|
   | `VITE_API_BASE_URL` | `https://<BACKEND_URL>` (no trailing slash) |
4. **Settings → Networking → Generate Domain**. Copy it, e.g.
   `https://plainlode-web.up.railway.app` — call it `<FRONTEND_URL>`.

> Note: `VITE_API_BASE_URL` is baked in at **build** time. If you change it
> later, you must **redeploy the frontend** for it to take effect.

---

## 4. Wire CORS (back-fill the backend)

1. Go back to the **backend** service → **Variables**.
2. Set `CORS_ORIGINS` = `<FRONTEND_URL>` (exact origin, no trailing slash).
   For multiple, comma-separate them.
3. The backend redeploys automatically on the variable change.

Localhost origins are always allowed (built-in regex), so local dev keeps
working without touching `CORS_ORIGINS`.

---

## 5. Verify end-to-end

1. Open `<FRONTEND_URL>` in a browser.
2. Type **back to school** → **Mine the signal**.
3. Watch the scanning motion, then the briefing (findings + kill signal), then
   the explainer card fills a beat later.
4. Open browser devtools → Network: `/api/scan` and `/api/explain` should hit
   `<BACKEND_URL>` and return 200, with **no CORS errors** in the console.

Direct backend check (spends ~5 Scrapingdog credits, takes ~15–25s):
```bash
curl -X POST https://<BACKEND_URL>/api/scan \
  -H "Content-Type: application/json" \
  -d '{"category":"back to school"}'
```

---

## Notes

- **Backend has no `fireworks-ai` dependency** — it calls Scrapingdog and
  Fireworks over plain HTTP (`requests`). The SDK is only for the fine-tune /
  deploy scripts (`requirements-dev.txt`), so the deploy image stays lean.
- **Snapshot fallback**: if a live Scrapingdog pull fails in prod, the backend
  serves the committed back-to-school snapshot (`source: scrapingdog_snapshot`).
  Runtime pulls refresh the snapshot in the container, but that's ephemeral —
  the committed file is the durable baseline.
- **Always-on**: Railway keeps the backend warm (no cold start), which the demo
  needs.
- **Env vars, not code**: no keys are committed; set them only in Railway.
