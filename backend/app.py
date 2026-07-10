"""Minimal FastAPI backend exposing the Plainlode scan engine to a frontend.

Endpoints:
  POST /api/scan          run a scan + briefing for a category (returns all at once)
  GET  /api/scan/stream   same pipeline, streamed as SSE stage-by-stage
  POST /api/explain       plain-English explainer for a produced briefing
  GET  /api/health        liveness check

Run from the repo root:
  uvicorn backend.app:app --reload

Env is read by the scan modules themselves (SCRAPINGDOG_API_KEY, FIREWORKS_*),
so source .env before running: set -a; source .env; set +a
"""

import json
import os
import queue
import threading
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.scan.briefing import write_briefing, write_explainer
from backend.scan.models import Finding, ScanResult, TermSeries
from backend.scan.scan import run_scan
from backend.scan.seed_gen import generate_seeds
from backend.scan.trends_client import NO_DATA_SOURCE

app = FastAPI(title="Plainlode API", version="0.1.0")

# CORS. Exact production origins come from the CORS_ORIGINS env var (comma-
# separated, e.g. "https://plainlode-web.up.railway.app"); local dev origins
# (any localhost / 127.0.0.1 port) are always allowed via the regex. Set
# CORS_ORIGINS in Railway to the deployed frontend URL.
_cors_env = os.environ.get("CORS_ORIGINS", "")
_allowed_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

def _finding_dict(f: Finding) -> dict:
    # slope is a fraction (0.318 == +31.8%); the frontend formats it.
    return {"query": f.query, "direction": f.direction,
            "slope": round(f.slope, 4), "rank": f.rank}


class ScanRequest(BaseModel):
    category: str
    seeds: list[str] | None = None


class FindingIn(BaseModel):
    query: str
    direction: str = ""
    slope: float = 0.0
    rank: int = 0


class ExplainRequest(BaseModel):
    category: str
    briefing: str
    findings: list[FindingIn] = []


@app.get("/api/health")
def health():
    return {"status": "ok"}


# UI labels for each pipeline stage, keyed by (stage, status). Kept here so the
# data layer stays free of presentation strings; the streaming callback attaches
# the label as each event flows through.
STAGE_LABELS = {
    ("seeds", "start"): "Finding products to watch",
    ("seeds", "done"): "Found products to watch",
    ("demand", "start"): "Pulling live demand",
    ("demand", "done"): "Live demand pulled",
    ("rank", "start"): "Ranking what's moving",
    ("rank", "done"): "Ranked what's moving",
    ("supply", "start"): "Checking live supply",
    ("supply", "done"): "Live supply checked",
    ("briefing", "start"): "Writing the briefing",
    ("briefing", "done"): "Briefing written",
}


def _scan_pipeline(category: str, seeds_override, on_stage=None) -> dict:
    """Shared scan + briefing pipeline behind both /api/scan and the SSE stream.

    Emits stage events via on_stage (seeds, demand, rank, supply, briefing).
    Returns the response dict (same shape as POST /api/scan). Raises RuntimeError
    if the briefing model step fails on real data; the caller decides how to
    surface it (502 for POST, an error event for the stream).
    """
    def emit(stage, status, **extra):
        if on_stage:
            on_stage({"stage": stage, "status": status, **extra})

    t_start = time.perf_counter()

    # Seeds: caller's if given, else generate from the category (fallback helper
    # never breaks the scan).
    emit("seeds", "start")
    if seeds_override:
        seeds, seed_source = seeds_override, "request"
    else:
        seeds, seed_source = generate_seeds(category)
    emit("seeds", "done")

    # run_scan emits demand / rank / supply stages internally.
    result: ScanResult = run_scan(seeds, category, seed_source=seed_source, on_stage=on_stage)
    result.category = category

    above = sorted((f for f in result.findings if not f.low_volume),
                   key=lambda f: f.rank)
    below = [f for f in result.findings if f.low_volume]

    # Honest no-data state: live failed and no snapshot, or nothing above the
    # floor. Do not invoke the briefing model on nothing; never fabricate.
    has_data = result.source != NO_DATA_SOURCE and bool(above)

    briefing = None
    if has_data:
        emit("briefing", "start")
        briefing = write_briefing(result)  # may raise RuntimeError
        emit("briefing", "done")

    print(f"[scan] category={category!r} seeds={seed_source} source={result.source} "
          f"has_data={has_data} total={time.perf_counter() - t_start:.1f}s")

    return {
        "category": category,
        "source": result.source,
        "pulled_at": result.pulled_at,
        "has_data": has_data,
        "findings": [_finding_dict(f) for f in above],
        "below_floor": [_finding_dict(f) for f in below],
        "briefing": briefing,
    }


@app.post("/api/scan")
def scan(req: ScanRequest):
    """Run the scan and briefing, returning the full result at once. The explainer
    is a separate, slower call (POST /api/explain). Kept as the fallback for the
    SSE stream below."""
    category = req.category.strip()
    if not category:
        raise HTTPException(status_code=400, detail="category is required")
    try:
        return _scan_pipeline(category, req.seeds)
    except RuntimeError as exc:
        # Briefing is the product; if the model step fails, surface it.
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/api/scan/stream")
def scan_stream(category: str):
    """Stream real scan progress as Server-Sent Events. Emits one JSON event per
    stage (start + done), then a final {"stage":"complete","result":...} whose
    result has the same shape as POST /api/scan."""
    category = (category or "").strip()
    if not category:
        raise HTTPException(status_code=400, detail="category is required")

    events: "queue.Queue" = queue.Queue()
    DONE = object()

    def on_stage(ev: dict):
        ev = dict(ev)
        ev["label"] = STAGE_LABELS.get((ev.get("stage"), ev.get("status")), "")
        events.put(ev)

    def worker():
        try:
            result = _scan_pipeline(category, None, on_stage=on_stage)
            events.put({"stage": "complete", "result": result})
        except Exception as exc:  # stream an error rather than crash the request
            events.put({"stage": "error", "detail": str(exc)})
        finally:
            events.put(DONE)

    threading.Thread(target=worker, daemon=True).start()

    def event_source():
        while True:
            ev = events.get()
            if ev is DONE:
                break
            yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/explain")
def explain(req: ExplainRequest):
    """Write just the plain-English explainer for an already-produced briefing.
    Called after /api/scan so the briefing shows immediately and the explainer
    card fills in a moment later."""
    category = req.category.strip()
    if not category or not req.briefing.strip():
        raise HTTPException(status_code=400, detail="category and briefing are required")

    # Rebuild a minimal ScanResult so write_explainer can render the findings
    # into its context. Series are empty; the explainer only needs query /
    # direction / slope / rank, all carried on the request findings.
    findings = [
        Finding(query=f.query, series=TermSeries(f.query, "", []),
                slope=f.slope, direction=f.direction, rank=f.rank, low_volume=False)
        for f in req.findings
    ]
    result = ScanResult(geo="", pulled_at="", source="", category=category,
                        findings=findings)
    t0 = time.perf_counter()
    try:
        explainer = write_explainer(result, req.briefing)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    print(f"[/api/explain] category={category!r} write_explainer={time.perf_counter() - t0:.1f}s")
    return {"explainer": explainer}
