"""Build the Plainlode report-voice fine-tune dataset.

This teaches the LoRA a VOICE and a FORMAT, category-agnostic. It does not teach
facts. Facts stay live via the scan. Every training example pairs a made-up
market signal (category + a few terms, each with direction and slope) with the
gold plain-language briefing that signal should produce: three sections,
Findings / Options / Recommended, where the recommendation names the one live
signal that would reverse it.

No external corpus, no Kaggle download. Categories and seed terms are defined in
code, spread across fifteen distinct verticals so the voice generalizes.

Output is finetune/train.jsonl in Fireworks SFT chat format, one JSON object per
line: {"messages": [system, user, assistant]}.

Run from the repo root:  python -m finetune.build_dataset
"""

import json
import os
import random

OUT_PATH = "finetune/train.jsonl"
TARGET_EXAMPLES = 135
ALL_FLAT_SHARE = 18  # honest "hold, nothing is clearly rising yet" cases

random.seed(42)  # reproducible builds

SYSTEM = (
    "You are Plainlode, a market-intelligence briefing writer for small "
    "e-commerce owners. Write in a plain-spoken, warm, confident voice, and be "
    "decision-first. Output exactly three sections: Findings, Options (two or "
    "three, numbered), and Recommended (one clear call that names the single "
    "live signal that would reverse it). Ground everything in the signal you are "
    "given. No em dashes. No hype."
)

# Fifteen verticals. Each pool holds five or six realistic seed terms so a signal
# can sample three to five of them; `season`, when set, unlocks seasonal reversal
# language; `themes` feed the interpretation sentence.
CATEGORIES = {
    "back to school": {
        "terms": ["school supplies", "lunch box", "pencil case", "kids backpack",
                  "dorm bedding", "planner"],
        "themes": ["the core of the season", "back-to-class essentials", "the ramp into the school year"],
        "season": {"peak": "late August", "next": "fall"},
    },
    "supplements": {
        "terms": ["magnesium glycinate", "creatine", "electrolyte powder",
                  "ashwagandha", "protein powder", "fish oil"],
        "themes": ["sleep and recovery routines", "everyday wellness stacks", "performance basics"],
        "season": None,
    },
    "home goods": {
        "terms": ["throw pillow", "area rug", "storage bins", "curtains",
                  "throw blanket", "floor lamp"],
        "themes": ["seasonal refresh pieces", "cozy home updates", "small-space upgrades"],
        "season": None,
    },
    "kitchen": {
        "terms": ["air fryer", "cast iron skillet", "chef knife", "food storage set",
                  "mixing bowls", "immersion blender"],
        "themes": ["everyday cooking upgrades", "batch-cooking gear", "counter-top essentials"],
        "season": None,
    },
    "outdoor and garden": {
        "terms": ["raised garden bed", "drip irrigation kit", "garden hose",
                  "potting soil", "patio umbrella", "solar path lights"],
        "themes": ["the spring planting push", "warm-weather yard projects", "outdoor-season setup"],
        "season": {"peak": "midsummer", "next": "fall"},
    },
    "pet supplies": {
        "terms": ["dog harness", "cat tree", "slow feeder bowl", "dental chews",
                  "nail grinder", "litter mat"],
        "themes": ["comfort-first pet gear", "everyday care basics", "training and enrichment"],
        "season": None,
    },
    "fitness": {
        "terms": ["adjustable dumbbells", "resistance bands", "yoga mat",
                  "kettlebell", "jump rope", "foam roller"],
        "themes": ["home-gym building", "the new-year training push", "low-space workout gear"],
        "season": {"peak": "January", "next": "spring"},
    },
    "beauty and skincare": {
        "terms": ["vitamin c serum", "retinol cream", "hyaluronic acid",
                  "mineral sunscreen", "lip mask", "gua sha"],
        "themes": ["barrier-first routines", "the shift toward gentler actives", "everyday glow basics"],
        "season": None,
    },
    "baby": {
        "terms": ["baby monitor", "swaddle blanket", "bottle warmer",
                  "high chair", "diaper bag", "teething toy"],
        "themes": ["new-parent essentials", "nursery basics", "everyday care gear"],
        "season": None,
    },
    "home coffee": {
        "terms": ["espresso machine", "milk frother", "drip coffee maker",
                  "pour over kettle", "burr grinder", "cold brew maker"],
        "themes": ["cafe-style setups at home", "trading up from basic brewers", "the home-barista push"],
        "season": None,
    },
    "home office": {
        "terms": ["standing desk", "ergonomic chair", "monitor arm",
                  "desk mat", "laptop stand", "cable organizer"],
        "themes": ["comfort-first desk setups", "the work-from-home upgrade", "ergonomic basics"],
        "season": None,
    },
    "auto accessories": {
        "terms": ["dash cam", "car phone mount", "seat covers",
                  "trunk organizer", "tire inflator", "floor mats"],
        "themes": ["everyday driver upgrades", "protect-and-organize basics", "road-trip prep gear"],
        "season": None,
    },
    "phone accessories": {
        "terms": ["magsafe charger", "phone grip", "screen protector",
                  "clear case", "car charger", "power bank"],
        "themes": ["the new-model upgrade wave", "protect-and-charge basics", "everyday carry gear"],
        "season": None,
    },
    "collectibles": {
        "terms": ["enamel pins", "card sleeves", "display case",
                  "vinyl figures", "coin album", "sticker sheets"],
        "themes": ["collection-care gear", "display and storage basics", "the hobby-growth push"],
        "season": None,
    },
    "seasonal decor": {
        "terms": ["string lights", "wreath", "artificial garland",
                  "pillow covers", "table runner", "candle holders"],
        "themes": ["the holiday setup push", "seasonal-refresh pieces", "the decorate-early wave"],
        "season": {"peak": "the holidays", "next": "the new year"},
    },
}

# --- synonym pools for phrasing variety -------------------------------------
RISE_WORDS = ["climbing", "rising", "picking up", "gaining", "trending up", "heating up"]
FALL_WORDS = ["cooling", "falling", "sliding", "softening", "fading", "slipping"]
TIMEFRAMES = ["over the last two months", "over the past eight weeks", "in recent weeks",
              "over the last two cycles", "this cycle"]
UP_PHRASES = ["up about {n} percent", "up roughly {n} percent", "higher by about {n} percent"]

LEAD_VERBS = ["Stock", "Feature", "Lead with", "Prioritize", "Push"]
FEATURE_PHRASES = ["feature it up front", "photograph it front and center",
                   "give it the top slot", "put it at the top of the page"]
LEAD_NOUNS = ["lead category", "hero product", "front-of-store feature", "headline pick"]

CALL_REASONS = [
    "Demand is rising and you have runway before the peak.",
    "It rides demand that is already climbing and fits where the category is heading.",
    "The slope is up and the category is with you.",
    "You are early enough to stock before it peaks.",
    "The trend is moving your way and you can act before it is crowded.",
]
MULTI_REASONS = [
    "Two related terms are rising together, which is a stronger signal than one moving alone.",
    "Two terms climbing at once points to a real shift, not noise in a single query.",
    "When neighboring terms rise together, the demand is broad, not a one-term blip.",
]
KILL_PHRASES = ["The one signal that kills this call is",
                "The signal that would kill this call is",
                "The one live signal that reverses this is"]
FLIP_ACTIONS = [
    "Once the slope rolls over, stop restocking and clear through.",
    "If that flips, move your feature spend.",
    "When it turns, pull back and sell down what is left.",
    "Watch it weekly and cut fast if it rolls over.",
]
HOLD_REASONS = [
    "There is no edge in committing stock to a flat market.",
    "Spending into a flat signal just ties up cash.",
    "Nothing here justifies a big bet this cycle.",
    "A flat market is a cash-preservation window, not a buying one.",
]


# --- signal construction ----------------------------------------------------

def direction_for(slope):
    if slope >= 15:
        return "rising"
    if slope <= -15:
        return "falling"
    return "flat"


def make_signal(pool, all_flat):
    """Return a list of (term, direction, slope), three to five terms.

    A normal signal guarantees at least one clear riser so there is a call to
    make. An all-flat signal keeps every term inside the flat band.
    """
    k = random.randint(3, 5)
    terms = random.sample(pool["terms"], min(k, len(pool["terms"])))
    if all_flat:
        return [(t, "flat", random.randint(-13, 13)) for t in terms]

    signal = [(terms[0], "rising", random.randint(16, 40))]
    for term in terms[1:]:
        slope = random.choice([
            random.randint(15, 38),    # another riser
            random.randint(-13, 13),   # flat
            random.randint(-44, -16),  # faller
            random.randint(-44, -16),  # weight fallers a touch heavier
        ])
        signal.append((term, direction_for(slope), slope))
    random.shuffle(signal)
    return signal


def render_user(category, signal):
    lines = [f"Category: {category}", "Signal:"]
    for term, direction, slope in signal:
        lines.append(f"- {term} | {direction} | {slope:+d}%")
    return "\n".join(lines)


# --- gold briefing construction ---------------------------------------------

def cap(text):
    return text[0].upper() + text[1:] if text else text


def listify(items):
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def are(items):
    return "is" if len(items) == 1 else "are"


def render_findings(pool, risers, flats, fallers):
    top_term, top_slope = risers[0]
    rise_word = random.choice(RISE_WORDS)
    up = random.choice(UP_PHRASES).format(n=top_slope)
    theme = random.choice(pool["themes"])

    if random.random() < 0.5:
        head = f"Demand for {top_term} is {rise_word}, {up} {random.choice(TIMEFRAMES)}"
    else:
        head = f"{cap(top_term)} demand is {rise_word}, {up}"

    others = [t for t, _ in risers[1:]]
    if len(others) == 1:
        head += f", with {others[0]} climbing alongside it"
    elif len(others) >= 2:
        head += f", with {listify(others)} climbing too"

    if fallers:
        faller_terms = [t for t, _ in fallers]
        lead_in = "related terms like " if random.random() < 0.5 else ""
        tail = f", while {lead_in}{listify(faller_terms)} {are(faller_terms)} {random.choice(FALL_WORDS)}."
    elif flats:
        flat_terms = [t for t, _ in flats]
        tail = f", while {listify(flat_terms)} {are(flat_terms)} holding steady."
    else:
        tail = ", and the rest of the category is climbing with it."

    interp = f"Buyers are leaning toward {theme}."
    return f"Findings: {head}{tail} {interp}"


def render_options(risers, flats, fallers):
    top_term = risers[0][0]
    options = [
        f"{random.choice(LEAD_VERBS)} {top_term} now as your "
        f"{random.choice(LEAD_NOUNS)} and {random.choice(FEATURE_PHRASES)}."
    ]
    # Second option: bundle a co-rising term, bundle a flat, or clear a faller.
    if len(risers) >= 2:
        options.append(
            f"Bundle {risers[1][0]} with {top_term} to raise basket size while both are rising."
        )
    elif flats:
        options.append(
            f"Bundle {top_term} with {flats[0][0]}, which is holding steady, to lift basket size."
        )
    elif fallers:
        options.append(
            f"Reprice slow {fallers[0][0]} stock to clear it before it drops further."
        )
    else:
        options.append(f"Widen the range around {top_term} while the whole category runs hot.")
    # Third option (sometimes omitted, to vary option count): test, hold, or clear.
    third_pool = [
        f"Test one {top_term} style before committing to a full range.",
        "Hold and watch one more cycle if cash is tight.",
    ]
    if fallers:
        third_pool.append(f"Mark down {fallers[-1][0]} now and clear it before it slides further.")
    if random.random() < 0.8:
        options.append(random.choice(third_pool))
    return options


def render_recommended(pool, risers):
    top_term = risers[0][0]
    call = random.choice([
        f"lead with {top_term}", f"stock {top_term}", f"feature {top_term}",
        f"make {top_term} your lead", f"launch a small {top_term} line",
    ])
    kill = random.choice(KILL_PHRASES)

    if len(risers) >= 2:
        reason = random.choice(MULTI_REASONS)
        reversal = f"{top_term} and {risers[1][0]} slopes flattening in the same cycle"
        flip = "If both cool at once, the wave is passing and you hold."
    else:
        reason = random.choice(CALL_REASONS)
        season = pool.get("season")
        if season and random.random() < 0.6:
            reversal = f"the seasonal top in {season['peak']}"
            flip = (f"If searches shift into {season['next']}, move your feature spend."
                    if random.random() < 0.5 else random.choice(FLIP_ACTIONS))
        else:
            reversal = random.choice([
                "the slope rolling over for two straight weeks",
                f"{top_term} flattening while another term starts to climb",
                "a broad pullback across the category",
            ])
            flip = random.choice(FLIP_ACTIONS)

    return f"Recommended: {call} now. {reason} {kill} {reversal}. {flip}"


def render_hold(category, signal):
    terms = [t for t, _, _ in signal]
    candidate = random.choice(terms)
    findings = (
        f"Findings: Nothing in {category} is clearly moving right now. "
        f"{cap(listify(terms))} are all holding within a few points of flat. "
        f"There is no strong directional signal this cycle."
    )
    options = [
        "Hold your current mix and watch one more cycle.",
        "Use the quiet window to clear slow stock and tidy your listings.",
        f"Prep a {candidate} feature now so you can move the day a signal appears.",
    ]
    recommended = (
        f"Recommended: hold, nothing is clearly rising yet. {random.choice(HOLD_REASONS)} "
        f"The signal that would change this call is {candidate} breaking upward and holding. "
        f"Once one term's slope turns up for two straight cycles, move on it."
    )
    return findings, options, recommended


def number(options):
    return [f"{i}. {opt}" for i, opt in enumerate(options, start=1)]


def build_assistant(category, pool, signal):
    if all(d == "flat" for _, d, _ in signal):
        findings, options, recommended = render_hold(category, signal)
    else:
        risers = sorted([(t, s) for t, d, s in signal if d == "rising"],
                        key=lambda x: x[1], reverse=True)
        flats = [(t, s) for t, d, s in signal if d == "flat"]
        fallers = sorted([(t, s) for t, d, s in signal if d == "falling"], key=lambda x: x[1])
        findings = render_findings(pool, risers, flats, fallers)
        options = render_options(risers, flats, fallers)
        recommended = render_recommended(pool, risers)

    lines = [findings, "Options:"] + number(options) + [recommended]
    return "\n".join(lines)


def make_example(category, pool, signal, assistant_text=None):
    assistant = assistant_text if assistant_text is not None else build_assistant(category, pool, signal)
    return {"messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": render_user(category, signal)},
        {"role": "assistant", "content": assistant},
    ]}


# --- the two verbatim voice anchors (options numbered to match the format) ---

def anchor_examples():
    a_signal = [("school supplies", "rising", 26), ("lunch box", "flat", 13),
                ("pencil case", "falling", -23), ("kids backpack", "falling", -41)]
    a_assistant = (
        "Findings: Demand for school supplies is climbing, up about 26 percent over the last "
        "two months, while related terms like kids backpack and pencil case are already falling. "
        "The season is ramping and attention is moving to the core category.\n"
        "Options:\n"
        "1. Stock school supplies now as your lead category and feature it up front.\n"
        "2. Bundle school supplies with lunch boxes, which are holding steady, to lift basket size.\n"
        "3. Hold and watch one more cycle if cash is tight.\n"
        "Recommended: lead with school supplies now. Demand is rising and you have runway before "
        "the peak. The one signal that kills this call is the seasonal top in late August. Once the "
        "slope rolls over, stop restocking and clear through."
    )
    b_signal = [("espresso machine", "rising", 22), ("milk frother", "rising", 14),
                ("drip coffee maker", "falling", -17)]
    b_assistant = (
        "Findings: Home espresso demand is rising, up about 22 percent, with milk frothers "
        "climbing alongside it, while drip coffee makers are cooling. Buyers are trading up toward "
        "cafe-style setups at home.\n"
        "Options:\n"
        "1. Lead with espresso machines and feature them as your hero product.\n"
        "2. Bundle a frother with each machine to raise basket size while both are rising.\n"
        "3. Discount drip stock now to clear it before it falls further.\n"
        "Recommended: make espresso machines your lead now. Two related terms are rising together, "
        "which is a stronger signal than one moving alone. The signal that would kill this call is "
        "espresso and frother slopes flattening in the same cycle. If both cool at once, the "
        "trade-up wave is passing and you hold."
    )
    return [
        make_example("back to school", None, a_signal, a_assistant),
        make_example("home coffee", None, b_signal, b_assistant),
    ]


def main():
    examples = anchor_examples()

    names = list(CATEGORIES.keys())
    n_generate = TARGET_EXAMPLES - len(examples)
    # Even spread: round-robin the categories across the generated slots.
    plan = [names[i % len(names)] for i in range(n_generate)]
    # Mark a share of slots as all-flat, spread across the plan.
    flat_idx = set(random.sample(range(n_generate), ALL_FLAT_SHARE))

    for i, category in enumerate(plan):
        pool = CATEGORIES[category]
        signal = make_signal(pool, all_flat=(i in flat_idx))
        examples.append(make_example(category, pool, signal))

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(json.dumps(ex, ensure_ascii=False) + "\n")

    flat_count = sum(
        1 for ex in examples if "nothing is clearly rising yet" in ex["messages"][2]["content"]
    )
    per_cat = {n: sum(1 for ex in examples if ex["messages"][1]["content"].startswith(f"Category: {n}"))
               for n in names}
    spread = ", ".join(f"{n}:{c}" for n, c in per_cat.items())
    print(f"categories: {len(names)} verticals")
    print(f"spread: {spread}")
    print(f"wrote {len(examples)} examples to {OUT_PATH} ({flat_count} honest-hold cases)")


if __name__ == "__main__":
    main()
