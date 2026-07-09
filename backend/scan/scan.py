"""Scan orchestrator for Plainlode.

Ties the data layer together: pull interest-over-time, rank by slope-derived
rising, pass through the (stubbed) cheap-tier filter seam, and return a typed
ScanResult. No FastAPI, no LLM client. Runs from the repo root:

    python -m backend.scan.scan
"""

import json
import os
from datetime import datetime, timezone

from backend.scan.filter import filter_findings
from backend.scan.models import ScanResult
from backend.scan.ranker import (
    MIN_RECENT_MEAN,
    WINDOW,
    _for_means,
    _mean,
    _windows,
    rank_findings,
)
from backend.scan.trends_client import fetch_with_snapshot

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RUN_LOG_PATH = os.path.join(_REPO_ROOT, "data", "run_log.jsonl")


def _append_run_log(result: ScanResult, seeds: list[str], category: str,
                    seed_source: str = "request") -> None:
    """Append one flat JSON line summarizing this scan to the run log.

    Fail-safe: any error here is logged and swallowed. The briefing is the
    product; the run log is secondary and must never break a scan.
    """
    try:
        kept = [f.query for f in result.findings if not f.low_volume]
        entry = {
            "ts": result.pulled_at,
            "category": category,
            "source": result.source,
            "seed_source": seed_source,  # how the seeds were chosen: model / fallback / request
            "seed_count": len(seeds),
            "kept_count": len(kept),
            "kept": kept,
        }
        os.makedirs(os.path.dirname(RUN_LOG_PATH), exist_ok=True)
        with open(RUN_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except Exception as exc:  # never let logging break a scan
        print(f"[run_log] failed to write log entry: {exc}")


def run_scan(seeds: list[str], category: str, geo: str = "US",
             seed_source: str = "request") -> ScanResult:
    """Run one scan end to end and return a ScanResult.

    Pull the seed terms' interest-over-time (live, with a snapshot fallback),
    rank them, pass the ranked findings through the filter seam, and stamp the
    result with provenance. `source` records whether the data came from a live
    pull or a snapshot; `seed_source` records how the seeds were chosen (model /
    fallback / request) and is written to the run log. One line is appended to
    the run log per scan.
    """
    series_list, source = fetch_with_snapshot(seeds, geo, key=category)
    ranked = rank_findings(series_list)
    findings = filter_findings(ranked, category)
    result = ScanResult(
        geo=geo,
        pulled_at=datetime.now(timezone.utc).isoformat(),
        source=source,
        findings=findings,
    )
    _append_run_log(result, seeds, category, seed_source)
    return result


def run_briefing(
    seeds: list[str], category: str, geo: str = "US"
) -> tuple[ScanResult, str, str]:
    """Run the scan, write the briefing, then write the plain-English explainer.

    Returns (scan_result, briefing_text, explainer_text). The two texts are kept
    separate so the frontend can render them in distinct UI blocks. The category
    is stamped onto the ScanResult so the briefing layer can render it.
    """
    # Imported here to avoid a circular import (briefing imports scan for this).
    from backend.scan.briefing import write_briefing, write_explainer

    scan_result = run_scan(seeds, category, geo)
    scan_result.category = category
    briefing = write_briefing(scan_result)
    explainer = write_explainer(scan_result, briefing)
    return scan_result, briefing, explainer


if __name__ == "__main__":
    seeds = ["school supplies", "lunch box", "pencil case", "dorm bedding", "kids backpack"]
    category = "back to school"
    result = run_scan(seeds, category=category)

    print(f"category:  {category}")
    print(f"pulled_at: {result.pulled_at}")
    print()

    def recent_mean_of(f):
        _, recent = _windows(_for_means([p.value for p in f.series.points]), WINDOW)
        return _mean(recent), len(recent)

    print(f"{'rank':>4}  {'query':20}  {'direction':9}  "
          f"{'slope':>8}  {'recent':>7}  {'used':>4}  {'last':>5}")
    for f in result.findings:
        if f.low_volume:
            continue
        recent_mean, used = recent_mean_of(f)
        last = f.series.points[-1].value if f.series.points else 0
        print(f"{f.rank:>4}  {f.query:20}  {f.direction:9}  "
              f"{f.slope * 100:>7.1f}%  {recent_mean:>7.1f}  {used:>4}  "
              f"{last:>5.1f}")

    low = [f for f in result.findings if f.low_volume]
    if low:
        print(f"\nbelow volume floor (recent mean < {MIN_RECENT_MEAN:.0f}, "
              f"excluded from ranking):")
        for f in low:
            recent_mean, _ = recent_mean_of(f)
            print(f"      {f.query:20}  {f.direction:9}  "
                  f"{f.slope * 100:>7.1f}%  recent={recent_mean:>6.1f}")
