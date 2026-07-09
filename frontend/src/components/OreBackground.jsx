// Fixed ore/rock backdrop with gold vein seams, ported verbatim from the v2
// design. Sits behind everything (z-index 0, pointer-events none); the app
// content layers over it at z-index 1 on a transparent background.
export default function OreBackground() {
  return (
    <div
      aria-hidden="true"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 0,
        pointerEvents: "none",
        background: `
          radial-gradient(130% 95% at 50% 4%, rgba(72,80,90,0.85) 0%, rgba(58,64,72,0) 48%),
          radial-gradient(95% 75% at 82% 114%, rgba(232,181,77,0.13) 0%, transparent 44%),
          radial-gradient(75% 60% at 12% -8%, rgba(232,181,77,0.1) 0%, transparent 42%),
          repeating-linear-gradient(112deg, rgba(255,255,255,0.035) 0 1px, transparent 1px 22px),
          repeating-linear-gradient(64deg, rgba(0,0,0,0.4) 0 1px, transparent 1px 34px),
          radial-gradient(150% 130% at 50% 40%, transparent 46%, rgba(0,0,0,0.78) 100%),
          #0C0F13`,
      }}
    >
      {/* gold vein seams */}
      <div
        style={{
          position: "absolute",
          top: "-12%",
          left: "17%",
          width: 3,
          height: "66%",
          transform: "rotate(6deg)",
          filter: "blur(1.5px)",
          background:
            "linear-gradient(180deg, transparent 0%, rgba(232,181,77,0.7) 45%, rgba(232,181,77,0.12) 100%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: "34%",
          left: "20.5%",
          width: 3,
          height: "60%",
          transform: "rotate(-4deg)",
          filter: "blur(1.5px)",
          background:
            "linear-gradient(180deg, rgba(232,181,77,0.1) 0%, rgba(232,181,77,0.55) 40%, transparent 100%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: "15%",
          left: "15.5%",
          width: 2,
          height: "34%",
          transform: "rotate(14deg)",
          filter: "blur(1px)",
          background: "linear-gradient(180deg, transparent, rgba(232,181,77,0.35), transparent)",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: "30%",
          left: "19%",
          width: 90,
          height: 90,
          transform: "translate(-50%,-50%)",
          filter: "blur(30px)",
          background: "radial-gradient(circle, rgba(232,181,77,0.32), transparent 70%)",
        }}
      />
    </div>
  );
}
