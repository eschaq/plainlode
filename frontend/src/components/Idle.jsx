import { C, veinGradient } from "../lib/theme";

const PLACEHOLDER = "back to school";

export default function Idle({ category, setCategory, onSubmit }) {
  // Width grows with the typed category so longer inputs (e.g. "back to
  // school") aren't clipped; the design fixed this at 4.2em for "coffee".
  const shown = category || PLACEHOLDER;
  const inputWidth = `${Math.max(6, shown.length * 0.6)}em`;

  return (
    <div style={{ width: "100%", maxWidth: 720, marginTop: 22, animation: "riseIn .5s ease both" }}>
      <div style={{ display: "flex", gap: 18, alignItems: "stretch" }}>
        <div style={{ width: 3, borderRadius: 2, background: veinGradient, flex: "none" }} />
        <h1
          style={{
            fontFamily: "'Fraunces', serif",
            fontWeight: 500,
            fontSize: "clamp(28px, 8vw, 38px)", // responsive; matches .cat-input
            lineHeight: 1.22,
            margin: 0,
            letterSpacing: "-0.015em",
            textWrap: "balance",
          }}
        >
          What should I add to my{" "}
          <input
            className="cat-input"
            style={{ width: inputWidth }}
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") onSubmit();
            }}
            placeholder={PLACEHOLDER}
            aria-label="Store category to scan"
            autoFocus
          />{" "}
          store next?
        </h1>
      </div>

      <p
        style={{
          color: C.muted,
          fontSize: 15,
          lineHeight: 1.6,
          margin: "24px 0 0 21px",
          maxWidth: 460,
        }}
      >
        One plain-language decision, mined from live demand signal. No dashboard, no charts to read.
      </p>

      <div style={{ margin: "32px 0 0 21px" }}>
        <button className="btn-primary" onClick={onSubmit}>
          Mine the signal →
        </button>
      </div>
    </div>
  );
}
