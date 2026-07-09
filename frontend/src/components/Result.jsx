import { C, veinGradient } from "../lib/theme";
import { parseBriefing } from "../lib/parseBriefing";

function pct(slope) {
  const p = Math.round((Number(slope) || 0) * 100);
  return `${p > 0 ? "+" : ""}${p}%`;
}

// Honest empty state: live pull failed and there was no snapshot to fall back
// on. Nothing is fabricated, so there's nothing to show.
function EmptyState({ category, onReset }) {
  return (
    <div
      style={{
        width: "100%",
        maxWidth: 720,
        marginTop: 24,
        animation: "riseIn .5s ease both",
        display: "flex",
        flexDirection: "column",
        gap: 18,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 7, height: 7, borderRadius: "50%", background: C.dim, flex: "none" }} />
        <span style={{ fontSize: 12.5, color: C.muted, fontWeight: 700 }}>No live signal</span>
      </div>
      <div style={{ display: "flex", gap: 14, alignItems: "stretch" }}>
        <div
          style={{
            width: 3,
            borderRadius: 2,
            background:
              "linear-gradient(180deg, rgba(232,181,77,0) 0%, rgba(232,181,77,.4) 30%, rgba(232,181,77,.4) 70%, rgba(232,181,77,0) 100%)",
            flex: "none",
          }}
        />
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
            No live signal for {category} right now.
          </h2>
          <p style={{ color: C.muted, fontSize: 14.5, lineHeight: 1.65, margin: "10px 0 0", maxWidth: 480 }}>
            We didn't get fresh demand data for that category, and there's no recent snapshot to fall
            back on. Nothing here is guessed, so there's nothing to show yet. Try another store
            category, or check back in a little while.
          </p>
        </div>
      </div>
      <div style={{ marginTop: 4 }}>
        <button className="btn-ghost" onClick={onReset}>
          Ask about another store
        </button>
      </div>
    </div>
  );
}

export default function Result({ data, explainer, explainerState, onReset }) {
  if (!data.has_data) return <EmptyState category={data.category} onReset={onReset} />;

  const isLive = data.source === "scrapingdog_live";
  const findings = data.findings || [];
  const brief = parseBriefing(data.briefing);

  return (
    <div
      style={{
        width: "100%",
        maxWidth: 720,
        display: "flex",
        flexDirection: "column",
        gap: 22,
        animation: "riseIn .55s ease both",
      }}
    >
      {/* source indicator */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <div
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: C.gold,
            opacity: isLive ? 1 : 0.55,
            animation: isLive ? "livePulse 1.8s ease-in-out infinite" : "none",
            flex: "none",
          }}
        />
        <span style={{ fontSize: 12.5, color: C.text, fontWeight: 700 }}>
          {isLive ? "Live signal" : "Recent snapshot"}
        </span>
        <span style={{ fontSize: 12.5, color: C.muted }}>
          {isLive ? "· scanned just now" : "· from a recent live pull"}
        </span>
      </div>

      {/* findings strip */}
      {findings.length > 0 && (
        <div>
          <div
            style={{
              fontSize: 11,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: C.muted,
              marginBottom: 12,
            }}
          >
            What's moving in {data.category}
          </div>
          <div className="bento">
            {findings.map((f, i) => {
              const rising = f.direction === "rising";
              const falling = f.direction === "falling";
              const dirClass = rising ? "up" : falling ? "down" : "";
              const arrow = rising ? "↑" : falling ? "↓" : "→";
              const feature = i === 0; // top mover leads the bento
              return (
                <div key={i} className={`cell ${dirClass}${feature ? " feature" : ""}`}>
                  <div className="num">
                    <span className="arrow">{arrow}</span>
                    <span className="slope">{pct(f.slope)}</span>
                  </div>
                  <div className="term">{f.query}</div>
                  {feature && <span className="tag">Top mover</span>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* BRIEFING (hero) */}
      <div style={{ border: `1px solid ${C.border2}`, background: C.cardBg, borderRadius: 22, overflow: "hidden" }}>
        <div style={{ display: "flex", alignItems: "stretch", gap: 16, padding: "26px 26px 8px" }}>
          <div
            style={{
              width: 3,
              borderRadius: 2,
              background: "linear-gradient(180deg, #E8B54D, rgba(232,181,77,0.15))",
              flex: "none",
            }}
          />
          <div>
            <div style={{ fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: C.gold }}>
              Briefing
            </div>
            {brief.headline && (
              <h2
                style={{
                  fontFamily: "'Fraunces', serif",
                  fontWeight: 400,
                  fontSize: "clamp(28px, 3.4vw, 38px)",
                  margin: "10px 0 0",
                  lineHeight: 1.1,
                  letterSpacing: "-0.02em",
                  maxWidth: "18ch",
                }}
              >
                {brief.headline}
              </h2>
            )}
          </div>
        </div>

        <div style={{ padding: "14px 26px 26px 45px", display: "flex", flexDirection: "column", gap: 22 }}>
          {brief.findings && (
            <div>
              <div
                style={{ fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: C.muted, marginBottom: 7 }}
              >
                Findings
              </div>
              <p style={{ margin: 0, fontSize: 15, lineHeight: 1.65, color: C.d6 }}>{brief.findings}</p>
            </div>
          )}

          {brief.options.length > 0 && (
            <div>
              <div
                style={{ fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: C.muted, marginBottom: 10 }}
              >
                Options
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
                {brief.options.map((o, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
                    <span
                      style={{ fontFamily: "'Fraunces', serif", fontSize: 14, color: C.gold, width: 18, flex: "none" }}
                    >
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <div style={{ fontSize: 15, color: C.d6, lineHeight: 1.5 }}>{o}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommended */}
          {(brief.recommended.call || brief.recommended.rest) && (
            <div
              style={{
                background: "rgba(232,181,77,0.07)",
                border: "1px solid rgba(232,181,77,0.35)",
                borderRadius: 12,
                padding: "18px 20px",
              }}
            >
              <div
                style={{ fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: C.gold, marginBottom: 8 }}
              >
                Recommended
              </div>
              <p style={{ margin: 0, fontSize: 16, lineHeight: 1.6, color: C.text }}>
                {brief.recommended.call && <b style={{ color: C.gold }}>{brief.recommended.call} </b>}
                {brief.recommended.rest}
              </p>

              {brief.recommended.killSignal && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "stretch",
                    gap: 12,
                    marginTop: 16,
                    paddingTop: 14,
                    borderTop: "1px solid rgba(232,181,77,0.2)",
                  }}
                >
                  <div style={{ width: 3, borderRadius: 2, background: C.gold, flex: "none" }} />
                  <div>
                    <div
                      style={{
                        fontSize: 11,
                        letterSpacing: "0.1em",
                        textTransform: "uppercase",
                        color: C.gold,
                        fontWeight: 700,
                      }}
                    >
                      Kill signal
                    </div>
                    <p style={{ margin: "5px 0 0", fontSize: 14, lineHeight: 1.55, color: C.c7 }}>
                      {brief.recommended.killSignal}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Explainer (softer) — fetched separately, so it fills in a beat after the
          briefing. Hidden entirely if that second call fails (it's secondary). */}
      {explainerState !== "error" && (
        <div style={{ border: `1px solid ${C.border3}`, background: C.cardBg2, borderRadius: 14, padding: "22px 24px" }}>
          <div
            style={{ fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: C.muted, marginBottom: 9 }}
          >
            In plain English
          </div>
          {explainerState === "done" && explainer ? (
            <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.7, color: C.b7 }}>{explainer}</p>
          ) : (
            // Subtle skeleton shimmer while /api/explain is in flight — on this
            // card only, so the rest of the briefing stays put.
            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 3 }} aria-hidden="true">
              <div className="shimmer-line" style={{ width: "100%" }} />
              <div className="shimmer-line" style={{ width: "94%" }} />
              <div className="shimmer-line" style={{ width: "72%" }} />
            </div>
          )}
        </div>
      )}

      <div style={{ marginTop: 4 }}>
        <button className="btn-ghost" onClick={onReset}>
          Ask about another store
        </button>
      </div>
    </div>
  );
}
