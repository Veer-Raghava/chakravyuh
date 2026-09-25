import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { adapter } from "../adapter";
import { LINEAGE_TRACES } from "../adapter/fixtures";
import { balances } from "../format";
import { Lineage } from "./Lineage";

const STAGE_ORDER = ["MAYAJAAL", "KAVACH", "SETU", "JAAL", "SHASTRA", "BUDDHI", "VAANI", "PRAMAAN"];

describe("getLineage — the per-record trace", () => {
  it("returns exactly eight stages in the fixed order, for every record", async () => {
    for (const recordId of Object.keys(LINEAGE_TRACES)) {
      const trace = await adapter.getLineage(recordId);
      expect(trace.stages.map((s) => s.stage)).toEqual(STAGE_ORDER);
    }
  });

  it("every stage balances: in === out + dropped", async () => {
    for (const recordId of Object.keys(LINEAGE_TRACES)) {
      const trace = await adapter.getLineage(recordId);
      for (const stage of trace.stages) {
        expect(balances(stage.counts)).toBe(true);
      }
    }
  });

  it("SETU carries the canonical src_ip -> peer_ip rename", async () => {
    const trace = await adapter.getLineage("4f2a9c3e…b19d");
    const setu = trace.stages.find((s) => s.stage === "SETU")!;
    const rename = setu.after.find((f) => f.status === "renamed" && f.name === "peer_ip");
    expect(rename).toBeDefined();
    expect(rename!.from).toBe("src_ip");
  });

  it("the grain-split mean is computed from data, not the hardcoded 9", async () => {
    const trace = await adapter.getLineage("4f2a9c3e…b19d");
    const { n_announcements, n_transactions } = trace.setu.collapse;
    const mean = n_announcements / n_transactions;
    // ~9, but not exactly 9 — a future run that lands at seven would show seven.
    expect(mean).toBeCloseTo(9, 0);
    expect(mean).not.toBe(9);
  });

  it("PRAMAAN carries the Merkle head in full (64 hex), not truncated", async () => {
    const trace = await adapter.getLineage("4f2a9c3e…b19d");
    expect(trace.merkle_head).toMatch(/^[0-9a-f]{64}$/);
  });
});

describe("Lineage route — mounts and renders the hero trace", () => {
  it("shows all eight stage tabs and a balancing arithmetic line", async () => {
    render(<Lineage />);
    // Eight stage tabs on the spine once the trace resolves.
    const tabs = await screen.findAllByRole("tab");
    expect(tabs).toHaveLength(8);
    // Default stage is SETU: the canonical rename is visible.
    expect(await screen.findByText("peer_ip")).toBeInTheDocument();
    expect(screen.getByText("balances")).toBeInTheDocument();
  });
});
