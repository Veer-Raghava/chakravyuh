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

describe("id — full identifier pass-through", () => {
  it("returns identifiers unchanged and in full, whatever their kind", () => {
    expect(id("103.21.244.17:8333", "ip")).toBe("103.21.244.17:8333");
    expect(id("4f2a9c3ee847fb7ea4367d08c823857b4f1a4f547a706d46dff57b24ba6bb19d", "txid")).toBe(
      "4f2a9c3ee847fb7ea4367d08c823857b4f1a4f547a706d46dff57b24ba6bb19d",
    );
    expect(id("bc1q4fk3tzn0kpdsvzt8d7zy85exj8tn9yzv8l9f4d", "addr")).toBe(
      "bc1q4fk3tzn0kpdsvzt8d7zy85exj8tn9yzv8l9f4d",
    );
  });

  it("never throws on a full value — full display is the point", () => {
    expect(() => id("2001:db8:0:0:0:0:0:1", "ip")).not.toThrow();
    expect(() => id("f".repeat(64), "txid")).not.toThrow();
  });
});
