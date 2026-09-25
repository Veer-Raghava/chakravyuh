import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { Origin } from "./Origin";

// The confident case and the abstain case are the two beats this screen has to land. Both
// are driven entirely by the fixture adapter — no number in these assertions is typed into
// the component, they all originate in getOriginEstimate.
describe("ORIGIN screen", () => {
  it("renders the fan, reveals the estimate on Space, and never implies a total", async () => {
    const { container } = render(<Origin />);

    // The first qualifying transaction loads its lanes: the rank-1 peer's lane is present.
    expect(await screen.findByText(/103\.x\.x\.x:8333/)).toBeInTheDocument();

    // Pre-reveal: no probability is shown anywhere.
    expect(screen.queryByText(/p = /)).toBeNull();

    // Space fires the reveal; the probability + interval appear in the adapter's exact form.
    fireEvent.keyDown(window, { key: " " });
    expect(await screen.findByText(/p = 0\.87\s+\[0\.79, 0\.92\]/)).toBeInTheDocument();

    // Deliberate property of the estimator: probabilities do not sum to 1, so nothing on the
    // screen is a percentage, a total, or a share-of-whole.
    expect(container.textContent).not.toContain("%");
  });

  it("shows the abstain state for the Tor transaction and refuses to name a peer", async () => {
    render(<Origin />);

    // Pick the transaction tagged ABSTAIN from the selector.
    const abstainCase = await screen.findByRole("button", { name: /ABSTAIN/ });
    fireEvent.click(abstainCase);

    // The exact refusal sentence lives in the aside. The estimate loads async on select, so
    // wait for it; it is split across text nodes, so assert against the aside's text content.
    const aside = await screen.findByRole("complementary");
    await waitFor(() =>
      expect(aside.textContent).toMatch(/observed peer is a Tor exit · origin not estimable/),
    );

    // Space must not conjure an estimate for an abstained transaction.
    fireEvent.keyDown(window, { key: " " });
    expect(within(aside).queryByText(/p = 0\./)).toBeNull();
  });
});
