import { describe, expect, it } from "vitest";
import { adapter, ADAPTER_SOURCE } from "../adapter";
import { fixturesAdapter, MANIFEST } from "../adapter/fixtures";
import { apiAdapter } from "../adapter/api";

describe("adapter source switch", () => {
  it("defaults to fixtures when VITE_SOURCE is unset", () => {
    expect(ADAPTER_SOURCE).toBe("fixtures");
    expect(adapter).toBe(fixturesAdapter);
  });

  it("fixtures adapter returns the manifest payload", async () => {
    await expect(adapter.getManifest()).resolves.toEqual(MANIFEST);
  });

  it("api adapter is a stub that fails loudly until S04", () => {
    expect(() => apiAdapter.getManifest()).toThrow("API not built yet");
  });

  it("every alert carries at least one counter-evidence row", async () => {
    // Contract section 8: an alert with empty counter-evidence is a bug.
    const detail = await adapter.getAlert("CASE-2026-0918");
    expect(detail.counter.length).toBeGreaterThan(0);
    expect(detail.counter.some((c) => c.would_clear)).toBe(true);
  });
});
