import { describe, expect, it } from "vitest";
import { balances, dec, id, ms, num } from "./format";

describe("num", () => {
  it("groups thousands", () => {
    expect(num(1_000_000)).toBe("1,000,000");
    expect(num(153)).toBe("153");
  });
});

describe("dec / ms", () => {
  it("fixes decimals and converts microseconds to ms", () => {
    expect(dec(0.87)).toBe("0.87");
    expect(ms(412_000)).toBe("412 ms");
  });
});

describe("balances — the in == out + dropped identity", () => {
  it("holds when a stage accounts for every row", () => {
    expect(balances({ in: 1_000_000, out: 999_847, dropped: 153 })).toBe(true);
    expect(balances({ in: 20, out: 20, dropped: 0 })).toBe(true);
  });

  it("is false when a fixture is edited into imbalance", () => {
    expect(balances({ in: 1_000_000, out: 999_847, dropped: 0 })).toBe(false);
  });
});

describe("id — display-only redaction guard", () => {
  it("passes already-redacted identifiers through unchanged", () => {
    expect(id("103.x.x.x:8333", "ip")).toBe("103.x.x.x:8333");
    expect(id("4f2a9c3e…c19d", "txid")).toBe("4f2a9c3e…c19d");
    expect(id("bc1q4f…9f4d", "addr")).toBe("bc1q4f…9f4d");
  });

  it("throws when a full IP reaches display", () => {
    expect(() => id("103.21.244.17:8333", "ip")).toThrow(/redaction invariant/);
    expect(() => id("2001:db8:0:0:0:0:0:1", "ip")).toThrow(/redaction invariant/);
  });

  it("throws when a full 64-hex txid reaches display", () => {
    expect(() => id("f".repeat(64), "txid")).toThrow(/redaction invariant/);
  });

  it("throws when a full bitcoin address reaches display", () => {
    expect(() => id("bc1q4f8k2m9x7p3q6r5t0w1e2y3u4i5o6a7s8d9f4d", "addr")).toThrow(/redaction invariant/);
  });
});
