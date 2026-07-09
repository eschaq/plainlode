// Plainlode palette — premium refinement of the v2 design. Deeper ground,
// translucent hairline borders, warmer surfaces. Token NAMES are unchanged so
// every component picks up the new look without edits; only the values moved.
export const C = {
  bg: "#0C0F13", // deeper ink ground
  text: "#F3F5F8",
  gold: "#E8B54D",
  goldHover: "#F0C877",
  goldSoft: "#F0C877",
  muted: "#9AA1AB",
  dim: "#6E7681", // was #5A626D — lifts contrast to AA
  c7: "#C7CCD3",
  d6: "#D6DAE0",
  b7: "#B7BDC6",
  cardBg: "#12161C", // panel
  cardBg2: "#161B22", // panel-2 (slightly warmer, for the explainer)
  // Borders are now translucent white hairlines — reads more premium on dark
  // than solid hex lines. Names kept as border/border2/border3.
  line: "rgba(255,255,255,0.07)",
  line2: "rgba(255,255,255,0.11)",
  border: "rgba(255,255,255,0.07)",
  border2: "rgba(255,255,255,0.11)",
  border3: "rgba(255,255,255,0.07)",
  border4: "#3A4048", // kept solid for the scanning tick lines / ghost button
};

// The vertical "vein" gradient used as a left accent throughout the design.
export const veinGradient =
  "linear-gradient(180deg, rgba(232,181,77,0) 0%, #E8B54D 30%, #E8B54D 70%, rgba(232,181,77,0) 100%)";
