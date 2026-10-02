import { useRun } from "../../data/RunContext";
import { useShell } from "../ShellContext";
import type { GlobeTx, GlobePoint } from "../../data/globe";
import styles from "./GlobeDetail.module.css";

/**
 * The Properties-drawer body for a clicked globe point/arc (§9). Sender (origin
 * likelihood + shortlist, or a dignified "No answer available"), the announcing IP
 * redacted to the backend form + port + operator (ASN), the truncated txid, and
 * fee / first-seen in mono. Units convert at THIS layer only: sats→BTC, _us→IST.
 * Two honest handoffs: Open in map → the graph (§10); Build proof → the packet.
 */

// satoshis (int64) → BTC string. Integer math only until the final divide (display).
function satsToBTC(sats: number): string {
  const btc = sats / 100_000_000;
  return `${btc.toFixed(8)} BTC`;
}

// _us are UTC microseconds; render human IST (Asia/Kolkata) only here.
function usToIST(us: number): string {
  return (
    new Intl.DateTimeFormat("en-IN", {
      timeZone: "Asia/Kolkata",
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(us / 1000)) + " IST"
  );
}

const REASON_GLOSS: Record<string, string> = {
  margin_below_floor: "the top candidates were too close together to name one",
};

export function GlobeDetail({ tx, focus }: { tx: GlobeTx; focus?: GlobePoint }) {
  const { goTo, closeDrawer } = useShell();
  const { selectTx } = useRun();
  const jump = (id: "map" | "origin") => {
    selectTx(tx.txid);
    closeDrawer();
    goTo(id);
  };

  // shortlist = candidates by rank; located leaders first. Never a lone name (§6).
  const shortlist = [...tx.points].sort((a, b) => a.rank - b.rank).slice(0, 3);
  const announcer = focus ?? shortlist[0];

  return (
    <div className={styles.wrap}>
      {/* Sender / origin — the honest heart of the panel */}
      <section className={styles.block}>
        <span className={styles.label}>sender</span>
        {tx.abstain ? (
          <div className={styles.abstain}>
            <span className={styles.abstainTag}>No answer available</span>
            <p className={styles.abstainWhy}>
              {REASON_GLOSS[tx.abstainReason] ?? "the estimate did not clear the confidence floor"}.
            </p>
          </div>
        ) : (
          <div className={styles.origin}>
            <span className={styles.originIp}>{tx.originDisplay}</span>
            <span className={styles.likelihood}>origin likelihood {(tx.pOrigin * 100).toFixed(1)}%</span>
            <div className={styles.bar} aria-hidden="true">
              <span className={styles.barFill} style={{ width: `${Math.min(100, tx.pOrigin * 100)}%` }} />
            </div>
          </div>
        )}

        <span className={styles.subLabel}>shortlist</span>
        <ol className={styles.shortlist}>
          {shortlist.map((p) => (
            <li
              key={p.ipSeed}
              className={`${styles.candidate} ${p.isLeader ? styles.leader : ""} ${
                announcer && p.ipSeed === announcer.ipSeed ? styles.focused : ""
              }`}
            >
              <span className={styles.candIp}>{p.ipDisplay}</span>
              <span className={styles.candMeta}>
                {p.country ?? "unlocated"} · AS{p.asn}
              </span>
              <span className={styles.candP}>{(p.pOrigin * 100).toFixed(1)}%</span>
            </li>
          ))}
        </ol>
      </section>

      {/* The announcing IP — redacted to the backend display form (§9) */}
      {announcer && (
        <section className={styles.block}>
          <span className={styles.label}>announcing IP · the IP that told us</span>
          <dl className={styles.rows}>
            <div className={styles.row}>
              <dt>address</dt>
              <dd className={styles.mono}>{announcer.ipDisplay}</dd>
            </div>
            <div className={styles.row}>
              <dt>source port</dt>
              <dd className={styles.mono}>{announcer.port}</dd>
            </div>
            <div className={styles.row}>
              <dt>network operator (ASN)</dt>
              <dd className={styles.mono}>
                AS{announcer.asn}
                {announcer.country ? ` · ${announcer.country}` : ""}
              </dd>
            </div>
          </dl>
        </section>
      )}

      {/* The transaction — truncated txid, fee + time in mono */}
      <section className={styles.block}>
        <span className={styles.label}>transaction</span>
        <dl className={styles.rows}>
          <div className={styles.row}>
            <dt>txid</dt>
            <dd className={styles.mono}>{tx.txidDisplay}</dd>
          </div>
          <div className={styles.row}>
            <dt>fee</dt>
            <dd className={styles.mono}>{tx.feeSats != null ? satsToBTC(tx.feeSats) : "—"}</dd>
          </div>
          <div className={styles.row}>
            <dt>first seen</dt>
            <dd className={styles.mono}>{usToIST(tx.firstSeenUs)}</dd>
          </div>
          <div className={styles.row}>
            <dt>announcements</dt>
            <dd className={styles.mono}>{tx.nAnnouncements}</dd>
          </div>
        </dl>
        <p className={styles.honest}>
          Receiving addresses are money-side detail; follow this tx into the map to see them.
        </p>
      </section>

      <div className={styles.actions}>
        <button type="button" className={styles.primary} onClick={() => jump("map")}>
          Open in map →
        </button>
        <button type="button" className={styles.ghost} onClick={() => jump("origin")}>
          Compare origin candidates
        </button>
      </div>
    </div>
  );
}
