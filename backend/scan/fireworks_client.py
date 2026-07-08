"""Fireworks serverless chat-completions client — the cheap-tier scan model.

This is a product runtime dependency: the scan's filter step calls a Fireworks
serverless model (AMD Instinct) to judge which ranked terms are real
opportunities. Keep it small and parse the response defensively, because
reasoning models (e.g. gpt-oss) don't always put the answer in the usual place.

Keys come from the environment (exported via .env). Nothing is hardcoded.
"""

import json
import os

import requests

ENDPOINT = "https://api.fireworks.ai/inference/v1/chat/completions"
TIMEOUT_SECONDS = 45
TEMPERATURE = 0.2


def _extract_text(body: dict) -> str:
    """Pull the assistant text out of a chat-completions body, defensively.

    Try in order: message.content, then message.reasoning_content (reasoning
    models like gpt-oss put their output there), then the stringified message.
    Returns the first non-empty string, or "" if nothing usable is present.
    Never raises on shape.
    """
    try:
        message = body["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        return ""
    if not isinstance(message, dict):
        return ""

    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content

    reasoning = message.get("reasoning_content")
    if isinstance(reasoning, str) and reasoning.strip():
        return reasoning

    # Last resort: hand the caller the whole message so nothing is silently lost.
    try:
        dumped = json.dumps(message)
    except (TypeError, ValueError):
        dumped = str(message)
    return dumped if dumped.strip() else ""


def complete(prompt: str, max_tokens: int = 512) -> str:
    """Send `prompt` to the cheap-tier Fireworks model and return its text.

    Raises on a missing key or model (setup problems). Returns "" if the request
    fails or the response has no usable text, so the caller can fall back rather
    than crash the scan.
    """
    api_key = os.environ.get("FIREWORKS_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "FIREWORKS_API_KEY not set. Source .env before running: "
            "set -a; source .env; set +a"
        )
    model = os.environ.get("FIREWORKS_MODEL", "")
    if not model:
        raise RuntimeError(
            "FIREWORKS_MODEL not set. Set it to a revealed serverless model id, "
            "e.g. accounts/fireworks/models/gpt-oss-20b"
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": TEMPERATURE,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        resp = requests.post(ENDPOINT, headers=headers, json=payload,
                             timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        print(f"[fireworks_client] request error: {exc}")
        return ""

    if resp.status_code != 200:
        print(f"[fireworks_client] HTTP {resp.status_code}: {resp.text[:200]}")
        return ""

    try:
        body = resp.json()
    except ValueError:
        print(f"[fireworks_client] non-JSON body: {resp.text[:200]}")
        return ""

    return _extract_text(body)


if __name__ == "__main__":
    print(repr(complete("Reply with exactly: plainlode filter ok", max_tokens=32)))
