import { C } from "../lib/theme";

// One row in the real-progress list: a pulsing gold dot while active, a gold
// check when done, plus the stage label (dimmed once complete).
function StageRow({ stage }) {
  const done = stage.status === "done";
  return (
    <div
      style={{ display: "flex", alignItems: "center", gap: 12, animation: "statusFade .4s ease both" }}
    >
      <span style={{ width: 16, display: "flex", justifyContent: "center", flex: "none" }}>
        {done ? (
          <span style={{ color: C.gold, fontSize: 14, lineHeight: 1 }}>✓</span>
        ) : (
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: C.gold,
              animation: "livePulse 1.2s ease-in-out infinite",
            }}
          />
        )}
      </span>
      <span style={{ fontSize: 14.5, color: done ? C.muted : C.text }}>{stage.label}</span>
      {stage.source && (
        <span style={{ fontSize: 12, color: C.dim }}>· {stage.source}</span>
      )}
    </div>
  );
}

// The scanning motion, ported from the design: five breathing tick lines, a
// breathing central vein, and a glow that travels down it. It runs for the real
// duration of the scan. Below it, real pipeline stages stream in via SSE
// (`stages`); if streaming is unavailable, a single rotating status label
// (`status`) is shown instead.
export default function Scanning({ category, stages, status, statusKey }) {
  const tickDelays = [0, 0.3, 0.6, 0.9, 1.2];
  const hasStages = Array.isArray(stages) && stages.length > 0;

  return (
    <div
      style={{
        width: "100%",
        maxWidth: 720,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        marginTop: 40,
      }}
    >
      <div
        style={{
          position: "relative",
          width: "100%",
          height: 260,
          overflow: "hidden",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* horizontal ticks */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            padding: "20px 0",
          }}
        >
          {tickDelays.map((d, i) => (
            <div
              key={i}
              style={{
                height: 1,
                background: C.border4,
                animation: `tick 2.4s ease-in-out ${d}s infinite`,
              }}
            />
          ))}
        </div>

        {/* the vein */}
        <div
          style={{
            position: "relative",
            width: 3,
            height: "100%",
            borderRadius: 3,
            background:
              "linear-gradient(180deg, rgba(232,181,77,0) 0%, rgba(232,181,77,0.28) 50%, rgba(232,181,77,0) 100%)",
            animation: "veinBreathe 2.2s ease-in-out infinite",
          }}
        >
          {/* traveling glow */}
          <div
            style={{
              position: "absolute",
              left: "50%",
              top: "50%",
              transform: "translate(-50%,-50%)",
              width: 3,
              height: 90,
              borderRadius: 3,
              background:
                "linear-gradient(180deg, rgba(232,181,77,0) 0%, #E8B54D 50%, rgba(232,181,77,0) 100%)",
              boxShadow: "0 0 24px 6px rgba(232,181,77,0.55)",
              animation: "veinTravel 1.9s cubic-bezier(.5,0,.5,1) infinite",
            }}
          />
        </div>
      </div>

      {hasStages ? (
        // Real pipeline progress from the SSE stream.
        <div
          style={{
            marginTop: 8,
            display: "flex",
            flexDirection: "column",
            gap: 11,
            minHeight: 26,
            width: "fit-content",
          }}
        >
          {stages.map((s) => (
            <StageRow key={s.key} stage={s} />
          ))}
        </div>
      ) : (
        // Fallback: single rotating status label (used when SSE is unavailable).
        <div style={{ height: 26, marginTop: 18, textAlign: "center" }}>
          <div
            key={statusKey}
            style={{ fontSize: 16, color: C.text, animation: "statusFade .45s ease both" }}
          >
            {status}
          </div>
        </div>
      )}

      <div
        style={{
          marginTop: 22,
          fontSize: 12,
          color: C.muted, // was C.dim (#5A626D ~3:1); muted meets AA contrast
          letterSpacing: "0.06em",
          textTransform: "uppercase",
        }}
      >
        Scanning {category} demand
      </div>
    </div>
  );
}
