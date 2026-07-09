"""Report-voice layer for Plainlode.

Turns a ScanResult into the fixed Plainlode briefing (Findings / Options /
Recommended) in the plain-language decision-first voice. This is a
prompt-engineered call on serverless gpt-oss, NOT a dedicated LoRA deployment:
the same training system prompt plus two gold examples as few-shot, then the
live signal block. Reuses fireworks_client for the defensive gpt-oss parsing.

The briefing is the product, so this fails loud: empty or failed model output
raises rather than returning junk. A second call writes a plain-English
explainer of the briefing for a non-technical store owner; the two are returned
as separate strings so the frontend can render them in distinct UI blocks.

Run from the repo root:  python -m backend.scan.briefing
"""

import json
import os

from backend.scan.fireworks_client import complete
from backend.scan.models import ScanResult

_TRAIN_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "finetune", "train.jsonl"
)

# The training system prompt, plus one runtime line sharpening the kill signal.
# The base voice and format instruction is kept in sync with build_dataset.py.
SYSTEM = (
    "You are Plainlode, a market-intelligence briefing writer for small "
    "e-commerce owners. Write in a plain-spoken, warm, confident voice, and be "
    "decision-first. Output exactly three sections: Findings, Options (two or "
    "three, numbered), and Recommended (one clear call that names the single "
    "live signal that would reverse it). The kill signal in Recommended must "
    "name a concrete, real-world event or condition that would reverse the call, "
    "for example a seasonal peak, a competitor entering, a supply or price "
    "change, or a related term overtaking this one. Do not merely restate that "
    "the trend could flatten or fall. Be specific and grounded in the category. "
    "Some signals include supply data from Amazon (product count, price range, "
    "average rating). When a term shows supply data, reason over BOTH demand and "
    "supply: a rising term with thin or expensive supply is a strong opening; a "
    "rising term with saturated, cheap, well-rated supply is crowded and needs a "
    "differentiated angle such as a bundle, higher quality, or a niche; a falling "
    "term gets cleared regardless of its supply. When supply data is present, let "
    "the Recommended call and the kill signal reflect this demand-meets-supply "
    "read. If a term has no supply data, judge it on demand alone. "
    "Ground everything in the signal you are given. No em dashes. No hype."
)

# Separate system prompt for the plain-English explainer call.
EXPLAINER_SYSTEM = (
    "You explain a market briefing in plain, friendly terms for a small store "
    "owner with no analytics background. Be warm and clear. Explain what the "
    "numbers mean in everyday language, why the recommendation makes sense, and "
    "what to watch for. Do not repeat the briefing verbatim. Keep it to three or "
    "four short sentences. No em dashes, no en dashes, no jargon."
)

# Marker that identifies the gold few-shot anchor in the training file, so it
# stays in sync with the fine-tune dataset instead of being copied here. One
# anchor (not two) keeps the prompt short and the briefing fast.
_FEWSHOT_MARKERS = (
    "school supplies | rising | +26%",   # back-to-school anchor
)


def _strip_dashes(text: str) -> str:
    """Enforce the no-dash brand rule: replace em and en dashes with a comma.

    The model is told not to use them, but this guarantees it. Hyphen-minus is
    left alone (it is part of the signal-line syntax, not a dash).
    """
    out = text.replace(" — ", ", ").replace(" – ", ", ")
    out = out.replace("—", ", ").replace("–", ", ")
    # Tidy artifacts the replacement can introduce.
    return out.replace(" ,", ",").replace(",,", ",").replace("  ", " ")


def _load_fewshot() -> list[tuple[str, str]]:
    """Read the two gold (signal, briefing) anchor pairs from train.jsonl."""
    with open(_TRAIN_PATH, encoding="utf-8") as fh:
        examples = [json.loads(line) for line in fh]
    pairs = []
    for marker in _FEWSHOT_MARKERS:
        match = next(
            (e for e in examples if marker in e["messages"][1]["content"]), None
        )
        if match is None:
            raise RuntimeError(
                f"Few-shot anchor not found in {_TRAIN_PATH} (marker: {marker!r}). "
                "Rebuild the dataset with finetune/build_dataset.py."
            )
        pairs.append((match["messages"][1]["content"], match["messages"][2]["content"]))
    return pairs


def _fmt_supply(s: dict) -> str:
    """Format a supply dict plainly for the signal block, e.g.
    '~240 products, price $3-$18 median $9, avg rating 4.3'. Skips missing parts."""
    parts = []
    if isinstance(s.get("product_count"), int):
        parts.append(f"~{s['product_count']:,} products")
    lo, mid, hi = s.get("price_min"), s.get("price_median"), s.get("price_max")
    if lo is not None and hi is not None:
        med = f" median ${mid:g}" if mid is not None else ""
        parts.append(f"price ${lo:g}-${hi:g}{med}")
    if s.get("avg_rating") is not None:
        parts.append(f"avg rating {s['avg_rating']:g}")
    return ", ".join(parts)


def _finding_lines(scan_result: ScanResult) -> list[str]:
    """One '- query | direction | slope%' line per ranked above-floor finding,
    with a ' | supply: ...' tail when supply data is attached."""
    above = sorted(
        (f for f in scan_result.findings if not f.low_volume), key=lambda f: f.rank
    )
    lines = []
    for f in above:
        line = f"- {f.query} | {f.direction} | {round(f.slope * 100):+d}%"
        if f.supply:
            supply = _fmt_supply(f.supply)
            if supply:
                line += f" | supply: {supply}"
        lines.append(line)
    return lines


def _strip_signal_echo(text: str) -> str:
    """Drop any echoed signal block by slicing from the first 'Findings'.

    Some runs prepend the Category/Signal block before the briefing. Anchor on
    the 'Findings' section header (colon optional, since the model sometimes
    drops it) and keep only from there. If it is absent, leave the text unchanged
    rather than risk eating real content. The signal block never contains the
    word 'Findings', so this reliably targets the section header.
    """
    idx = text.find("Findings")
    return text[idx:] if idx != -1 else text


def _render_signal_block(scan_result: ScanResult) -> str:
    """Render the ranked above-floor findings into the training signal format."""
    lines = [f"Category: {scan_result.category}", "Signal:"] + _finding_lines(scan_result)
    return "\n".join(lines)


def _build_prompt(signal_block: str, fewshot: list[tuple[str, str]]) -> str:
    """Assemble system instruction + few-shot pairs + the live signal turn.

    fireworks_client.complete sends a single user turn, so the three parts are
    folded into one prompt string.
    """
    parts = [SYSTEM, "", "Here is an example of the exact format and voice."]
    for i, (user, assistant) in enumerate(fewshot, start=1):
        parts += [f"\nExample {i}", user, "", assistant]
    parts += ["\nNow write the briefing for this signal.", signal_block]
    return "\n".join(parts)


def write_briefing(scan_result: ScanResult) -> str:
    """Turn a ScanResult into the fixed Plainlode briefing text.

    Raises RuntimeError on empty or failed model output; the briefing is the
    product, so it fails loud rather than returning junk.
    """
    signal_block = _render_signal_block(scan_result)
    prompt = _build_prompt(signal_block, _load_fewshot())

    # Cap at 700 with low reasoning effort: enough for the three sections, and it
    # bounds generation time so the scan stays comfortably under the gate. Low
    # effort is what makes 700 sufficient — otherwise gpt-oss spends the budget
    # reasoning and truncates the briefing. The 12s timeout means a Fireworks slow
    # spell fails fast (raises -> 502) rather than hanging up to the old 45s.
    text = complete(prompt, max_tokens=700, temperature=0.3, reasoning_effort="low", timeout=12)
    if not text or not text.strip():
        raise RuntimeError(
            "Briefing model returned empty output. Check FIREWORKS_MODEL "
            "(serverless gpt-oss) and the API key, then retry."
        )
    # Echo strip first (some runs prepend the signal block), then the dash guard
    # so the briefing holds the no-dash brand rule too.
    return _strip_dashes(_strip_signal_echo(text.strip()))


def write_explainer(scan_result: ScanResult, briefing: str) -> str:
    """Write a plain-English explainer of the briefing for a non-technical owner.

    A second serverless call, given the category, the ranked findings, and the
    briefing text as context. Warmer read (temperature 0.4). Fails loud on empty
    output and runs the dash guard so the no-dash brand rule holds.
    """
    parts = [
        EXPLAINER_SYSTEM, "",
        f"Category: {scan_result.category}",
        "Findings:",
        *_finding_lines(scan_result),
        "",
        "Briefing:",
        briefing,
        "",
        "Now write the plain-English explainer.",
    ]
    prompt = "\n".join(parts)

    text = complete(prompt, max_tokens=1024, temperature=0.4, reasoning_effort="low")
    if not text or not text.strip():
        raise RuntimeError(
            "Explainer model returned empty output. Check FIREWORKS_MODEL "
            "(serverless gpt-oss) and the API key, then retry."
        )
    return _strip_dashes(text.strip())


if __name__ == "__main__":
    from backend.scan.scan import run_briefing

    seeds = ["school supplies", "lunch box", "pencil case", "kids backpack", "dorm bedding"]
    scan_result, briefing, explainer = run_briefing(seeds, category="back to school")

    print(f"category:  {scan_result.category}")
    print(f"pulled_at: {scan_result.pulled_at}")
    print()
    print(f"{'rank':>4}  {'query':20}  {'direction':9}  {'slope':>8}")
    for f in sorted((f for f in scan_result.findings if not f.low_volume), key=lambda f: f.rank):
        print(f"{f.rank:>4}  {f.query:20}  {f.direction:9}  {f.slope * 100:>7.1f}%")
    low = [f for f in scan_result.findings if f.low_volume]
    if low:
        print("below volume floor (excluded):")
        for f in low:
            print(f"      {f.query:20}  {f.direction:9}  {f.slope * 100:>7.1f}%")

    print("\n" + "=" * 64)
    print("BRIEFING")
    print("=" * 64)
    print(briefing)

    print("\n" + "=" * 64)
    print("PLAIN-ENGLISH EXPLAINER")
    print("=" * 64)
    print(explainer)
    print("=" * 64)
