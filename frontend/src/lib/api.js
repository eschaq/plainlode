// Talks to the Plainlode FastAPI backend. Base URL comes from an env var so the
// same build can point at localhost in dev or the deployed backend later.
export const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

/**
 * POST /api/scan for a category. Returns the parsed JSON response:
 * { category, source, has_data, findings, below_floor, briefing, explainer, ... }
 * Throws Error with a readable message on network or non-2xx responses.
 */
export async function runScan(category) {
  let res;
  try {
    res = await fetch(`${API_BASE}/api/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category }),
    });
  } catch {
    throw new Error(`Can't reach the scan service at ${API_BASE}.`);
  }
  if (!res.ok) {
    let detail = `The scan service responded ${res.status}.`;
    try {
      const body = await res.json();
      if (body && body.detail) detail = String(body.detail);
    } catch {
      /* keep the status-based message */
    }
    throw new Error(detail);
  }
  return res.json();
}

/**
 * POST /api/explain for a briefing already returned by /api/scan. Returns the
 * plain-English explainer string. Called after the briefing renders so it can
 * fill in a moment later without blocking the scan.
 */
export async function runExplain(category, briefing, findings) {
  const res = await fetch(`${API_BASE}/api/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category, briefing, findings: findings || [] }),
  });
  if (!res.ok) throw new Error(`The explainer service responded ${res.status}.`);
  const data = await res.json();
  return data.explainer;
}
