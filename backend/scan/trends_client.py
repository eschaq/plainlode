"""Scrapingdog Google Trends client — the Plainlode live signal pull.

Pulls interest-over-time (TIMESERIES) for a list of query terms and returns one
TermSeries per term. Scrapingdog allows up to 5 queries per TIMESERIES call and
charges 5 credits per successful call, so terms are batched in groups of 5.

Data layer only: no LLM calls, no ranking. The ranker consumes TermSeries next.

The API key is read from SCRAPINGDOG_API_KEY, exported into the environment via
.env before running (no python-dotenv).
"""

import os

import requests

from backend.scan.models import TermSeries, TrendPoint

ENDPOINT = "https://api.scrapingdog.com/google_trends"
MAX_QUERIES_PER_CALL = 5
TIMEOUT_SECONDS = 45


def _batched(items, size):
    """Yield successive `size`-length chunks of `items`."""
    for start in range(0, len(items), size):
        yield items[start:start + size]


def _fetch_batch(api_key, queries, geo):
    """Pull one TIMESERIES call for up to 5 queries. Returns list[TermSeries].

    On any failure (network error, non-200, non-JSON, or empty timeline_data)
    the batch is skipped and an empty list is returned so the run continues.
    """
    params = {
        "api_key": api_key,
        "query": ",".join(queries),
        "data_type": "TIMESERIES",
        "geo": geo,
    }
    try:
        resp = requests.get(ENDPOINT, params=params, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        print(f"[trends_client] request error for {queries}: {exc}")
        return []

    if resp.status_code != 200:
        print(f"[trends_client] HTTP {resp.status_code} for {queries}: "
              f"{resp.text[:180]}")
        return []

    try:
        body = resp.json()
    except ValueError:
        print(f"[trends_client] non-JSON body for {queries}: {resp.text[:180]}")
        return []

    timeline = (body or {}).get("interest_over_time", {}).get("timeline_data", [])
    if not timeline:
        print(f"[trends_client] empty timeline_data for {queries}, skipping batch")
        return []

    # timeline_data is a list of time points; each point's `values` array holds
    # one entry per query, in the same order the queries were sent. Build a
    # points list per query index, then map back to the input query strings.
    points_by_index = {i: [] for i in range(len(queries))}
    for point in timeline:
        date = point.get("date", "")
        try:
            timestamp = int(point.get("timestamp", 0))
        except (TypeError, ValueError):
            timestamp = 0
        for i, entry in enumerate(point.get("values", [])):
            if i not in points_by_index:
                continue
            try:
                value = int(entry.get("extracted_value", 0))
            except (TypeError, ValueError):
                value = 0
            points_by_index[i].append(TrendPoint(date, timestamp, value))

    series = []
    for i, query in enumerate(queries):
        series.append(TermSeries(query=query, geo=geo, points=points_by_index[i]))
    return series


def fetch_timeseries(queries, geo="US"):
    """Pull interest-over-time for `queries` at `geo`. Returns list[TermSeries].

    Terms are batched at most 5 per Scrapingdog call. A batch that fails or comes
    back empty is skipped rather than aborting the whole run, so a partial result
    is still returned.
    """
    api_key = os.environ.get("SCRAPINGDOG_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "SCRAPINGDOG_API_KEY not set. Source .env before running: "
            "set -a; source .env; set +a"
        )

    results = []
    for batch in _batched(list(queries), MAX_QUERIES_PER_CALL):
        results.extend(_fetch_batch(api_key, batch, geo))
    return results


if __name__ == "__main__":
    seeds = [
        "soy candle",
        "candle refill kit",
        "beeswax candle",
        "wax melts",
        "candle making kit",
    ]
    series_list = fetch_timeseries(seeds, geo="US")
    for series in series_list:
        last = series.points[-1].value if series.points else "—"
        print(f"{series.query:20}  points={len(series.points):3}  last={last}")
