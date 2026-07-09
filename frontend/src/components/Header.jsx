import { C, veinGradient } from "../lib/theme";

export default function Header() {
  return (
    <div
      style={{
        width: "100%",
        maxWidth: 720,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginBottom: 56,
      }}
    >
      <div style={{ display: "flex", alignItems: "stretch", gap: 14 }}>
        <div
          style={{
            width: 3,
            borderRadius: 2,
            background:
              "linear-gradient(180deg, rgba(232,181,77,0) 0%, #E8B54D 22%, #E8B54D 78%, rgba(232,181,77,0) 100%)",
          }}
        />
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div
            style={{
              fontFamily: "'Fraunces', serif",
              fontWeight: 600,
              fontSize: 22,
              letterSpacing: "-0.01em",
              lineHeight: 1,
            }}
          >
            Plainlode
          </div>
          <div style={{ fontSize: 11, color: C.muted, marginTop: 5, letterSpacing: "0.02em" }}>
            The signal, mined plain.
          </div>
        </div>
      </div>
    </div>
  );
}
