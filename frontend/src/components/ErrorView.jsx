import { C, veinGradient } from "../lib/theme";

// Graceful fetch-error state with a retry. Honest about what failed.
export default function ErrorView({ error, onRetry, onReset }) {
  return (
    <div
      style={{
        width: "100%",
        maxWidth: 720,
        marginTop: 40,
        animation: "riseIn .5s ease both",
        display: "flex",
        flexDirection: "column",
        gap: 18,
      }}
    >
      <div style={{ display: "flex", gap: 14, alignItems: "stretch" }}>
        <div style={{ width: 3, borderRadius: 2, background: veinGradient, flex: "none" }} />
        <div>
          <h2
            style={{
              fontFamily: "'Fraunces', serif",
              fontWeight: 500,
              fontSize: 26,
              margin: 0,
              lineHeight: 1.25,
              letterSpacing: "-0.01em",
            }}
          >
            The signal didn't come through.
          </h2>
          <p style={{ color: C.muted, fontSize: 14.5, lineHeight: 1.6, margin: "10px 0 0", maxWidth: 480 }}>
            We couldn't complete the scan.
            {error ? <span style={{ color: C.c7 }}> {error}</span> : null}
          </p>
        </div>
      </div>
      <div style={{ display: "flex", gap: 12 }}>
        <button className="btn-primary" onClick={onRetry}>
          Try again
        </button>
        <button className="btn-ghost" onClick={onReset}>
          Start over
        </button>
      </div>
    </div>
  );
}
