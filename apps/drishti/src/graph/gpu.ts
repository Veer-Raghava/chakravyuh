/**
 * GPU path seam. DRISHTI-SPEC section 4 calls for cosmos.gl on the GPU above the node cap.
 * cosmos.gl is not vendored — the console must run air-gapped and we do not add a runtime
 * dependency for it here — so this reports "unavailable" and the SVG fallback renders the
 * complete experience on every machine, which is the hard requirement (spec rule 12).
 *
 * When cosmos.gl is vendored into `vendor/`, implement `mountGpuGraph` to draw with it,
 * seeded from the same `computeBase` layout and the same `semantics` maps, and flip
 * `gpuAvailable` to a real capability probe. Nothing else in the screen changes.
 */
import { GRAPH_NODE_CAP } from "../adapter";

export const GPU_NODE_CAP = GRAPH_NODE_CAP;

/** True only when a real GPU renderer is vendored and the context is usable. */
export function gpuAvailable(): boolean {
  return false;
}
