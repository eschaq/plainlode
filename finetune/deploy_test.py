"""Deploy the fine-tuned Plainlode voice model and run one real test briefing.

Brings up a dedicated on-demand deployment of the fine-tuned model (live-merge,
single model), sends one signal block in the exact training format, prints the
returned briefing in full, then prints the deployment id and the exact teardown
command. It does NOT tear down; we read the briefing first and tear down by hand
the moment it reads right, to conserve credits.

Run from the repo root:  python -m finetune.deploy_test
"""

import os

from fireworks import LLM

# The exact system prompt used in training (kept in sync with build_dataset.py).
SYSTEM = (
    "You are Plainlode, a market-intelligence briefing writer for small "
    "e-commerce owners. Write in a plain-spoken, warm, confident voice, and be "
    "decision-first. Output exactly three sections: Findings, Options (two or "
    "three, numbered), and Recommended (one clear call that names the single "
    "live signal that would reverse it). Ground everything in the signal you are "
    "given. No em dashes. No hype."
)

MODEL = "accounts/eschachter/models/plainlode-voice-v2"
DEPLOY_ID = "plainlode-voice-v2-test"

# One real signal block, exact training format (category: back to school).
USER_SIGNAL = (
    "Category: back to school\n"
    "Signal:\n"
    "- school supplies | rising | +26%\n"
    "- lunch box | flat | +13%\n"
    "- pencil case | falling | -23%\n"
    "- kids backpack | falling | -41%"
)


def extract_text(message) -> str:
    """Pull the briefing out of the response message defensively.

    Order: content, then reasoning_content (reasoning models like gpt-oss put
    their output there, and it may live in pydantic extras), then the whole
    stringified message so nothing is silently lost.
    """
    for attr in ("content", "reasoning_content"):
        val = getattr(message, attr, None)
        if isinstance(val, str) and val.strip():
            return val
    extra = getattr(message, "model_extra", None) or {}
    reasoning = extra.get("reasoning_content")
    if isinstance(reasoning, str) and reasoning.strip():
        return reasoning
    return str(message)


def main():
    api_key = os.environ.get("FIREWORKS_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "FIREWORKS_API_KEY not set. Source .env before running: "
            "set -a; source .env; set +a"
        )

    # Bring up the dedicated deployment (live-merge, single model). Blocks until
    # ready. This is the only step that spins up a GPU and spends credits.
    llm = LLM(
        model=MODEL,
        deployment_type="on-demand",
        id=DEPLOY_ID,
        accelerator_type="NVIDIA_A100_80GB",
        accelerator_count=1,
    )
    llm.apply()

    # One chat completion with the exact training system prompt + signal block.
    resp = llm.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER_SIGNAL},
        ],
        max_tokens=2048,
        temperature=0.3,
    )
    briefing = extract_text(resp.choices[0].message)

    print("=" * 64)
    print("TEST BRIEFING  (category: back to school)")
    print("=" * 64)
    print(briefing)
    print("=" * 64)
    print()

    deployment = llm.deployment_id or llm.deployment_url
    print(f"Deployment id: {deployment}")
    print()
    print("TEARDOWN, run the moment the briefing reads right.")
    print(f"  python -c \"from fireworks import LLM; "
          f"LLM(model='{MODEL}', deployment_type='on-demand', id='{DEPLOY_ID}')"
          f".delete_deployment()\"")
    if llm.deployment_id:
        print(f"  or:  firectl delete deployment {llm.deployment_id}")


if __name__ == "__main__":
    main()
