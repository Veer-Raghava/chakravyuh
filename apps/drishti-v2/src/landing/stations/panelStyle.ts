// Shared visual language for the floating <Html> labels across the pipeline
// stations. One source so every station after SETU reads the same:
//   · Fraunces (display) for headings — warmth, the wide type scale (§4.2)
//   · Hanken (text) for prose lines
//   · IBM Plex Mono for DATA ONLY (hashes, IPs, ports, satoshis, timestamps, weights)
// on a warm paper-deep card with a hairline + soft shadow (§4 surface rule).
//
// Import these instead of hand-rolling inline styles per station — that drift
// is exactly what made everything-after-SETU feel inconsistent.
import type { CSSProperties } from "react";

/** The card the floating labels sit on — translucent paper, hairline, soft lift. */
export const panel: CSSProperties = {
  fontFamily: "var(--font-text)",
  background: "rgba(246, 239, 224, 0.86)",
  border: "1px solid var(--line)",
  borderRadius: 9,
  padding: "11px 13px",
  boxShadow: "0 8px 26px -14px rgba(27, 23, 18, 0.55)",
  color: "var(--ink)",
  backdropFilter: "blur(3px)",
};

/** Station heading — serif, the human voice. */
export const head: CSSProperties = {
  fontFamily: "var(--font-display)",
  fontWeight: 500,
  fontSize: "15px",
  lineHeight: 1.06,
  letterSpacing: "-0.01em",
  color: "var(--ink)",
  margin: 0,
};

/** The small mono kicker above a heading (LAYER · gloss). */
export const kicker: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "9px",
  letterSpacing: "0.16em",
  textTransform: "uppercase",
  color: "var(--ink-soft)",
  marginBottom: 3,
};

/** Prose inside a panel — sans, readable. */
export const prose: CSSProperties = {
  fontFamily: "var(--font-text)",
  fontSize: "12px",
  lineHeight: 1.5,
  color: "var(--ink)",
};

/** Any datum — hash, IP, port, BTC, timestamp, weight. Mono, tabular. */
export const datum: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: "10px",
  fontVariantNumeric: "tabular-nums",
  letterSpacing: "0.01em",
  color: "var(--ink)",
};
