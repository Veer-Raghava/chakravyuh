import { useCallback, useEffect, useMemo, useState } from "react";
import { adapter, type Manifest, type OriginEstimate, type TransactionRow } from "../adapter";
import { StatusBar } from "../components/StatusBar";
import { CommandLine, type LastCall } from "../components/CommandLine";
import { Fan } from "../components/Fan";
import { MetricReadout } from "../components/MetricReadout";
import { dec, id } from "../format";
import styles from "./Origin.module.css";

const reduceMotion = () =>
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// Reason code -> the plain clause the abstain readout shows. Only tor is required today;
// an unknown reason falls back to the raw code rather than inventing a sentence.
const ABSTAIN_CLAUSE: Record<string, string> = {
  tor_present: "observed peer is a Tor exit",
};

const RELAY_NOTE =
  "Announcement order is noisy by design. Bitcoin Core delays each announcement to each peer " +
  "by an independent random wait, so first-seen alone is weak. The estimate uses order, spread, " +
  "and who did not see it.";

/** One selectable case: the transaction row plus the estimate that qualified it. */
interface Case {
  tx: TransactionRow;
  estimate: OriginEstimate;
}

export function Origin() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [cases, setCases] = useState<Case[]>([]);
  const [selected, setSelected] = useState(0);
  const [estimate, setEstimate] = useState<OriginEstimate | null>(null);
  const [armed, setArmed] = useState(false); // the reveal, gated to a keypress — never on mount
  const [last, setLast] = useState<LastCall | null>(null);

  // Build the selector from the transactions that actually carry an origin estimate: ask
  // for each txid's estimate and keep only the ones the adapter answered for (est.txid ===
  // txid), so a transaction with no estimate never shows a borrowed fan.
  useEffect(() => {
    adapter.getManifest().then(setManifest);
    adapter.listTransactions().then(async (txs) => {
      const qualified: Case[] = [];
      for (const tx of txs) {
        const est = await adapter.getOriginEstimate(tx.txid);
        if (est.txid === tx.txid) qualified.push({ tx, estimate: est });
      }
      setCases(qualified);
    });
  }, []);

  const current = cases[selected];

  // Re-fetch on selection so the CommandLine shows an honest per-call latency, and reset the
  // reveal: switching transactions must never carry the previous lane's highlight.
  useEffect(() => {
    if (!current) return;
    const t0 = performance.now();
    adapter.getOriginEstimate(current.tx.txid).then((est) => {
      setEstimate(est);
      setLast({ label: `getOriginEstimate(${current.tx.txid})`, ms: Math.round(performance.now() - t0) });
    });
    setArmed(false);
  }, [current?.tx.txid]);

  const move = useCallback(
    (dir: 1 | -1) => {
      setSelected((s) => (cases.length ? (s + (dir === 1 ? 1 : cases.length - 1)) % cases.length : 0));
    },
    [cases.length],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA")) return;
      if (e.key === "j" || e.key === "ArrowDown") return move(1);
      if (e.key === "k" || e.key === "ArrowUp") return move(-1);
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        return setArmed(true);
      }
      if (e.key === "Escape") return setArmed(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [move]);

  const rank1 = useMemo(() => estimate?.lanes.find((l) => l.rank === 1) ?? null, [estimate]);
  const revealed = armed && !!estimate && !estimate.abstain;

  if (!estimate || !current) {
    return (
      <div className={styles.page}>
        <StatusBar manifest={manifest} />
        <div className={styles.loading}>loading origin estimate…</div>
        <CommandLine last={last} />
      </div>
    );
  }

  const abstain = estimate.abstain;
  const clause = estimate.abstain_reason ? (ABSTAIN_CLAUSE[estimate.abstain_reason] ?? estimate.abstain_reason) : "";

  return (
    <div className={styles.page}>
      <StatusBar manifest={manifest} />

      <div className={styles.head}>
        <span className={styles.crumb}>
          DRISHTI · /_origin · <span className="mono">{estimate.txid}</span>
        </span>
        <div className={styles.cases}>
          <span className={styles.casesLabel}>transaction j / k</span>
          {cases.map((c, i) => (
            <button
              key={c.tx.txid}
              className={styles.case}
              data-active={i === selected || undefined}
              onClick={() => setSelected(i)}
            >
              <span className="mono">{c.tx.txid}</span>
              <span className={styles.caseTag} data-abstain={c.tx.abstained || undefined}>
                {c.tx.abstained ? "ABSTAIN" : "attributable"}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className={styles.body}>
        <div className={styles.main}>
          <div className={styles.fanTitle}>
            <span className={styles.fanLabel}>ANNOUNCEMENT TIMELINE · {estimate.lanes.length} PEERS</span>
            {!abstain && (
              <span className={styles.hint} data-done={revealed || undefined}>
                {revealed ? "estimate shown" : "SPACE — reveal origin"}
              </span>
            )}
          </div>

          <div className={styles.fanWrap}>
            <Fan estimate={estimate} revealed={revealed} reduceMotion={reduceMotion()} />
          </div>

          <div className={styles.readouts}>
            {estimate.features.map((f) => (
              <MetricReadout
                key={f.label}
                label={f.label}
                value={f.value}
                gloss={f.gloss}
                tone={abstain ? "cool" : undefined}
              />
            ))}
          </div>

          <p className={styles.note}>{RELAY_NOTE}</p>
        </div>

        <aside className={styles.aside}>
          {abstain ? (
            <div className={styles.abstain}>
              <span className={styles.abstainMark}>ABSTAIN</span>
              <p className={styles.abstainSentence}>
                ABSTAIN · {clause} · origin not estimable
              </p>
              <p className={styles.abstainWhy}>
                The estimator refuses rather than guess. A tool that answers this transaction is
                less trustworthy than one that will not.
              </p>
            </div>
          ) : revealed && rank1 ? (
            <div className={styles.card}>
              <span className={styles.cardLabel}>ESTIMATED ORIGINATOR</span>
              <span className={`${styles.cardPeer} mono`}>
                {id(rank1.peer_ip, "ip")}:{rank1.peer_port}
              </span>
              <div className={styles.cardMeta}>
                {rank1.asn != null && (
                  <span className="mono">AS{rank1.asn}{rank1.as_org ? ` · ${rank1.as_org}` : ""}</span>
                )}
                {rank1.geo_country && <span>{rank1.geo_country}</span>}
                <span>{rank1.net_class}</span>
              </div>

              <div className={styles.cardDivider} aria-hidden="true" />

              <span className={styles.cardPLabel}>PROBABILITY OF ORIGIN</span>
              <div className={styles.cardP}>
                <span className={`${styles.cardPBig} mono`}>{dec(rank1.p_origin)}</span>
                {estimate.p_interval && (
                  <span className={`${styles.cardPInt} mono`}>
                    [{dec(estimate.p_interval[0])}, {dec(estimate.p_interval[1])}]
                  </span>
                )}
              </div>
              {estimate.margin != null && (
                <span className={`${styles.cardMargin} mono`}>margin {dec(estimate.margin)} over the runner-up</span>
              )}
            </div>
          ) : (
            <div className={styles.prompt}>
              <span className={styles.promptKey}>SPACE</span>
              <p className={styles.promptText}>
                {estimate.lanes.length} peers announced this transaction. Reveal which one the
                estimator believes sent it — and how far ahead of the next.
              </p>
            </div>
          )}
        </aside>
      </div>

      <CommandLine last={last} />
    </div>
  );
}
