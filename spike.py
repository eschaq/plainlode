#!/usr/bin/env python3
"""
Plainlode day-one spike — SOP Phase 3.3 ("test any data source connections" +
"test Claude/model API connection"). Runs the three gating checks in one pass
and prints a PASS/FAIL summary. Nothing here is Plainlode product code; it is
throwaway verification you run once your credits land.

Checks:
  1. Scrapingdog Google Trends  — interest-over-time pull comes clean (the core signal)
  2. Scrapingdog rising queries  — the "what's rising" data path the Findings beat needs
  3. Fireworks serverless        — cheap-tier base-model call returns on Fireworks/AMD
  4. Kaggle license              — nicapotato reviews set reads CC0/CC-BY (programmatic)

Run:
  export SCRAPINGDOG_API_KEY=...        # from scrapingdog dashboard
  export FIREWORKS_API_KEY=...          # from fireworks.ai
  # optional: export FIREWORKS_MODEL=accounts/fireworks/models/llama-v3p1-8b-instruct
  # Kaggle: have ~/.kaggle/kaggle.json in place (pip install kaggle) OR skip and eyeball
  python spike.py

Each successful Scrapingdog request costs 5 API credits. A full run spends
~15 credits (well under the free allotment).
"""

import os
import sys
import json
import subprocess
import tempfile

try:
    import requests
except ImportError:
    print("Missing dependency. Run: pip install requests")
    sys.exit(1)

# ---- config -----------------------------------------------------------------

SCRAPINGDOG_KEY = os.environ.get("SCRAPINGDOG_API_KEY", "")
FIREWORKS_KEY = os.environ.get("FIREWORKS_API_KEY", "")
FIREWORKS_MODEL = os.environ.get(
    "FIREWORKS_MODEL", "accounts/fireworks/models/llama-v3p1-8b-instruct"
)
KAGGLE_DATASET = "nicapotato/womens-ecommerce-clothing-reviews"
ACCEPTABLE_LICENSES = ("cc0", "cc-by", "cc by", "public domain")

# A realistic e-commerce demo query, not "pizza,burger". This is what a
# Plainlode user's category signal actually looks like.
DEMO_QUERY = "soy candle,candle refill kit"   # multi-query: valid for TIMESERIES only
RISING_QUERY = "soy candle"                    # single query: rising/related is single-query-only

results = []  # (label, status, detail)


def record(label, status, detail=""):
    results.append((label, status, detail))
    tag = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]", "SKIP": "[SKIP]"}[status]
    print(f"{tag} {label}" + (f" — {detail}" if detail else ""))


# ---- check 1 + 2: Scrapingdog -----------------------------------------------

SD_ENDPOINT = "https://api.scrapingdog.com/google_trends"


def _scrapingdog_call(data_type, param_name="query", query=DEMO_QUERY):
    """Docs list the param as 'query' but the cURL example uses 'q'. Caller can
    try both. Returns (ok, json_or_error, status_code)."""
    params = {
        "api_key": SCRAPINGDOG_KEY,
        param_name: query,
        "data_type": data_type,
        "geo": "US",
    }
    try:
        r = requests.get(SD_ENDPOINT, params=params, timeout=45)
    except Exception as e:
        return False, f"request error: {e}", None
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:180]}", r.status_code
    try:
        return True, r.json(), 200
    except Exception:
        return False, f"non-JSON body: {r.text[:180]}", 200


def check_scrapingdog_timeseries():
    if not SCRAPINGDOG_KEY:
        record("Scrapingdog interest-over-time", "SKIP", "SCRAPINGDOG_API_KEY not set")
        return
    ok, body, _ = _scrapingdog_call("TIMESERIES", "query")
    if not ok:
        # docs cURL uses q= ; retry once with that param name
        ok, body, _ = _scrapingdog_call("TIMESERIES", "q")
    if not ok:
        record("Scrapingdog interest-over-time", "FAIL", str(body))
        return
    timeline = (body or {}).get("interest_over_time", {}).get("timeline_data", [])
    if timeline:
        record(
            "Scrapingdog interest-over-time",
            "PASS",
            f"{len(timeline)} timeline points returned for '{DEMO_QUERY}'",
        )
    else:
        record(
            "Scrapingdog interest-over-time",
            "FAIL",
            "200 OK but interest_over_time.timeline_data was empty",
        )


def check_scrapingdog_rising():
    """Scrapingdog documents only TIMESERIES/GEO_MAP/GEO_MAP_0. Rising/related is
    undocumented and the Findings beat leans on it. Two traps avoided here:
    it is single-query-only (use RISING_QUERY, not the two-term DEMO_QUERY), and
    an unknown data_type may be silently ignored and fall back to TIMESERIES,
    which must NOT read as a PASS. Fail loudly so you learn this on day one."""
    if not SCRAPINGDOG_KEY:
        record("Scrapingdog rising queries", "SKIP", "SCRAPINGDOG_API_KEY not set")
        return
    candidates = ["RELATED_QUERIES", "RELATED_TOPICS"]
    fell_back = False
    for dt in candidates:
        ok, body, _ = _scrapingdog_call(dt, "query", query=RISING_QUERY)
        if not ok or not isinstance(body, dict) or not body or "error" in body:
            continue
        keys = list(body.keys())
        rising_key = next(
            (k for k in keys if any(t in k.lower() for t in ("rising", "related", "top"))),
            None,
        )
        if rising_key:
            record(
                "Scrapingdog rising queries",
                "PASS",
                f"data_type={dt} returned '{rising_key}' (keys: {', '.join(keys[:4])})",
            )
            return
        if "interest_over_time" in keys:
            # unknown data_type ignored; API handed back timeseries again
            fell_back = True
    if fell_back:
        record(
            "Scrapingdog rising queries",
            "FAIL",
            "unknown data_type was ignored and fell back to TIMESERIES; no "
            "rising/related field returned. Derive 'rising' from the TIMESERIES slope.",
        )
    else:
        record(
            "Scrapingdog rising queries",
            "FAIL",
            "no rising/related data_type returned usable data (tried "
            + ", ".join(candidates)
            + "). Confirm the correct param with Scrapingdog support, or derive "
            "'rising' yourself from the TIMESERIES slope. The Findings beat depends on this.",
        )


# ---- check 3: Fireworks serverless (AMD) ------------------------------------

FW_ENDPOINT = "https://api.fireworks.ai/inference/v1/chat/completions"


def check_fireworks_serverless():
    if not FIREWORKS_KEY:
        record("Fireworks serverless call", "SKIP", "FIREWORKS_API_KEY not set")
        return
    headers = {
        "Authorization": f"Bearer {FIREWORKS_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": FIREWORKS_MODEL,
        "max_tokens": 32,
        "temperature": 0.2,
        "messages": [
            {"role": "user", "content": "Reply with exactly: plainlode spike ok"}
        ],
    }
    try:
        r = requests.post(FW_ENDPOINT, headers=headers, json=payload, timeout=60)
    except Exception as e:
        record("Fireworks serverless call", "FAIL", f"request error: {e}")
        return
    if r.status_code != 200:
        detail = f"HTTP {r.status_code}: {r.text[:200]}"
        if r.status_code == 404:
            detail += "  (model id may have been deprecated — check the Models page and set FIREWORKS_MODEL)"
        record("Fireworks serverless call", "FAIL", detail)
        return
    try:
        content = r.json()["choices"][0]["message"]["content"].strip()
        record("Fireworks serverless call", "PASS", f"model replied: {content[:60]!r}")
    except Exception as e:
        record("Fireworks serverless call", "FAIL", f"unexpected body shape: {e}")


def check_fireworks_finetune_note():
    """Not a live call — a load-bearing architecture warning. Fireworks
    serverless does NOT serve LoRA add-ons or custom fine-tunes; those require a
    DEDICATED deployment (per-GPU-hour, not free per-token). This hits the core
    'fine-tuned voice on Fireworks' beat, the credit budget, and the deck's
    moat claim. Decide the serving path before you sink LoRA hours."""
    record(
        "Fireworks fine-tune serving",
        "WARN",
        "LoRA fine-tunes need a DEDICATED deployment on Fireworks (serverless "
        "won't serve them). That is per-GPU-hour billing. Confirm the path and "
        "credit burn, or fall back to prompt-engineered voice on a serverless "
        "base model. This is a build decision, not a script result.",
    )


# ---- check 4: Kaggle license ------------------------------------------------


def check_kaggle_license():
    """Programmatically read the dataset license via the Kaggle API instead of
    eyeballing the sidebar. Needs `pip install kaggle` and ~/.kaggle/kaggle.json."""
    tmp = tempfile.mkdtemp()
    try:
        proc = subprocess.run(
            ["kaggle", "datasets", "metadata", "-d", KAGGLE_DATASET, "-p", tmp],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        record(
            "Kaggle license",
            "SKIP",
            "kaggle CLI not installed (pip install kaggle). Manual fallback: "
            "read the License field in the dataset page right sidebar.",
        )
        return
    except Exception as e:
        record("Kaggle license", "SKIP", f"kaggle call failed: {e}. Eyeball the sidebar.")
        return

    meta_path = os.path.join(tmp, "dataset-metadata.json")
    if not os.path.exists(meta_path):
        record(
            "Kaggle license",
            "SKIP",
            f"no metadata written (auth issue?): {proc.stderr.strip()[:160]}. "
            "Eyeball the sidebar.",
        )
        return
    try:
        with open(meta_path) as f:
            meta = json.load(f)
    except Exception as e:
        record("Kaggle license", "SKIP", f"could not parse metadata: {e}")
        return

    licenses = meta.get("info", {}).get("licenses", []) or meta.get("licenses", [])
    names = [l.get("name", "") for l in licenses] if licenses else []
    joined = ", ".join(n for n in names if n) or "(none listed)"
    ok = any(any(a in n.lower() for a in ACCEPTABLE_LICENSES) for n in names)
    if ok:
        record("Kaggle license", "PASS", f"license: {joined}")
    else:
        record(
            "Kaggle license",
            "FAIL",
            f"license reads '{joined}' — not clearly CC0/CC-BY. Swap the corpus "
            "before training (filter Kaggle 'ecommerce reviews' by CC0/CC-BY).",
        )


# ---- run --------------------------------------------------------------------


def main():
    print("Plainlode day-one spike  (SOP Phase 3.3)\n" + "=" * 44)
    check_scrapingdog_timeseries()
    check_scrapingdog_rising()
    check_fireworks_serverless()
    check_fireworks_finetune_note()
    check_kaggle_license()

    print("\n" + "=" * 44 + "\nSUMMARY")
    hard_fail = False
    for label, status, _ in results:
        print(f"  {status:4}  {label}")
        if status == "FAIL":
            hard_fail = True
    print("=" * 44)
    if hard_fail:
        print("At least one hard check FAILED. Trigger the snapshot fallback for the "
              "live source if it's the Scrapingdog pull, and resolve before build hours.")
        sys.exit(1)
    print("No hard failures. Address any WARN before locking the core architecture.")
    sys.exit(0)


if __name__ == "__main__":
    main()
