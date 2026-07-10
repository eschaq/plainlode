// Parse the backend's briefing string into the structured pieces the design
// renders: a headline, the Findings paragraph, the numbered Options, and the
// Recommended block with its kill-signal sentence pulled out. The model uses the
// literal labels "Findings", "Options", "Recommended" (colon sometimes dropped)
// and numbered options, but phrasing varies, so this parses defensively and
// never invents content — anything it can't classify falls back to raw text.

const EMPTY = {
  headline: "",
  findings: "",
  options: [],
  recommended: { call: "", rest: "", killSignal: "" },
};

const LABELS = ["Findings", "Options", "Recommended"];

export function parseBriefing(text) {
  if (!text || !text.trim()) return EMPTY;

  // Strip stray markdown FIRST. This is both a safety net (asterisks never
  // render) and load-bearing: if the model emits "**Findings:**", the "**" sits
  // between the newline and the label and defeats the section regex, jamming the
  // whole briefing into one block. Cleaning it makes the labels parse.
  text = cleanMarkdown(text);

  const marks = [];
  for (const label of LABELS) {
    const re = new RegExp(`(?:^|\\n)\\s*${label}\\b\\s*:?\\s*`, "i");
    const m = re.exec(text);
    if (m) marks.push({ key: label.toLowerCase(), start: m.index, contentStart: m.index + m[0].length });
  }
  marks.sort((a, b) => a.start - b.start);

  // No recognizable structure: show the whole thing rather than lose it.
  if (marks.length === 0) return { ...EMPTY, findings: text.trim() };

  const sec = {};
  for (let i = 0; i < marks.length; i++) {
    const end = i + 1 < marks.length ? marks[i + 1].start : text.length;
    sec[marks[i].key] = text.slice(marks[i].contentStart, end).trim();
  }

  const findings = sec.findings || "";
  const options = parseOptions(sec.options || "");
  const recommended = splitRecommended(sec.recommended || "");
  const headline = capitalize(recommended.call).replace(/[.!?]+$/, "");

  return { headline, findings, options, recommended };
}

function parseOptions(raw) {
  if (!raw || !raw.trim()) return [];
  // Split on leading "1." / "2)" numbered markers.
  const parts = raw
    .split(/(?:^|\n)\s*\d+[.)]\s+/)
    .map((s) => s.replace(/\s+/g, " ").trim())
    .filter(Boolean);
  if (parts.length >= 2) return parts;
  // Fallback: one item per non-empty line, stripping any bullet/number marker.
  return raw
    .split("\n")
    .map((s) => s.replace(/^\s*[-•\d.)]+\s*/, "").replace(/\s+/g, " ").trim())
    .filter(Boolean);
}

function splitRecommended(raw) {
  if (!raw || !raw.trim()) return { call: "", rest: "", killSignal: "" };
  const t = raw.replace(/\s+/g, " ").trim();

  // The kill signal is the sentence naming what would reverse/kill the call.
  // Match kill/reverse as STEMS (not exact words) so every phrasing lands:
  //   "the call is killed", "kill signal", "would reverse this call",
  //   "the signal that would reverse", "reverses/reversed/reversing/reversal".
  // Pair it with a call/signal/this reference to avoid stray matches; everything
  // from that sentence on becomes the kill-signal block.
  const sentences = t.match(/[^.!?]+[.!?]*/g) || [t];
  let killIdx = -1;
  for (let i = 0; i < sentences.length; i++) {
    if (
      /\b(kill|revers)/i.test(sentences[i]) &&
      /\b(call|signal|this|it)\b/i.test(sentences[i])
    ) {
      killIdx = i;
      break;
    }
  }

  let main = t;
  let killSignal = "";
  if (killIdx >= 0) {
    main = sentences.slice(0, killIdx).join("").trim();
    killSignal = sentences.slice(killIdx).join("").trim();
  }

  const call = firstSentence(main);
  const rest = main.slice(call.length).trim();
  return { call, rest, killSignal };
}

function firstSentence(s) {
  const t = (s || "").trim();
  const m = /^(.*?[.!?])(\s|$)/.exec(t);
  return m ? m[1].trim() : t;
}

function capitalize(s) {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

// Remove stray markdown so asterisks never render and the section labels parse
// even when the model wraps them (e.g. "**Findings:**" or "### Findings").
function cleanMarkdown(s) {
  return s
    .replace(/\*/g, "") // all asterisks: ** bold, * emphasis/bullets
    .replace(/__/g, "") // markdown bold underscores
    .replace(/(^|\n)[ \t]{0,3}#{1,6}[ \t]*/g, "$1"); // markdown headings -> plain
}
