/**
 * The single seam between the console and its data. Track B builds every screen against
 * `fixtures`; the switch to live data is one environment variable and nothing else.
 */
import type { Adapter } from "./types";
import { fixturesAdapter } from "./fixtures";
import { apiAdapter } from "./api";

const source = import.meta.env.VITE_SOURCE ?? "fixtures";

export const adapter: Adapter = source === "api" ? apiAdapter : fixturesAdapter;
export const ADAPTER_SOURCE = source;

export * from "./types";
