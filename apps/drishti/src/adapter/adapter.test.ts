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

  it("api adapter is wired: pipeline reads fetch, the simulated seam delegates to fixtures", () => {
    // getManifest is a real HTTP read now, not the old throwing stub, so it must not throw
    // synchronously (it returns a promise that rejects only if the server is unreachable).
    expect(() => void apiAdapter.getManifest().catch(() => undefined)).not.toThrow();
    // The six run-control/lineage calls are the frontend-owned seam and delegate unchanged.
    expect(apiAdapter.listRuns).toBe(fixturesAdapter.listRuns);
    expect(apiAdapter.getLineage).toBe(fixturesAdapter.getLineage);
    expect(apiAdapter.getRows).toBe(fixturesAdapter.getRows);
  });

  it("every alert carries at least one counter-evidence row", async () => {
    // Contract section 8: an alert with empty counter-evidence is a bug.
    const detail = await adapter.getAlert("CASE-2026-0918");
    expect(detail.counter.length).toBeGreaterThan(0);
    expect(detail.counter.some((c) => c.would_clear)).toBe(true);
  });
});
