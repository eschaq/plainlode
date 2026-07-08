"""Scan orchestrator for Plainlode.

Ties the data layer together: pull interest-over-time, rank by slope-derived
rising, pass through the (stubbed) cheap-tier filter seam, and return a typed
ScanResult. No FastAPI, no LLM client. Runs from the repo root:

    python -m backend.scan.scan
"""

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
from backend.scan.trends_client import fetch_timeseries

SOURCE = "scrapingdog_google_trends"


def run_scan(seeds: list[str], category: str, geo: str = "US") -> ScanResult:
    """Run one scan end to end and return a ScanResult.

    Pull the seed terms' interest-over-time, rank them, pass the ranked findings
    through the filter seam, and stamp the result with provenance.
    """
    series_list = fetch_timeseries(seeds, geo)
    ranked = rank_findings(series_list)
    findings = filter_findings(ranked, category)
    return ScanResult(
        geo=geo,
        pulled_at=datetime.now(timezone.utc).isoformat(),
        source=SOURCE,
        findings=findings,
    )


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
