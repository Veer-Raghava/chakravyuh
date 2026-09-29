import { useRef } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRun } from "../../data/RunContext";
import { usToIST } from "../../data/jaal";
import { usePrefersReducedMotion } from "../../scroll/usePrefersReducedMotion";
import styles from "./UntangleScreen.module.css";

/**
 * Untangle · SETU (§11.2) — "network vs money". One messy captured row is really
 * two things — what the NETWORK saw and what the MONEY did. SETU pulls them apart,
 * and renames one column: src_ip → "the IP that told us" (the rename is the whole
 * lesson). We show the echo (one transaction, many IPs claim to have seen it) and
 * keep null ≠ 0 ≠ unknown honest. Mostly a readout; the rename is the headline.
 */
export function UntangleScreen() {
  const reduced = usePrefersReducedMotion();
  const root = useRef<HTMLDivElement>(null);
  const { fixtures } = useRun();

  const col = fixtures.collapse;
  const o = fixtures.alert.origin;

  const echoPct = ((col.echo / col.announcements) * 100).toFixed(1);
  const meanPerTx = col.mean_announcements_per_tx.toFixed(1);

  // the six real announcing peers for this one transaction = echo, made concrete.
  const lanes = [...o.shortlist].sort((a, b) => (a.announcements_ms[0] ?? 0) - (b.announcements_ms[0] ?? 0));
  const heardAt = (ms: number) => usToIST(o.first_seen_us + ms * 1000);

  useGSAP(
    () => {
      if (reduced || !root.current) return;
      gsap
        .timeline({ defaults: { ease: "power2.out" } })
        .from(`.${styles.raw}`, { opacity: 0, x: -20, duration: 0.5 })
        .from(`.${styles.rename}`, { opacity: 0, scale: 0.8, duration: 0.5 }, "-=0.2")
        .from(`.${styles.table}`, { opacity: 0, x: 24, duration: 0.5, stagger: 0.15 }, "-=0.2")
        .from(`.${styles.laneRow}`, { opacity: 0, y: 8, duration: 0.35, stagger: 0.05 }, "-=0.3");
    },
    { dependencies: [reduced], scope: root },
  );

  return (
    <section className={styles.screen} ref={root}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>Untangle</h1>
          <span className={styles.tag}>SETU · सेतु</span>
        </div>
        <p className={styles.gloss}>
          One captured row holds two things at once: what the network saw, and what the money
          did. SETU pulls them apart.
        </p>
      </header>

      <div className={styles.echo}>
        <div className={styles.echoStat}>
          <span className={styles.echoNum}>{meanPerTx}</span>
          <span className={styles.echoLabel}>announcements per transaction, on average</span>
        </div>
        <div className={styles.echoStat}>
          <span className={styles.echoNum}>{echoPct}%</span>
          <span className={styles.echoLabel}>are echoes: the same tx, re-announced</span>
        </div>
        <p className={styles.echoLine}>
          {new Intl.NumberFormat("en-US").format(col.announcements)} announcements collapse to{" "}
          {new Intl.NumberFormat("en-US").format(col.transactions)} real transactions.
        </p>
      </div>

      <div className={styles.split}>
        {/* BEFORE — one raw observation, wire + money tangled */}
        <div className={styles.raw}>
          <span className={styles.side}>one raw observation · as captured</span>
          <dl className={styles.rawRows}>
            <div className={styles.rawRow}><dt>timestamp</dt><dd>{heardAt(0)}</dd></div>
            <div className={`${styles.rawRow} ${styles.highlight}`}>
              <dt>src_ip</dt><dd>{lanes[0].peer_ip_display}</dd>
            </div>
            <div className={styles.rawRow}><dt>src_port</dt><dd>{lanes[0].peer_port}</dd></div>
            <div className={styles.rawRow}><dt>asn</dt><dd>{lanes[0].asn}</dd></div>
            <div className={styles.rawRow}><dt>geo_country</dt><dd>{lanes[0].geo_country}</dd></div>
            <div className={styles.rawRow}><dt>txid</dt><dd>{o.txid_display}</dd></div>
          </dl>
        </div>

        {/* THE RENAME — the headline transformation */}
        <div className={styles.rename}>
          <code className={styles.oldName}>src_ip</code>
          <span className={styles.arrow} aria-hidden>↓</span>
          <span className={styles.newName}>the IP that told us</span>
          <span className={styles.renameNote}>a rename that defuses the trap</span>
        </div>

        {/* AFTER — two clean tables */}
        <div className={styles.tables}>
          <div className={styles.table}>
            <div className={styles.tableHead}>
              <span className={styles.floor}>THE WIRE</span>
              <span className={styles.floorSub}>who told us · {lanes.length} IPs, one tx</span>
            </div>
            <div className={`${styles.laneRow} ${styles.laneHeader}`}>
              <span>the IP that told us</span>
              <span>port</span>
              <span className={styles.tipCol}>
                network operator (ASN)
                <span className={styles.tip} tabIndex={0} role="note" aria-label="null is not unknown">
                  ?
                  <span className={styles.tipBody}>
                    A blank operator means we never resolved it. That is not zero, and not an
                    “unknown” we looked for and failed to find. <strong>null ≠ 0 ≠ unknown.</strong>
                  </span>
                </span>
              </span>
              <span>heard at</span>
            </div>
            {lanes.map((l) => (
              <div key={l.peer_ip + l.peer_port} className={styles.laneRow}>
                <span className={styles.pink}>{l.peer_ip_display}</span>
                <span>{l.peer_port}</span>
                <span>{l.asn ?? <em className={styles.null}>null</em>}</span>
                <span className={styles.dim}>{heardAt(l.announcements_ms[0] ?? 0)}</span>
              </div>
            ))}
          </div>

          <div className={styles.table}>
            <div className={styles.tableHead}>
              <span className={styles.floor}>THE MONEY</span>
              <span className={styles.floorSub}>one transaction</span>
            </div>
            <div className={`${styles.laneRow} ${styles.txRow}`}>
              <span className={styles.mono}>{o.txid_display}</span>
            </div>
            <dl className={styles.txMeta}>
              <div className={styles.txMetaRow}><dt>first seen</dt><dd>{heardAt(0)}</dd></div>
              <div className={styles.txMetaRow}><dt>announced by</dt><dd>{lanes.length} distinct IPs</dd></div>
            </dl>
          </div>
        </div>
      </div>

      <p className={styles.lesson}>
        The earliest IP to announce a transaction is usually a <strong>relay</strong> passing it
        on, not the sender. That confusion is the trap SETU defuses.
      </p>
    </section>
  );
}
