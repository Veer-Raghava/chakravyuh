// The Sutra's stops — the app's ONE nav source of truth (§11.0). Workflow-ordered,
// not alphabetised: Globe (home) → the seven pipeline stops in the order an officer
// works a case → World (MAYAJAAL) pinned far right as the ambient "about the engine"
// destination. Funnel counts are the canonical numbers (§ "Canonical numbers"),
// reused from the landing so the story's spine becomes the tool's navigation.

export type StageId =
  | "globe"
  | "intake"
  | "untangle"
  | "map"
  | "origin"
  | "leads"
  | "proof"
  | "world";

export type Stage = {
  id: StageId;
  /** Plain-English word shown on the thread (§3 vocabulary). */
  name: string;
  /** Tiny mono Sanskrit tag under the word. Empty for Globe (home). */
  tag: string;
  /** One-line gloss for the screen header + aperture. */
  gloss: string;
  /** The funnel bead's value while this stage holds — 1,000,000 → 1. null = ambient. */
  count: number | null;
};

// The seven pipeline stops form the funnel spine; Globe + World sit outside it.
export const STAGES: Stage[] = [
  { id: "globe", name: "Globe", tag: "", gloss: "the world of transactions", count: 1_000_000 },
  { id: "intake", name: "Intake", tag: "KAVACH", gloss: "load & seal a dataset", count: 999_847 },
  { id: "untangle", name: "Untangle", tag: "SETU", gloss: "network vs money", count: 111_043 },
  { id: "map", name: "Map", tag: "JAAL", gloss: "the connection map", count: 24_626 },
  { id: "origin", name: "Origin", tag: "SHASTRA", gloss: "who sent it — or honestly, we don't know", count: 10_220 },
  { id: "leads", name: "Leads", tag: "VAANI", gloss: "the ranked lead queue", count: 20 },
  { id: "proof", name: "Proof", tag: "PRAMAAN", gloss: "the court-ready proof", count: 1 },
  { id: "world", name: "World", tag: "MAYAJAAL", gloss: "the synthetic world we built", count: null },
];

/** World is pinned right, outside the funnel order — the thread proper is the first seven. */
export const THREAD_STAGES = STAGES.filter((s) => s.id !== "world");
export const WORLD_STAGE = STAGES.find((s) => s.id === "world")!;

export const indexOf = (id: StageId) => STAGES.findIndex((s) => s.id === id);
