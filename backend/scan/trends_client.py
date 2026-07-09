"""Scrapingdog Google Trends client — the Plainlode live signal pull.

Pulls interest-over-time (TIMESERIES) for a list of query terms and returns one
TermSeries per term. Scrapingdog allows up to 5 queries per TIMESERIES call and
charges 5 credits per successful call, so terms are batched in groups of 5.

Data layer only: no LLM calls, no ranking. The ranker consumes TermSeries next.

The API key is read from SCRAPINGDOG_API_KEY, exported into the environment via
.env before running (no python-dotenv).
"""

import dataclasses
import json
import os
import re
import time
from datetime import datetime, timezone

import requests

from backend.scan.models import TermSeries, TrendPoint

ENDPOINT = "https://api.scrapingdog.com/google_trends"
MAX_QUERIES_PER_CALL = 5
TIMEOUT_SECONDS = 45
# Scrapingdog's Trends upstream is occasionally flaky (transient non-200s like a
# 400 "please try again", or a 403 from a concurrency/upstream hiccup on a funded
# account). Retry the live pull a few times before giving up and serving the
# snapshot.
MAX_LIVE_ATTEMPTS = 3        # 1 initial attempt + up to 2 retries
RETRY_DELAY_SECONDS = 1.5    # short pause between live-pull retries

# Snapshot fallback: real prior pulls cached to disk so the demo survives when
# Scrapingdog is out of credits or erroring. These are never fabricated; a
# snapshot only ever holds data from a prior successful live pull.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SNAPSHOT_DIR = os.path.join(_REPO_ROOT, "data", "snapshots")
LIVE_SOURCE = "scrapingdog_live"
SNAPSHOT_SOURCE = "scrapingdog_snapshot"
NO_DATA_SOURCE = "none"


def _batched(items, size):
    """Yield successive `size`-length chunks of `items`."""
    for start in range(0, len(items), size):
        yield items[start:start + size]


def _fetch_batch(api_key, queries, geo):
    """Pull one TIMESERIES call for up to 5 queries. Returns list[TermSeries].

    Transient failures (network error, any non-200 including a flaky 400 "please
    try again" or a 403 concurrency/upstream hiccup, or a non-JSON body) are
    retried up to MAX_LIVE_ATTEMPTS times with a short delay. If every attempt
    fails, or the data is empty, the batch is skipped (empty list) so the caller
    can fall back to the snapshot.
    """
    params = {
        "api_key": api_key,
        "query": ",".join(queries),
        "data_type": "TIMESERIES",
        "geo": geo,
    }

    body = None
    for attempt in range(1, MAX_LIVE_ATTEMPTS + 1):
        try:
            resp = requests.get(ENDPOINT, params=params, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            print(f"[trends_client] attempt {attempt}/{MAX_LIVE_ATTEMPTS} "
                  f"request error for {queries}: {exc}")
        else:
            if resp.status_code == 200:
                try:
                    body = resp.json()
                    print(f"[trends_client] attempt {attempt}/{MAX_LIVE_ATTEMPTS} "
                          f"live pull OK for {queries}")
                    break
                except ValueError:
                    print(f"[trends_client] attempt {attempt}/{MAX_LIVE_ATTEMPTS} "
                          f"non-JSON body for {queries}: {resp.text[:180]}")
            else:
                # All non-200s are retried, including 403: on a funded account a
                # 403 is a transient concurrency or upstream issue, not a hard
                # credit limit.
                print(f"[trends_client] attempt {attempt}/{MAX_LIVE_ATTEMPTS} "
                      f"HTTP {resp.status_code} for {queries}: {resp.text[:180]}")
        if attempt < MAX_LIVE_ATTEMPTS:
            time.sleep(RETRY_DELAY_SECONDS)

    if body is None:
        print(f"[trends_client] all {MAX_LIVE_ATTEMPTS} attempts failed for "
              f"{queries}, skipping batch")
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


# --- snapshot fallback -------------------------------------------------------

def _normalize_key(name):
    """Slugify a category or seed-set name into a filesystem-safe snapshot key."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(name).strip().lower()).strip("-")
    return slug or "unnamed"


def _seed_key(queries):
    """Snapshot key derived from the seed set when no category key is given."""
    return "seeds-" + _normalize_key("-".join(sorted(queries)))


def _snapshot_path(key):
    return os.path.join(SNAPSHOT_DIR, f"{key}.json")


def _save_snapshot(key, series_list, geo):
    """Write a successful live pull to the snapshot for `key` (most recent wins)."""
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    envelope = {
        "key": key,
        "geo": geo,
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "series": [dataclasses.asdict(s) for s in series_list],
    }
    with open(_snapshot_path(key), "w", encoding="utf-8") as fh:
        json.dump(envelope, fh, indent=2)


def _load_snapshot(key):
    """Load the snapshot for `key` as list[TermSeries], or [] if none/unreadable."""
    path = _snapshot_path(key)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            envelope = json.load(fh)
    except (ValueError, OSError):
        return []
    out = []
    for s in envelope.get("series", []):
        points = [
            TrendPoint(
                date=p.get("date", ""),
                timestamp=int(p.get("timestamp", 0) or 0),
                value=int(p.get("value", 0) or 0),
            )
            for p in s.get("points", [])
        ]
        out.append(
            TermSeries(query=s.get("query", ""), geo=s.get("geo", ""), points=points)
        )
    return out


def fetch_with_snapshot(queries, geo="US", key=None):
    """Live pull with a snapshot fallback. Returns (list[TermSeries], source).

    On a successful live pull, refresh the snapshot for `key` and return the live
    data. On a failed or empty pull (non-200, 403 account-limit, missing key, or
    empty result), serve the most recent matching snapshot if one exists. If
    neither is available, return an empty list and the honest no-data source,
    never fabricated data.

    `key` is a category or seed-set name; it is normalized to a snapshot file.
    """
    snap_key = _normalize_key(key) if key else _seed_key(queries)
    try:
        live = fetch_timeseries(queries, geo)
    except RuntimeError as exc:
        # e.g. SCRAPINGDOG_API_KEY not set (fresh clone): fall back to snapshot.
        print(f"[trends_client] live pull unavailable: {exc}")
        live = []

    if live:
        _save_snapshot(snap_key, live, geo)
        print(f"[trends_client] live pull OK ({len(live)} series); "
              f"snapshot '{snap_key}' refreshed")
        return live, LIVE_SOURCE

    snapshot = _load_snapshot(snap_key)
    if snapshot:
        print(f"[trends_client] live pull failed or empty; serving snapshot "
              f"'{snap_key}' ({len(snapshot)} series)")
        return snapshot, SNAPSHOT_SOURCE

    print(f"[trends_client] live pull failed and no snapshot '{snap_key}'; "
          "returning no data")
    return [], NO_DATA_SOURCE


if __name__ == "__main__":
    # Running this captures/refreshes the back-to-school demo snapshot from a
    # real live pull (when Scrapingdog credits are available) and prints whether
    # the data came from live or a snapshot.
    seeds = [
        "school supplies",
        "lunch box",
        "pencil case",
        "kids backpack",
        "dorm bedding",
    ]
    series_list, source = fetch_with_snapshot(seeds, geo="US", key="back to school")
    print(f"source: {source}")
    for series in series_list:
        last = series.points[-1].value if series.points else "—"
        print(f"{series.query:20}  points={len(series.points):3}  last={last}")
