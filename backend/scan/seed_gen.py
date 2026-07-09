"""Generate live-scan seeds for a category using the cheap-tier model, with a
static helper as the fallback.

This is a v2 parallel addition. It must NEVER break the scan: any failure,
timeout, empty or malformed model output falls back to the static seed helper.
The back-to-school demo stays deterministic by using the curated known-good set
(it never touches the model).
"""

import json
import re

from backend.scan.fireworks_client import complete

# Curated known-good seeds. Categories listed here bypass the model entirely so
# the scripted demo is deterministic.
DEFAULT_SEEDS = {
    "back to school": ["school supplies", "lunch box", "pencil case",
                       "kids backpack", "dorm bedding"],
}

# Short timeout: a slow seed call should fall back fast, not eat the latency
# budget the rest of the scan needs.
SEED_TIMEOUT_SECONDS = 8


def seeds_for_category(category: str) -> list[str]:
    """Static fallback seed set (the v1 helper). Never calls a model."""
    known = DEFAULT_SEEDS.get(category.strip().lower())
    if known:
        return list(known)
    base = category.strip()
    return [base, f"{base} kit", f"best {base}"]


def _build_prompt(category: str, n: int) -> str:
    return (
        "You are a product-catalog assistant for a small e-commerce store owner.\n"
        f'For the category "{category}", return exactly {n} common, high-volume, '
        "searchable product terms a shopper would actually type. Use real product "
        "nouns, 1 to 4 words each. No sentences, no brand names, no explanations.\n\n"
        'Example: category "pet supplies" -> '
        '{"seeds": ["dog food", "cat litter", "dog toys", "flea treatment", "aquarium filter"]}\n\n'
        "Return STRICT JSON ONLY, no prose, no markdown, no code fences, exactly:\n"
        '{"seeds": ["term", "term", ...]}'
    )


def _extract_json(text: str) -> dict:
    """Pull a JSON object out of the model text, tolerating fences/prose."""
    if not text:
        return {}
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except (ValueError, TypeError):
        pass
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        obj = json.loads(text[start:end + 1])
        return obj if isinstance(obj, dict) else {}
    except (ValueError, TypeError):
        return {}


def _valid_seed(s) -> bool:
    """A seed is a short product noun phrase: 1-4 words, no sentence punctuation."""
    if not isinstance(s, str):
        return False
    t = s.strip()
    if not t or len(t) > 40:
        return False
    if re.search(r"[.!?;:]", t):  # sentences / lists, not a term
        return False
    words = t.split()
    return 1 <= len(words) <= 4


def generate_seeds(category: str, n: int = 5) -> tuple[list[str], str]:
    """Return (seeds, source) where source is "model" or "fallback".

    Curated categories (e.g. back to school) return the known-good set as
    "fallback" without calling the model, keeping the demo deterministic. For
    everything else it asks the cheap-tier model and validates the result,
    falling back to the static helper on any problem. Never raises.
    """
    fallback = seeds_for_category(category)

    # Deterministic path for curated demo categories.
    if category.strip().lower() in DEFAULT_SEEDS:
        return fallback, "fallback"

    try:
        text = complete(
            _build_prompt(category, n),
            max_tokens=400,
            temperature=0.2,
            reasoning_effort="low",
            timeout=SEED_TIMEOUT_SECONDS,
        )
    except Exception as exc:  # never let seed generation break the scan
        print(f"[seed_gen] model call failed for {category!r}: {exc}; using fallback")
        return fallback, "fallback"

    raw = _extract_json(text).get("seeds")
    if not isinstance(raw, list):
        print(f"[seed_gen] no usable seeds for {category!r}; using fallback")
        return fallback, "fallback"

    seen, seeds = set(), []
    for item in raw:
        if _valid_seed(item):
            key = item.strip().lower()
            if key not in seen:
                seen.add(key)
                seeds.append(item.strip())

    if len(seeds) < n:
        print(f"[seed_gen] only {len(seeds)}/{n} valid seeds for {category!r}; using fallback")
        return fallback, "fallback"

    return seeds[:n], "model"
