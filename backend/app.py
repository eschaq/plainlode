"""Minimal FastAPI backend exposing the Plainlode scan engine to a frontend.

Endpoints:
  POST /api/scan     run a scan + briefing for a category
  GET  /api/health   liveness check

Run from the repo root:
  uvicorn backend.app:app --reload

Env is read by the scan modules themselves (SCRAPINGDOG_API_KEY, FIREWORKS_*),
so source .env before running: set -a; source .env; set +a
"""

import os
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.scan.briefing import write_briefing, write_explainer
from backend.scan.models import Finding, ScanResult, TermSeries
from backend.scan.scan import run_scan
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

# v1 default seeds when the caller omits them. The smart category-to-seeds model
# step is v2/roadmap; this is a simple placeholder, not fabricated data (these
# are real terms the live source is then queried for).
DEFAULT_SEEDS = {
    "back to school": ["school supplies", "lunch box", "pencil case",
                       "kids backpack", "dorm bedding"],
}


def seeds_for_category(category: str) -> list[str]:
    """Derive a small default seed set from a category (v1 placeholder)."""
    known = DEFAULT_SEEDS.get(category.strip().lower())
    if known:
        return list(known)
    base = category.strip()
    return [base, f"{base} kit", f"best {base}"]


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


@app.post("/api/scan")
def scan(req: ScanRequest):
    """Run the scan and briefing. Returns as soon as the briefing is ready; the
    explainer is a separate, slower call (POST /api/explain) so this stays under
    the response-time gate."""
    category = req.category.strip()
    if not category:
        raise HTTPException(status_code=400, detail="category is required")

    # Stage timing so we can confirm what /api/scan actually runs. This path is
    # scan + briefing ONLY; the explainer runs exclusively in /api/explain.
    t_start = time.perf_counter()

    seeds = req.seeds if req.seeds else seeds_for_category(category)
    t0 = time.perf_counter()
    result: ScanResult = run_scan(seeds, category)  # called exactly once
    t_scan = time.perf_counter() - t0
    result.category = category  # the briefing renderer needs the category

    above = sorted((f for f in result.findings if not f.low_volume),
                   key=lambda f: f.rank)
    below = [f for f in result.findings if f.low_volume]

    # Honest no-data state: live failed and no snapshot, or nothing above the
    # floor. Do not invoke the briefing model on nothing; never fabricate.
    has_data = result.source != NO_DATA_SOURCE and bool(above)

    briefing = None
    t_brief = 0.0
    if has_data:
        try:
            t1 = time.perf_counter()
            briefing = write_briefing(result)  # called exactly once
            t_brief = time.perf_counter() - t1
        except RuntimeError as exc:
            # Briefing is the product; if the model step fails, surface it.
            raise HTTPException(status_code=502, detail=str(exc))

    total = time.perf_counter() - t_start
    print(f"[/api/scan] category={category!r} run_scan={t_scan:.1f}s "
          f"write_briefing={t_brief:.1f}s total={total:.1f}s (no explainer on this path)")

    return {
        "category": category,
        "source": result.source,
        "pulled_at": result.pulled_at,
        "has_data": has_data,
        "findings": [_finding_dict(f) for f in above],
        "below_floor": [_finding_dict(f) for f in below],
        "briefing": briefing,
    }


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
