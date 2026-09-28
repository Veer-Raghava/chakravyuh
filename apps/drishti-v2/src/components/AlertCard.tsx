import type { CSSProperties, ReactNode } from "react";
import { fixtures } from "../data/loader";
import styles from "./AlertCard.module.css";

/**
 * The reusable Alert card (§11.0) — first seen at landing station 6 (VAANI), now
 * the one component the tool reuses in Leads, in the Properties drawer, and in the
 * packet. Build once, reuse everywhere. Reads the single-alert fixture: what
 * happened, the network detail, why flagged, the teal counter-evidence beside it,
 * and an honest origin line.
 *
 * Two backend fields are first-class here, not footnotes (§6):
 *  - would_clear on a counter — "this one doubt is enough to close the lead"
 *  - attribution_ready — gates the {operator · region · UTC} hero; false = honest not-ready.
 * Attribution leads with the network operator (ASN) + region + shortlist size, never the
 * exact host (§2) — the full IP/port live only in packet.json and are never rendered.
 * All identifiers are the backend's *_display forms (truncated per §9); we never
 * render a full identifier on screen.
 */
const RISK = { high: "var(--coral)", med: "var(--butter)", low: "var(--riso-blue)" } as const;

function utcMicrosToUTC(us: number): string {
  // _us fields are UTC microseconds (int64). Convert only at the render layer.
  return new Date(us / 1000).toISOString().slice(0, 19).replace("T", " ") + "Z";
}

export function AlertCard({ footer }: { footer?: ReactNode }) {
  const a = fixtures.alert;
  const o = a.origin;
  const risk = RISK[a.severity as keyof typeof RISK] ?? RISK.high;
  const clearing = a.counters.find((c) => c.would_clear);

  return (
    <article className={styles.card} style={{ "--risk": risk } as CSSProperties}>
      <div className={styles.severityEdge} />

      <header className={styles.head}>
        <span className={styles.score}>{a.conf_high.toFixed(2)}</span>
        <span className={styles.severity}>{a.severity.toUpperCase()}</span>
        <span className={styles.subject}>{a.subject_display}</span>
      </header>

      <p className={styles.headline}>{a.headline}</p>

      {/* the {operator · region · UTC} hero — gated by attribution_ready (§6) */}
      {a.attribution_ready ? (
        <div className={styles.attribution}>
          <span className={styles.attrLabel}>attribution ready</span>
          <span className={styles.attrValue}>
            AS{o.attribution.asn} · {o.attribution.geo_country} · {utcMicrosToUTC(o.first_seen_us)}
          </span>
        </div>
      ) : (
        <div className={`${styles.attribution} ${styles.notReady}`}>
          <span className={styles.attrLabel}>attribution not ready</span>
          <span className={styles.attrValue}>operator, region and precise time not all present</span>
        </div>
      )}

      <dl className={styles.rows}>
        <div className={styles.row}>
          <dt>origin</dt>
          <dd>
            {o.abstain ? (
              <span className={styles.abstain}>No answer available</span>
            ) : (
              <>
                AS{o.attribution.asn} · {o.attribution.geo_country} · operator likelihood{" "}
                {(o.attribution.p_asn * 100).toFixed(2)}% · shortlist of {o.shortlist.length}
              </>
            )}
          </dd>
        </div>
        <div className={styles.row}>
          <dt>why flagged</dt>
          <dd className={styles.why}>{a.features[0]?.statement}</dd>
        </div>
      </dl>

      {/* counter-evidence beside every "why flagged" — shown at the same moment (§6) */}
      <div className={styles.counters}>
        <span className={styles.counterLabel}>why it might be innocent</span>
        {a.counters.slice(0, 2).map((c, i) => (
          <p key={i} className={styles.counter}>
            {c.statement}
          </p>
        ))}
      </div>

      {clearing && (
        <p className={styles.wouldClear}>One doubt is enough to close this lead: {clearing.statement}</p>
      )}

      {footer && <div className={styles.footer}>{footer}</div>}
    </article>
  );
}
