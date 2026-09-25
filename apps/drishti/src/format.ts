/**
 * The one display-only formatter every component uses. Redaction is NOT done here:
 * data from the adapter is already truncated at write time (see adapter/types.ts). So a
 * COMPLETE identifier reaching `id()` is a pipeline bug, and we throw rather than smooth
 * it over — a forensics tool that silently renders a full IP/address/txid has failed at
 * its own premise. SHA-256 and Merkle roots are the sanctioned exception and go through
 * HashBlock, never through here.
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

// A complete IPv4/6 has every segment; the redacted form always carries an `x`.
const FULL_IPV4 = /^\d{1,3}(\.\d{1,3}){3}(:\d+)?$/;
const FULL_IPV6 = /^([0-9a-fA-F]{1,4}:){2,}[0-9a-fA-F]{1,4}(:\d+)?$/;
// A complete txid/hash is 64 hex; the redacted form carries an ellipsis.
const FULL_HEX64 = /^[0-9a-fA-F]{64}$/;
const ELLIPSIS = /[…]|\.\.\./;

/**
 * Pass a value already redacted upstream through to display. Throws if it looks complete,
 * because that means the invariant upstream broke. Display-only: never mutates the value.
 */
export function id(value: string, kind: IdKind): string {
  if (kind === "ip") {
    if (FULL_IPV4.test(value) || FULL_IPV6.test(value)) {
      throw new Error(`redaction invariant broken: full IP reached display: ${value}`);
    }
    return value;
  }
  if (kind === "txid") {
    if (FULL_HEX64.test(value)) {
      throw new Error(`redaction invariant broken: full txid reached display`);
    }
    return value;
  }
  // addr: a redacted bitcoin address keeps first6+last4 and carries an ellipsis. A long
  // string with no ellipsis is a full address that escaped truncation.
  if (!ELLIPSIS.test(value) && value.length > 14) {
    throw new Error(`redaction invariant broken: full address reached display`);
  }
  return value;
}
