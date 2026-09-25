import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Queue, QueueInspector } from "./Queue";
import type { AlertDetail } from "../adapter";

// The mining-pool case is the demo beat: it opens, shows its counter-evidence with a WOULD
// CLEAR marker, and clears out of the queue. Every value comes from the fixture adapter.
describe("QUEUE screen", () => {
  it("opens the mining-pool lead, shows its counter-evidence, and clears it out", async () => {
    render(<Queue onNavigate={() => {}} />);

    const caseCell = await screen.findByText("CASE-2026-0918");
    fireEvent.click(caseCell);

    // The inspector loads the detail: counter-evidence is present and marked decisive.
    expect((await screen.findAllByText(/WOULD CLEAR/)).length).toBeGreaterThan(0);
    expect(screen.getByText(/mining pool payout/i)).toBeInTheDocument();

    // Clearing drops the lead from the queue entirely.
    fireEvent.click(screen.getByRole("button", { name: /clear lead/i }));
    await waitFor(() => expect(screen.queryByText("CASE-2026-0918")).toBeNull());
  });
});

// The two states the spec calls defects, exercised on the inspector in isolation so a bad
// fixture cannot slip a bare score or an empty counter section past the screen.
describe("QUEUE inspector defect states", () => {
  const base: AlertDetail = {
    alert_id: "AL-T", case_id: "CASE-T", severity: "high", headline: "test lead", status: "OPEN",
    why: { base_rate: 0.03, contributions: [{ feature: "a signal", value: 0.2 }] },
    evidence: [{ kind: "typology", statement: "x", weight: 0.1, source_ref: "ref#1" }],
    counter: [{ kind: "shared_ip", statement: "y", strength: 0.5, would_clear: false }],
    confidence: { score: 0.7, low: 0.6, high: 0.8, coverage_target: 0.9, empirical_coverage: 0.9, label: "UNCLEAR" },
  };

  it("renders a visible defect when an alert has no counter-evidence", () => {
    render(<QueueInspector detail={{ ...base, counter: [] }} onClear={() => {}} onNavigate={() => {}} />);
    expect(screen.getByText(/PIPELINE DEFECT/)).toBeInTheDocument();
  });

  it("renders a defect instead of a bare score when the interval is missing", () => {
    const noInterval = { ...base, confidence: { ...base.confidence, low: NaN, high: NaN } };
    render(<QueueInspector detail={noInterval} onClear={() => {}} onNavigate={() => {}} />);
    expect(screen.getByText(/NO INTERVAL/)).toBeInTheDocument();
    // The point estimate must not appear on its own.
    expect(screen.queryByText("0.70")).toBeNull();
  });
});
