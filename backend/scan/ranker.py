"""Slope-derived rising layer for the Plainlode scan.

Scrapingdog exposes interest-over-time only, no rising feed, so "rising" is
derived from the trend slope: compare a recent window of the series against the
window just before it. Input is list[TermSeries] from trends_client; output is a
ranked list[Finding], ordered by slope descending.

Pure Python. No LLM calls, no FastAPI.

Run from the repo root:  python -m backend.scan.ranker
"""

from backend.scan.models import Finding
from backend.scan.trends_client import fetch_timeseries

# Number of points in each comparison window (recent vs. prior).
WINDOW = 8

# Slope magnitude above which a term counts as rising / falling.
RISING_THRESHOLD = 0.15

# Denominator floor for the slope percent, so low-volume noise (e.g. prior_mean
# of 1) does not blow up into huge percentages.
SLOPE_FLOOR = 5.0

# Google Trends' final bucket is an in-progress period that reads artificially
# low. Drop it from the mean math so it doesn't fake a falling slope. The raw
# value is still kept for display.
DROP_TRAILING_POINTS = 1

# Recent-window mean below this counts as low-volume: a near-dead term whose
# slope is noise, not opportunity. These are excluded from the ranking.
MIN_RECENT_MEAN = 10.0


def _mean(values):
    """Mean of a list of numbers, 0.0 for an empty list."""
    return sum(values) / len(values) if values else 0.0


def _for_means(values):
    """The values that feed the mean math: raw series minus the trailing
    in-progress bucket(s). Never drops below an empty list."""
    if DROP_TRAILING_POINTS and len(values) > DROP_TRAILING_POINTS:
        return values[:-DROP_TRAILING_POINTS]
    return values


def _windows(values, n):
    """Split into (prior, recent) comparison windows.

    With at least 2n points, compare the last n against the n before that.
    Shorter series fall back to last-half vs. first-half so nothing crashes.
    """
    if len(values) >= 2 * n:
        return values[-2 * n:-n], values[-n:]
    half = len(values) // 2
    return values[:half], values[half:]


def rank_findings(series_list):
    """Turn list[TermSeries] into a ranked list[Finding].

    slope is the percent change from the prior window mean to the recent window
    mean, floored so low volume stays quiet. direction/rising follow from the
    threshold. Findings are sorted by slope descending and ranked from 1.
    """
    findings = []
    for series in series_list:
        values = [p.value for p in series.points]
        prior, recent = _windows(_for_means(values), WINDOW)
        prior_mean = _mean(prior)
        recent_mean = _mean(recent)
        slope = (recent_mean - prior_mean) / max(prior_mean, SLOPE_FLOOR)

        if slope >= RISING_THRESHOLD:
            direction = "rising"
        elif slope <= -RISING_THRESHOLD:
            direction = "falling"
        else:
            direction = "flat"

        # A near-dead term's slope is noise, not opportunity. Keep its real
        # direction/slope for transparency, but force rising off and hold it
        # out of the ranking.
        low_volume = recent_mean < MIN_RECENT_MEAN

        findings.append(Finding(
            query=series.query,
            series=series,
            slope=slope,
            direction=direction,
            rising=(direction == "rising") and not low_volume,
            low_volume=low_volume,
        ))

    ranked = sorted(
        (f for f in findings if not f.low_volume),
        key=lambda f: f.slope,
        reverse=True,
    )
    for i, finding in enumerate(ranked, start=1):
        finding.rank = i

    # Low-volume terms keep rank 0 and trail the ranked ones.
    low = [f for f in findings if f.low_volume]
    return ranked + low


if __name__ == "__main__":
    seeds = [
        "soy candle",
        "candle refill kit",
        "beeswax candle",
        "wax melts",
        "candle making kit",
    ]
    series_list = fetch_timeseries(seeds, geo="US")
    findings = rank_findings(series_list)

    # Diagnostic: last 5 raw values per term, so the trailing shape is visible
    # (the final bucket is the in-progress one dropped from the mean math).
    print("raw tails (last 5 values, trailing bucket is in-progress):")
    for series in series_list:
        tail = [p.value for p in series.points[-5:]]
        print(f"  {series.query:20}  {tail}")
    print()

    def recent_mean_of(f):
        _, recent = _windows(_for_means([p.value for p in f.series.points]), WINDOW)
        return _mean(recent), len(recent)

    print(f"{'rank':>4}  {'query':20}  {'direction':9}  "
          f"{'slope':>8}  {'recent':>7}  {'used':>4}  {'last':>5}")
    for f in findings:
        if f.low_volume:
            continue
        recent_mean, used = recent_mean_of(f)
        last = f.series.points[-1].value if f.series.points else 0
        print(f"{f.rank:>4}  {f.query:20}  {f.direction:9}  "
              f"{f.slope * 100:>7.1f}%  {recent_mean:>7.1f}  {used:>4}  "
              f"{last:>5.1f}")

    low = [f for f in findings if f.low_volume]
    if low:
        print(f"\nbelow volume floor (recent mean < {MIN_RECENT_MEAN:.0f}, "
              f"excluded from ranking):")
        for f in low:
            recent_mean, _ = recent_mean_of(f)
            print(f"      {f.query:20}  {f.direction:9}  "
                  f"{f.slope * 100:>7.1f}%  recent={recent_mean:>6.1f}")
