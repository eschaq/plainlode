import { C } from "../lib/theme";

// The scanning motion, ported from the design: five breathing tick lines, a
// breathing central vein, and a glow that travels down it. This runs for the
// real duration of the fetch — App keeps this view mounted until the request
// promise settles, so the motion loops for exactly as long as the scan takes.
export default function Scanning({ category, status, statusKey }) {
  const tickDelays = [0, 0.3, 0.6, 0.9, 1.2];

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

      <div style={{ height: 26, marginTop: 18, textAlign: "center" }}>
        <div
          key={statusKey}
          style={{
            fontSize: 16,
            color: C.text,
            animation: "statusFade .45s ease both",
          }}
        >
          {status}
        </div>
      </div>

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
