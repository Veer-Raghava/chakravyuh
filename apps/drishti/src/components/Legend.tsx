/**
 * The key to the visual grammar, so the graph explains itself: which shape is a wallet, a
 * transaction, a peer; which stroke is money, an announcement, a heuristic guess. Every
 * swatch is the ACTUAL glyph/stroke the canvas draws (same NODE_GEOM shapes, same stroke
 * classes), never a hand-drawn stand-in, so the legend can never drift from the picture.
 * Colour is deliberately absent here too — shape and stroke carry meaning, the one accent
 * stays reserved for the origin path on the canvas itself.
 */
import type { GraphNode } from "../adapter";
import { NODE_GEOM, KIND_WORD } from "../graph/semantics";
import fg from "./ForceGraph.module.css";
import styles from "./Legend.module.css";

const SHAPES: GraphNode["kind"][] = ["transaction", "address", "cluster", "peer", "asn"];

// Small glyph, centred in a 32x24 box, reusing the canvas Glyph geometry at legend scale.
function Swatch({ kind }: { kind: GraphNode["kind"] }) {
  const g = NODE_GEOM[kind];
  const s = Math.min(g.size, kind === "cluster" ? 14 : 12); // clamp so the row height is even
  const round = g.shape === "circle" || g.shape === "hollow-circle";
  return (
    <svg className={styles.swatch} viewBox="-16 -12 32 24" aria-hidden="true">
      {round ? (
        <circle r={s / 2} className={fg.glyph} data-shape={g.shape} />
      ) : (
        <rect
          x={-s / 2}
          y={-s / 2}
          width={s}
          height={s}
          rx={2}
          className={fg.glyph}
          data-shape={g.shape}
          transform={g.shape === "diamond" ? "rotate(45)" : undefined}
        />
      )}
    </svg>
  );
}

// A stroke sample drawn with the real edge classes, so dotted/dashed/hair read exactly as on
// the canvas. The money-flow sample carries a small arrowhead matching the graph's markers.
function Line({ stroke, arrow }: { stroke: string; arrow?: boolean }) {
  return (
    <svg className={styles.line} viewBox="0 0 32 12" aria-hidden="true">
      <path d="M2,6 L28,6" className={fg.edge} data-stroke={stroke} />
      {arrow && <path d="M26,3 L31,6 L26,9" className={styles.arrow} />}
    </svg>
  );
}

export function Legend() {
  return (
    <div className={styles.legend} aria-label="legend">
      <div className={styles.col}>
        {SHAPES.map((k) => (
          <div key={k} className={styles.item}>
            <Swatch kind={k} />
            <span className={styles.word}>{KIND_WORD[k]}</span>
          </div>
        ))}
      </div>
      <div className={styles.col}>
        <div className={styles.item}>
          <Line stroke="solid" arrow />
          <span className={styles.word}>money flow</span>
        </div>
        <div className={styles.item}>
          <Line stroke="dotted" />
          <span className={styles.word}>announced</span>
        </div>
        <div className={styles.item}>
          <Line stroke="dashed" />
          <span className={styles.word}>same owner?</span>
        </div>
        <div className={styles.item}>
          <Line stroke="hair" />
          <span className={styles.word}>structure</span>
        </div>
      </div>
    </div>
  );
}
