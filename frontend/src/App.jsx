import { useEffect, useRef, useState } from "react";
import { C } from "./lib/theme";
import { runScan, runExplain } from "./lib/api";
import OreBackground from "./components/OreBackground";
import Header from "./components/Header";
import Idle from "./components/Idle";
import Scanning from "./components/Scanning";
import Result from "./components/Result";
import ErrorView from "./components/ErrorView";

// Cycled under the scanning vein while the real request is in flight.
const STATUSES = ["pulling live demand signal", "ranking what's moving", "reading the market"];
const DEFAULT_CATEGORY = "back to school";

export default function App() {
  const [phase, setPhase] = useState("idle"); // idle | scanning | result | error
  const [category, setCategory] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [statusIndex, setStatusIndex] = useState(0);
  const [explainer, setExplainer] = useState(null);
  const [explainerState, setExplainerState] = useState("idle"); // idle|loading|done|error

  const statusTimer = useRef(null);
  const scanId = useRef(0); // ignore results from superseded scans

  useEffect(() => () => clearInterval(statusTimer.current), []);

  function startScan(catArg) {
    const cat = (catArg ?? category).trim() || DEFAULT_CATEGORY;
    const myId = ++scanId.current;

    setCategory(cat);
    setData(null);
    setError(null);
    setExplainer(null);
    setExplainerState("idle");
    setStatusIndex(0);
    setPhase("scanning");

    // The status text cycles while we wait; the scanning view stays mounted for
    // the real duration of the request, so the motion runs exactly as long as
    // the fetch (live pull + briefing model call) takes.
    clearInterval(statusTimer.current);
    statusTimer.current = setInterval(() => {
      setStatusIndex((i) => (i + 1) % STATUSES.length);
    }, 1150);

    runScan(cat)
      .then((resp) => {
        if (scanId.current !== myId) return; // a newer scan/reset supersedes this
        clearInterval(statusTimer.current);
        setData(resp);
        setPhase("result");

        // Fetch the plain-English explainer separately so the briefing shows
        // immediately and the explainer card fills in a moment later.
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
      })
      .catch((err) => {
        if (scanId.current !== myId) return;
        clearInterval(statusTimer.current);
        setError(err.message || "Something went wrong.");
        setPhase("error");
      });
  }

  function reset() {
    scanId.current++; // any in-flight scan/explainer result is now ignored
    clearInterval(statusTimer.current);
    setData(null);
    setError(null);
    setExplainer(null);
    setExplainerState("idle");
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
        <Scanning category={category} status={STATUSES[statusIndex]} statusKey={statusIndex} />
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
