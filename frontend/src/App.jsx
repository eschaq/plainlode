import { useEffect, useRef, useState } from "react";
import { C } from "./lib/theme";
import { runScan, runExplain, API_BASE } from "./lib/api";
import OreBackground from "./components/OreBackground";
import Header from "./components/Header";
import Idle from "./components/Idle";
import Scanning from "./components/Scanning";
import Result from "./components/Result";
import ErrorView from "./components/ErrorView";

// Rotating labels used only in the POST fallback (when SSE is unavailable).
const STATUSES = ["pulling live demand signal", "ranking what's moving", "reading the market"];
const DEFAULT_CATEGORY = "back to school";

export default function App() {
  const [phase, setPhase] = useState("idle"); // idle | scanning | result | error
  const [category, setCategory] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [statusIndex, setStatusIndex] = useState(0);
  const [stages, setStages] = useState([]); // real SSE progress: [{key,label,status,source?}]
  const [explainer, setExplainer] = useState(null);
  const [explainerState, setExplainerState] = useState("idle"); // idle|loading|done|error

  const statusTimer = useRef(null);
  const esRef = useRef(null); // active EventSource
  const scanId = useRef(0); // ignore results from superseded scans

  useEffect(
    () => () => {
      clearInterval(statusTimer.current);
      if (esRef.current) esRef.current.close();
    },
    []
  );

  // Render a completed scan result and kick off the separate explainer fetch.
  function handleResult(resp, myId) {
    if (scanId.current !== myId) return;
    clearInterval(statusTimer.current);
    setData(resp);
    setPhase("result");
    if (resp.has_data && resp.briefing) {
      setExplainerState("loading");
      runExplain(resp.category, resp.briefing, resp.findings)
        .then((ex) => {
          if (scanId.current !== myId) return;
          setExplainer(ex);
          setExplainerState("done");
        })
        .catch(() => {
          if (scanId.current !== myId) return;
          setExplainerState("error"); // secondary; the card just stays hidden
        });
    }
  }

  // Merge one SSE stage event into the progress list (add on start, update on done).
  function updateStage(ev) {
    setStages((prev) => {
      const idx = prev.findIndex((s) => s.key === ev.stage);
      const entry = {
        key: ev.stage,
        label: ev.label || ev.stage,
        status: ev.status === "done" ? "done" : "active",
        source: ev.source || (idx >= 0 ? prev[idx].source : undefined),
      };
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = entry;
        return next;
      }
      return [...prev, entry];
    });
  }

  // Fallback path: plain POST /api/scan with the old rotating status labels.
  function fallbackToPost(cat, myId) {
    if (scanId.current !== myId) return;
    clearInterval(statusTimer.current);
    setStatusIndex(0);
    setStages([]); // no real stages on the fallback path; show the rotating label
    statusTimer.current = setInterval(
      () => setStatusIndex((i) => (i + 1) % STATUSES.length),
      1150
    );
    runScan(cat)
      .then((resp) => handleResult(resp, myId))
      .catch((err) => {
        if (scanId.current !== myId) return;
        clearInterval(statusTimer.current);
        setError(err.message || "Something went wrong.");
        setPhase("error");
      });
  }

  function startScan(catArg) {
    const cat = (catArg ?? category).trim() || DEFAULT_CATEGORY;
    const myId = ++scanId.current;

    setCategory(cat);
    setData(null);
    setError(null);
    setExplainer(null);
    setExplainerState("idle");
    setStages([]);
    setStatusIndex(0);
    setPhase("scanning");

    clearInterval(statusTimer.current);
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    // Prefer the real-progress SSE stream; fall back to POST on any failure.
    if (typeof EventSource === "undefined") {
      fallbackToPost(cat, myId);
      return;
    }

    let settled = false;
    const es = new EventSource(`${API_BASE}/api/scan/stream?category=${encodeURIComponent(cat)}`);
    esRef.current = es;

    es.onmessage = (e) => {
      if (scanId.current !== myId) {
        es.close();
        return;
      }
      let ev;
      try {
        ev = JSON.parse(e.data);
      } catch {
        return;
      }
      if (ev.stage === "complete") {
        settled = true;
        es.close();
        esRef.current = null;
        handleResult(ev.result, myId);
      } else if (ev.stage === "error") {
        // Pipeline error (e.g. briefing failed) — show it honestly; retrying via
        // POST would just re-run and likely fail again.
        settled = true;
        es.close();
        esRef.current = null;
        setError(ev.detail || "The scan failed.");
        setPhase("error");
      } else {
        updateStage(ev);
      }
    };

    es.onerror = () => {
      // Connection failure before completion — fall back to the plain POST flow.
      if (settled || scanId.current !== myId) return;
      settled = true;
      es.close();
      esRef.current = null;
      fallbackToPost(cat, myId);
    };
  }

  function reset() {
    scanId.current++; // any in-flight scan/stream/explainer result is now ignored
    clearInterval(statusTimer.current);
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    setData(null);
    setError(null);
    setExplainer(null);
    setExplainerState("idle");
    setStages([]);
    setPhase("idle");
  }

  return (
    <>
      <OreBackground />
      <div
        style={{
          position: "relative",
          zIndex: 1,
          minHeight: "100vh",
          background: "transparent",
          color: C.text,
          fontFamily: "'Space Grotesk', system-ui, sans-serif",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "28px 20px 60px",
        }}
      >
        <Header />

        {phase === "idle" && (
          <Idle category={category} setCategory={setCategory} onSubmit={() => startScan()} />
        )}

        {phase === "scanning" && (
          <Scanning
            category={category}
            stages={stages}
            status={STATUSES[statusIndex]}
            statusKey={statusIndex}
          />
        )}

        {phase === "result" && data && (
          <Result
            data={data}
            explainer={explainer}
            explainerState={explainerState}
            onReset={reset}
          />
        )}

        {phase === "error" && (
          <ErrorView error={error} onRetry={() => startScan(category)} onReset={reset} />
        )}
      </div>
    </>
  );
}
