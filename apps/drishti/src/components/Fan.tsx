import { useMemo } from "react";
import type { OriginEstimate } from "../adapter";
import { dec, id } from "../format";
import styles from "./Fan.module.css";

interface Props {
  estimate: OriginEstimate;
  /** The reveal is gated to a keypress by the caller; this component never self-arms. */
  revealed: boolean;
  /** When true, transitions are removed and the end state is shown at once. */
  reduceMotion?: boolean;
}

/** Axis ticks derived from window_ms — a scale, not hardcoded values. Every ~2s up to
 *  the window, so a 12s window reads 0 · 2s · 4s … 12s. */
function axisTicks(windowMs: number): number[] {
  const step = 2000;
  const ticks: number[] = [];
  for (let t = 0; t <= windowMs; t += step) ticks.push(t);
  return ticks;
}

const secLabel = (ms: number) => (ms === 0 ? "0" : `${ms / 1000}s`);

/**
 * The origin timeline fan. One horizontal lane per announcing peer, ordered by first-seen
 * time (top = earliest). x-axis is milliseconds since the first announcement of this txid.
 *
 * The reveal is one stroke width and one colour, deliberately: the rank-1 lane thickens to
 * --signal and gains its probability + interval; the rank-2 lane keeps a --line-hi stroke
 * and its own probability; every other lane recedes to --ink-mute. A bracket between #1 and
 * #2 draws the margin the estimator is actually confident about.
 *
 * The lane probabilities are independent estimates and DO NOT sum to 1 — there is no total,
 * no percentage-of-whole and no stacked bar anywhere here, by design.
 */
export function Fan({ estimate, revealed, reduceMotion }: Props) {
  const { lanes, window_ms, abstain, p_interval, margin } = estimate;
  const ticks = useMemo(() => axisTicks(window_ms), [window_ms]);

  // Lane order is the first-seen order the adapter already sorts by. The bracket is placed
  // by lane INDEX (not rank) so it lands on the actual rows, wherever #1 and #2 sit.
  const i1 = lanes.findIndex((l) => l.rank === 1);
  const i2 = lanes.findIndex((l) => l.rank === 2);
  const showBracket = revealed && !abstain && i1 >= 0 && i2 >= 0 && margin != null;

  // %-of-height offsets so the bracket tracks the two lanes at any container size.
  const n = lanes.length;
  const bracketTop = i1 >= 0 ? ((Math.min(i1, i2) + 0.5) / n) * 100 : 0;
  const bracketHeight = i1 >= 0 && i2 >= 0 ? (Math.abs(i2 - i1) / n) * 100 : 0;

  return (
    <div
      className={styles.fan}
      data-revealed={revealed || undefined}
      data-abstain={abstain || undefined}
      data-reduce={reduceMotion || undefined}
    >
      <div className={styles.lanes}>
        {/* Faint time gridlines behind every lane, so a tick reads against the axis. */}
        <div className={styles.grid} aria-hidden="true">
          {ticks.map((t) => (
            <span key={t} className={styles.gridline} style={{ left: `${(t / window_ms) * 100}%` }} />
          ))}
        </div>

        {lanes.map((lane) => {
          const state =
            abstain ? "abstain" : lane.rank === 1 ? "origin" : lane.rank === 2 ? "runner" : "other";
          const pText =
            lane.rank === 1 && p_interval
              ? `p = ${dec(lane.p_origin)}  [${dec(p_interval[0])}, ${dec(p_interval[1])}]`
              : lane.rank === 2
                ? `p = ${dec(lane.p_origin)}`
                : "";
          return (
            <div className={styles.lane} key={`${lane.peer_ip}:${lane.peer_port}`} data-state={state}>
              <div className={styles.label}>
                <span className={`${styles.peer} mono`}>
                  {id(lane.peer_ip, "ip")}:{lane.peer_port}
                </span>
                <span className={styles.meta}>
                  {lane.asn != null && <span className="mono">AS{lane.asn}</span>}
                  {lane.geo_country && <span>{lane.geo_country}</span>}
                </span>
              </div>

              <div className={styles.track}>
                <span className={styles.baseline} aria-hidden="true" />
                {lane.announce_times_ms.map((t, k) => (
                  <span
                    key={k}
                    className={styles.tick}
                    data-first={k === 0 || undefined}
                    style={{ left: `${(t / window_ms) * 100}%` }}
                    title={`${t} ms`}
                  />
                ))}
              </div>

              {/* Probability rides at the right edge of the lane, revealed on keypress.
                  Nothing is rendered until the reveal, so no estimate exists in the DOM
                  before the user asks for it. */}
              <div className={`${styles.pval} mono`} data-show={revealed && !!pText}>
                {revealed ? pText : ""}
              </div>
            </div>
          );
        })}

        {showBracket && (
          <div
            className={styles.bracket}
            style={{ top: `${bracketTop}%`, height: `${bracketHeight}%` }}
            aria-hidden="true"
          >
            <span className={`${styles.bracketVal} mono`}>margin {dec(margin!)}</span>
          </div>
        )}
      </div>

      <div className={styles.axis} aria-hidden="true">
        {ticks.map((t) => (
          <span key={t} className={`${styles.axisTick} mono`} style={{ left: `${(t / window_ms) * 100}%` }}>
            {secLabel(t)}
          </span>
        ))}
        <span className={styles.axisCaption}>ms since first announcement</span>
      </div>
    </div>
  );
}
