// The single seam between the new console and its data.
// These JSON files are the backend's real committed UI fixtures (seed 42, ~25 txs),
// produced by scripts/export_ui_fixtures.py off the same serializer the live API uses,
// so shapes match DATA-CONTRACTS.md by construction. Copied from data/fixtures/ui/.
//
// UNITS (do not violate): money = satoshis (int64) -> format to BTC only at render.
// times = UTC microseconds (`_us`, int64) -> convert to IST only at render.
// null != 0 != "unknown". Identifiers use RFC documentation ranges; truncate per
// DATA-CONTRACTS §9 at the DISPLAY layer, never in the data.
//
// tsconfig needs: "resolveJsonModule": true, "esModuleInterop": true.
// When a live backend lands, swap these imports for fetch() behind the same names.

import manifest from "./fixtures/manifest.json";
import collapse from "./fixtures/collapse.json";
import transactions from "./fixtures/transactions.json";
import graph from "./fixtures/graph.json";
import graphAddress from "./fixtures/graph-address.json";
import origin from "./fixtures/origin.json";
import originAbstain from "./fixtures/origin-abstain.json";
import alerts from "./fixtures/alerts.json";
import alert from "./fixtures/alert.json";
import packet from "./fixtures/packet.json";
import world from "./fixtures/world.json";

export const fixtures = {
  manifest,
  world, // canonical numbers (funnel, ceiling, observer-fraction curve) — one source
  collapse,
  transactions,
  graph, // fused peer/money graph, aggregated above the node cap
  graphAddress, // address-only view
  origin, // confident case
  originAbstain, // "No answer available" case
  alerts,
  alert, // single alert detail (evidence + counter, with would_clear)
  packet, // court-ready proof; merkle_head/signature printed in full
};

export type Fixtures = typeof fixtures;
export default fixtures;
