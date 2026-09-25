import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { App } from "./App";

// Proves the integration gap is closed: LINEAGE is reachable from the real shell (not
// only the /_lineage scratch route), and selecting it mounts the actual Lineage screen
// against the fixture adapter — no dev server required.
describe("App shell — LINEAGE wired as screen 7", () => {
  it("shows a LINEAGE nav entry and renders the Lineage screen when selected", async () => {
    render(<App />);

    const nav = screen.getByRole("button", { name: /LINEAGE/ });
    expect(nav).toBeInTheDocument();

    fireEvent.click(nav);

    // The real Lineage page mounts with the hero fixture: the canonical rename and the
    // balancing arithmetic line both appear.
    expect(await screen.findByText("peer_ip")).toBeInTheDocument();
    expect(await screen.findByText("balances")).toBeInTheDocument();
  });
});
