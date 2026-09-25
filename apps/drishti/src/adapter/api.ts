/**
 * Live API adapter. Every screen already reads through this shape; the bodies land
 * with S04 (the FastAPI read-only server on 127.0.0.1:8000). Until then each call
 * throws, so a misconfigured VITE_SOURCE=api fails loudly instead of rendering blanks.
 */
import type { Adapter } from "./types";

const BASE = "http://127.0.0.1:8000";

const notBuilt = (): never => {
  throw new Error("API not built yet");
};

export const apiAdapter: Adapter = {
  getManifest: notBuilt,
  getCollapseStats: notBuilt,
  listTransactions: notBuilt,
  getOriginEstimate: notBuilt,
  getGraph: notBuilt,
  listAlerts: notBuilt,
  getAlert: notBuilt,
  getPacket: notBuilt,
  listLineageRecords: notBuilt,
  getLineage: notBuilt,
  listRuns: notBuilt,
  setActiveRun: notBuilt,
  launchRun: notBuilt,
  getRows: notBuilt,
};

export { BASE as API_BASE };
