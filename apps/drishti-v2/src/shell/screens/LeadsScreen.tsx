import { useMemo, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { fixtures } from "../../data/loader";
import { AlertCard } from "../../components/AlertCard";
import { useShell } from "../ShellContext";
import { usePrefersReducedMotion } from "../../scroll/usePrefersReducedMotion";
import styles from "./LeadsScreen.module.css";

/**
 * Leads · VAANI (§11.4) — "the ranked queue". The screen an officer lives in:
 * ~20 ranked leads, not a thousand maybes. The top lead is the full reusable
 * Alert card (evidence + its own teal counter-evidence, shown at the same moment);
 * below it a compact ranked list. Default sort = "act on this first." No global
 * model report card anywhere (§6) — risk shows only as per-lead reasoning.
 */
type QueueAlert = (typeof fixtures.alerts.alerts)[number];

const RISK: Record<string, string> = { high: "var(--coral)", med: "var(--butter)", low: "var(--riso-blue)" };
const SHOWN = 20;

type SortKey = "risk" | "confidence" | "cluster";
const SORTS: { key: SortKey; label: string }[] = [
  { key: "risk", label: "act on this first" },
  { key: "confidence", label: "confidence" },
  { key: "cluster", label: "group size" },
];

/** Display-layer rename (§3 kill-list: "cluster" never on the officer screen). The
 *  backend id `cluster:616` is a likely-same-owner group; we render it as "group 616"
 *  and keep the "likely same owner" gloss on the badge. Same data, plain word. */
const subjectLabel = (s: string) => (s.startsWith("cluster:") ? `group ${s.slice(8)}` : s);

/** Same kill-list rename applied inside backend-authored prose: the bare word
 *  "cluster" → "owner group" (never "clustering", guarded by \b). Display-only. */
const scrub = (s: string) => s.replace(/\bcluster\b/gi, "owner group");

function sortAlerts(list: QueueAlert[], key: SortKey): QueueAlert[] {
  const copy = [...list];
  if (key === "risk") copy.sort((a, b) => b.risk_score - a.risk_score);
  else if (key === "confidence") copy.sort((a, b) => b.conf_high - a.conf_high || b.conf_low - a.conf_low);
  else copy.sort((a, b) => b.cluster_size - a.cluster_size);
  return copy;
}

/** Drawer body for a compact row — the summary the queue fixture carries, honestly
 *  labelled. Full evidence (factors, counters, origin lanes) is exported only for
 *  the featured lead in this fixture, so we say so rather than invent it. */
function LeadSummary({ a, actions }: { a: QueueAlert; actions: ReactNode }) {
  return (
    <div className={styles.summary}>
      <div className={styles.sumHead}>
        <span className={styles.sumScore} style={{ color: RISK[a.severity] }}>{a.risk_score.toFixed(2)}</span>
        <span className={styles.sumSeverity} style={{ color: RISK[a.severity], borderColor: RISK[a.severity] }}>
          {a.severity.toUpperCase()}
        </span>
        <span className={styles.sumSubject}>{subjectLabel(a.subject_display)}</span>
      </div>
      <p className={styles.sumHeadline}>{scrub(a.headline)}</p>
      <dl className={styles.sumRows}>
        <div className={styles.sumRow}><dt>network operator (ASN)</dt><dd>{a.origin_asn ?? "—"} · {a.origin_country ?? "—"}</dd></div>
        <div className={styles.sumRow}><dt>likely same owner</dt><dd>{a.cluster_size > 1 ? `${a.cluster_size} addresses` : "single address"}</dd></div>
        <div className={styles.sumRow}><dt>confidence band</dt><dd>{a.conf_low.toFixed(2)}–{a.conf_high.toFixed(2)}</dd></div>
        <div className={styles.sumRow}>
          <dt>attribution</dt>
          <dd className={a.attribution_ready ? styles.ready : styles.notReady}>
            {a.attribution_ready ? "ready" : "not ready"}
          </dd>
        </div>
      </dl>
      <p className={styles.sumNote}>
        Full evidence — factors, counter-evidence and origin candidates — is exported for the
        featured lead in this capture.
      </p>
      {actions}
    </div>
  );
}

export function LeadsScreen() {
  const { goTo, openDrawer } = useShell();
  const reduced = usePrefersReducedMotion();
  const [sort, setSort] = useState<SortKey>("risk");
  const [ready, setReady] = useState(false);
  const [clustered, setClustered] = useState(false);

  const featuredId = fixtures.alert.alert_id;
  const total = fixtures.alerts.alerts.length;

  const rows = useMemo(() => {
    let list = fixtures.alerts.alerts.filter((a) => a.alert_id !== featuredId);
    if (ready) list = list.filter((a) => a.attribution_ready);
    if (clustered) list = list.filter((a) => a.cluster_size > 1);
    return sortAlerts(list, sort).slice(0, SHOWN);
  }, [sort, ready, clustered, featuredId]);

  useGSAP(
    () => {
      if (reduced) return;
      gsap.from(`.${styles.row}`, { opacity: 0, y: 10, duration: 0.4, stagger: 0.04, ease: "power2.out" });
    },
    { dependencies: [rows, reduced] },
  );

  const actions = (
    <div className={styles.actions}>
      <button className={styles.actMap} type="button" onClick={() => goTo("map")}>Open in map →</button>
      <button className={styles.actProof} type="button" onClick={() => goTo("proof")}>Build proof</button>
    </div>
  );

  const openRow = (a: QueueAlert) =>
    openDrawer(`Lead · ${subjectLabel(a.subject_display)}`, <LeadSummary a={a} actions={actions} />);

  return (
    <section className={styles.screen}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>Leads</h1>
          <span className={styles.tag}>VAANI · वाणी</span>
        </div>
        <p className={styles.gloss}>
          {total} ranked leads — not a thousand maybes. Each answers “what do I do next” in a line,
          and shows its own doubts beside the evidence.
        </p>
      </header>

      <div className={styles.featured}>
        <span className={styles.featLabel}>act on this first</span>
        <AlertCard footer={actions} />
      </div>

      <div className={styles.controls}>
        <div className={styles.segmented} role="group" aria-label="Sort leads">
          {SORTS.map((s) => (
            <button
              key={s.key}
              type="button"
              className={`${styles.seg} ${sort === s.key ? styles.segOn : ""}`}
              onClick={() => setSort(s.key)}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className={styles.filters}>
          <button type="button" className={`${styles.filter} ${ready ? styles.filterOn : ""}`} onClick={() => setReady((v) => !v)}>
            attribution ready
          </button>
          <button type="button" className={`${styles.filter} ${clustered ? styles.filterOn : ""}`} onClick={() => setClustered((v) => !v)}>
            grouped
          </button>
        </div>
      </div>

      <p className={styles.count}>
        showing {rows.length} of {total - 1} — plus the featured lead above
      </p>

      <ul className={styles.list}>
        {rows.map((a) => (
          <li key={a.alert_id}>
            <button
              className={styles.row}
              type="button"
              style={{ "--risk": RISK[a.severity] } as CSSProperties}
              onClick={() => openRow(a)}
            >
              <span className={styles.edge} aria-hidden />
              <span className={styles.rank}>#{a.rank}</span>
              <span className={styles.rowScore}>{a.risk_score.toFixed(2)}</span>
              <span className={styles.rowMain}>
                <span className={styles.rowHeadline}>{scrub(a.headline)}</span>
                <span className={styles.rowMeta}>
                  {subjectLabel(a.subject_display)} · operator {a.origin_asn ?? "—"} · {a.origin_country ?? "—"}
                  {a.cluster_size > 1 && <span className={styles.cluster}> · likely same owner ·{a.cluster_size}</span>}
                </span>
              </span>
              {a.attribution_ready && <span className={styles.readyDot} title="attribution ready" aria-label="attribution ready" />}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
