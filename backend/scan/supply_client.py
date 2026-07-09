"""OpenWeb Ninja Amazon supply signal — a second live source that enriches the
scan with supply and pricing data.

This is a parallel layer. It NEVER raises and returns None on any problem
(missing key, timeout, non-200, off-shape or empty response), so the briefing
runs demand-only exactly as before when supply data is unavailable.
"""

import os
import re
import statistics

import requests

ENDPOINT = "https://api.openwebninja.com/realtime-amazon-data/search"
TIMEOUT_SECONDS = 8


def _parse_price(raw) -> float | None:
    """'$7.50' / '$1,234.56' -> float; None if unparseable."""
    if not isinstance(raw, str):
        return None
    m = re.search(r"\d+(?:\.\d+)?", raw.replace(",", ""))
    return float(m.group()) if m else None


def _parse_rating(raw) -> float | None:
    """'4.8' -> 4.8 (0-5); None if unparseable/out of range."""
    try:
        r = float(raw)
    except (TypeError, ValueError):
        return None
    return r if 0 <= r <= 5 else None


def fetch_supply(term: str) -> dict | None:
    """Look up Amazon supply signal for a term. Returns a compact dict, or None.

    dict shape: {term, product_count, price_min, price_median, price_max,
    avg_rating}. Never raises.
    """
    api_key = os.environ.get("OPENWEBNINJA_API_KEY", "")
    if not api_key:
        return None

    try:
        resp = requests.get(
            ENDPOINT,
            headers={"x-api-key": api_key},
            params={"query": term, "country": "US"},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        print(f"[supply_client] request error for {term!r}: {exc}")
        return None

    if resp.status_code != 200:
        print(f"[supply_client] HTTP {resp.status_code} for {term!r}: {resp.text[:150]}")
        return None

    try:
        body = resp.json()
    except ValueError:
        print(f"[supply_client] non-JSON body for {term!r}")
        return None

    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        return None
    products = data.get("products")
    if not isinstance(products, list) or not products:
        return None

    prices = [p for p in (_parse_price(pr.get("product_price"))
                          for pr in products if isinstance(pr, dict)) if p is not None]
    ratings = [r for r in (_parse_rating(pr.get("product_star_rating"))
                           for pr in products if isinstance(pr, dict)) if r is not None]

    # Saturation: total matching products if present, else the sample size.
    product_count = data.get("total_products")
    if not isinstance(product_count, int):
        product_count = len(products)

    return {
        "term": term,
        "product_count": product_count,
        "price_min": round(min(prices), 2) if prices else None,
        "price_median": round(statistics.median(prices), 2) if prices else None,
        "price_max": round(max(prices), 2) if prices else None,
        "avg_rating": round(statistics.mean(ratings), 1) if ratings else None,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_supply("school supplies"), indent=2))
