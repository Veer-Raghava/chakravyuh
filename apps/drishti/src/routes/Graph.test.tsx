import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { computeBase, place, W, H } from "../graph/layout";
import { LAYER, EDGE_STROKE, edgeBaseOpacity } from "../graph/semantics";
import { fold } from "../graph/fold";
import { GRAPHS } from "../adapter/fixtures";
import { adapter } from "../adapter";
import { Graph } from "./Graph";

const nodes = GRAPHS.default.nodes;
// Addresses never take a grid slot — they bloom beside their cluster via placeAddress(), so
// the columnar-layout assertions below run over the aggregate nodes only.
const gridNodes = nodes.filter((n) => n.kind !== "address");

describe("graph layout", () => {
  it("is deterministic: same nodes in, byte-identical positions out", () => {
    expect(computeBase(nodes)).toEqual(computeBase([...nodes].reverse()));
  });

  it("puts the chain layer left of the seam and the network layer right, in BOTH", () => {
    const base = computeBase(nodes);
    for (const n of gridNodes) {
      const p = place(base, n.node_id, "both");
      if (LAYER[n.kind] === "chain") expect(p.x).toBeLessThan(W / 2);
      else expect(p.x).toBeGreaterThan(W / 2);
      expect(p.visible).toBe(true);
    }
  });

  it("hides the other layer in a solo mode and centres the shown one", () => {
    const base = computeBase(nodes);
    const chainShown = gridNodes.filter((n) => LAYER[n.kind] === "chain");
    const netShown = gridNodes.filter((n) => LAYER[n.kind] === "network");
    for (const n of netShown) expect(place(base, n.node_id, "chain").visible).toBe(false);
    for (const n of chainShown) expect(place(base, n.node_id, "network").visible).toBe(false);
    // the centred block straddles the seam
    const xs = chainShown.map((n) => place(base, n.node_id, "chain").x);
    expect(Math.min(...xs)).toBeLessThan(W / 2);
    expect(Math.max(...xs)).toBeGreaterThan(W / 2);
    expect(place(base, chainShown[0].node_id, "chain").y).toBeGreaterThan(0);
    expect(place(base, chainShown[0].node_id, "chain").y).toBeLessThan(H);
  });
});

describe("graph fold", () => {
  it("folds every wallet into its cluster by default, so no address node is shown", () => {
    const folded = fold(GRAPHS.default, new Set());
    expect(folded.nodes.some((n) => n.kind === "address")).toBe(false);
    expect(folded.foldedAddresses).toBeGreaterThan(0);
    // a spend that pointed at a folded wallet is redirected onto that wallet's cluster
    const spend = folded.edges.find((e) => e.kind === "SPENDS" && e.src === "tx:4f2a9c3e")!;
    expect(spend.dst).toBe("cluster:12");
  });

  it("blooms exactly one cluster's members when it is expanded, and no others", () => {
    const folded = fold(GRAPHS.default, new Set(["cluster:12"]));
    const shown = folded.nodes.filter((n) => n.kind === "address").map((n) => n.node_id);
    expect(shown).toContain("addr:bc1q4f");
    expect(shown.every((id) => folded.memberOf.get(id) === "cluster:12")).toBe(true);
  });
});

describe("graph semantics", () => {
  it("marks the SAME_OWNER heuristic visibly weaker than a confirmed value transfer", () => {
    const same = GRAPHS.default.edges.find((e) => e.kind === "SAME_OWNER")!;
    const spend = GRAPHS.default.edges.find((e) => e.kind === "SPENDS")!;
    expect(edgeBaseOpacity(same)).toBeLessThan(edgeBaseOpacity(spend));
    expect(EDGE_STROKE.SAME_OWNER).toBe("dashed"); // never solid — not equal to an observed spend
    expect(EDGE_STROKE.ANNOUNCED_BY).toBe("dotted");
  });
});

describe("GRAPH screen", () => {
  it("renders the fused graph, lets the layer toggle switch, and labels the origin path", async () => {
    render(<Graph />);
    // the origin peer is on the path, so its label renders without hovering
    expect(await screen.findByText("103.x.x.x")).toBeInTheDocument();
    // the three layer modes are present; BOTH starts active
    expect(screen.getByRole("button", { name: "CHAIN" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "BOTH" })).toHaveAttribute("data-active");
    fireEvent.click(screen.getByRole("button", { name: "NETWORK" }));
    expect(screen.getByRole("button", { name: "NETWORK" })).toHaveAttribute("data-active");
  });

  it("opens the selected node in the aside and never invents a metric", async () => {
    render(<Graph />);
    fireEvent.click(await screen.findByText("103.x.x.x"));
    const aside = screen.getByRole("complementary");
    await waitFor(() => expect(aside.textContent).toMatch(/peer/i)); // KIND_WORD, uppercased to match the canvas caption
    expect(aside.textContent).toMatch(/on estimated-origin path/);
    expect(aside.textContent).not.toContain("%");
  });

  it("states aggregation explicitly when the adapter aggregates above the node cap", async () => {
    vi.spyOn(adapter, "getGraph").mockResolvedValueOnce(GRAPHS.aggregated);
    render(<Graph />);
    expect(await screen.findByText(/AGGREGATED · 4,912 addresses in 318 clusters/)).toBeInTheDocument();
    vi.restoreAllMocks();
  });
});
