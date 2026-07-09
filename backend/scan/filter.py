"""Cheap-tier model-filter step for the Plainlode scan.

This is the product's real model call. It asks a Fireworks serverless model
(AMD Instinct) to judge which ranked terms are genuine opportunities for the
category versus noise, and tags each kept term with a one-line reason.

The scan must never crash on the model step: any request failure, empty output,
or JSON parse failure falls back to keeping every finding unchanged.
"""

import json
import os

from backend.scan.fireworks_client import complete
from backend.scan.models import Finding

_PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "prompts", "scan_filter.txt"
)


def _load_template() -> str:
    with open(_PROMPT_PATH, encoding="utf-8") as fh:
        return fh.read()


def _render_findings(findings: list[Finding]) -> str:
    """One line per term: query, direction, slope as a percent."""
    lines = []
    for f in findings:
        lines.append(f"- {f.query} | {f.direction} | slope {f.slope * 100:.1f}%")
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    """Pull the JSON object out of the model text, tolerating fences/prose.

    Returns {} if nothing parses, so the caller falls back to keeping all.
    """
    if not text:
        return {}
    # Fast path: the whole thing is JSON.
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except (ValueError, TypeError):
        pass
    # Slow path: grab the first {...last } span and try that.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        obj = json.loads(text[start:end + 1])
        return obj if isinstance(obj, dict) else {}
    except (ValueError, TypeError):
        return {}


def filter_findings(findings: list[Finding], category: str) -> list[Finding]:
    """Judge each ranked finding as opportunity vs. noise for `category`.

    Kept findings are returned in their original order, each tagged with a
    one-line reason. On any model or parse failure, every finding is kept
    unchanged so the scan never breaks on the model step.
    """
    if not findings:
        return findings

    # Below-floor terms are already flagged as too low-volume to be opportunities.
    # They bypass the model entirely and pass through untouched, so we only spend
    # tokens judging terms that could actually be surfaced.
    above = [f for f in findings if not f.low_volume]
    below = [f for f in findings if f.low_volume]
    if not above:
        return below

    prompt = (
        _load_template()
        .replace("[[CATEGORY]]", category)
        .replace("[[FINDINGS]]", _render_findings(above))
    )

    # gpt-oss and other reasoning models spend tokens thinking before they emit
    # the JSON, so a flat 512 budget truncates the answer once you have a few
    # terms. max_tokens is only a ceiling (billed per token generated), so scale
    # it with the term count and keep a comfortable floor.
    max_tokens = max(1024, 320 * len(above))
    # Filtering is a judgment task, not a creative one. Temperature 0.0 keeps it
    # deterministic so the same seeds keep the same findings every run and the
    # scripted demo is reproducible.
    #
    # Retry up to 3 total attempts on an empty or unparseable response before
    # giving up. A transient model hiccup should not silently flip the scan to
    # keep-all, which would break demo reproducibility.
    results = None
    for attempt in range(1, 4):
        text = complete(prompt, max_tokens=max_tokens, temperature=0.0)
        parsed = _extract_json(text)
        candidate = parsed.get("results") if isinstance(parsed, dict) else None
        if isinstance(candidate, list) and candidate:
            results = candidate
            print(f"[filter] model output parsed on attempt {attempt}/3")
            break
        print(f"[filter] attempt {attempt}/3 returned no usable JSON")
    if results is None:
        print("[filter] all 3 attempts failed, keeping all findings")
        return above + below

    # Map the model's verdicts back to findings by query string.
    verdicts = {}
    for item in results:
        if isinstance(item, dict) and isinstance(item.get("query"), str):
            verdicts[item["query"]] = item

    kept = []
    for f in above:
        verdict = verdicts.get(f.query)
        if verdict is None:
            # Model said nothing about this term; keep it rather than drop blind.
            kept.append(f)
            continue
        if verdict.get("keep", True):
            reason = verdict.get("reason", "")
            f.reason = reason.strip() if isinstance(reason, str) else ""
            kept.append(f)
    # If the model dropped everything, that is almost certainly a bad parse,
    # not a real "nothing here" verdict. Keep all rather than return empty.
    if not kept:
        print("[filter] model dropped every term, keeping all findings")
        return above + below
    return kept + below
