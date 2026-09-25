/**
 * The one display-only formatter every component uses. This workstation shows identifiers
 * IN FULL — full IPs, full Bitcoin addresses, full txids — so an investigator reads exactly
 * what will go on the production notice, not a redacted stand-in. `id()` is kept as the one
 * seam every identifier passes through (so a future policy change lives in one place), but it
 * is now a pass-through: it never truncates and never throws. SHA-256, the Merkle root and the
 * Ed25519 signature are cryptographic evidence and go through HashBlock, never here.
 */

/** Grouped integer for mono tabular display, e.g. 1000000 -> "1,000,000". */
export function num(n: number): string {
  return n.toLocaleString("en-US");
}

/** Fixed-decimal for mono display, e.g. pct(0.87) -> "0.87". */
export function dec(n: number, places = 2): string {
  return n.toFixed(places);
}

/** Microseconds to a mono millisecond string, e.g. us(412000) -> "412 ms". */
export function ms(microseconds: number): string {
  return `${Math.round(microseconds / 1000).toLocaleString("en-US")} ms`;
}

/**
 * The one accountability identity: a stage may only ever emit rows it took in, so
 * `in === out + dropped`. LINEAGE renders a visible failure when this is false rather
 * than three numbers that quietly do not add up. A pure predicate so it is trivially
 * testable and cannot lie about a fixture that was edited into imbalance.
 */
export function balances(counts: { in: number; out: number; dropped: number }): boolean {
  return counts.in === counts.out + counts.dropped;
}

type IdKind = "ip" | "addr" | "txid";

/**
 * Pass an identifier through to display, in full. Kept as the single seam every id crosses
 * so display policy lives in one function; today that policy is "show everything". Never
 * mutates the value. `kind` is retained for call-site clarity and future per-kind handling.
 */
export function id(value: string, _kind: IdKind): string {
  return value;
}
