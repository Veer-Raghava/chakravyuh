import { useEffect, useMemo, useState } from "react";
import { adapter, type LineageStage, type LineageTrace, type Manifest } from "../adapter";
import { StatusBar } from "../components/StatusBar";
import { CommandLine, type LastCall } from "../components/CommandLine";
import { DataTable, type Column } from "../components/DataTable";
import { HashBlock } from "../components/HashBlock";
import { Histogram } from "../components/Histogram";
import { Sparkline } from "../components/Sparkline";
import { balances, dec, num } from "../format";
import type { LineageRecord } from "../adapter";
import styles from "./Lineage.module.css";

const rejectColumns: Column<{ row_id: number; reason: string }>[] = [
  { key: "row_id", header: "row id", width: "120px", numeric: true, render: (r) => num(r.row_id), sortValue: (r) => r.row_id },
  { key: "reason", header: "reject reason", width: "1fr", render: (r) => r.reason, sortValue: (r) => r.reason },
];

const reduceMotion = () =>
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

const gb = (bytes: number) => `${(bytes / 1e9).toFixed(2)} GB`;

// One captured field's journey through a single stage, paired for the mirrored map.
type FlowKind = "rename" | "born" | "kept" | "dropped";
interface FlowRow {
  kind: FlowKind;
  beforeName?: string;
  beforeValue?: string;
  afterName?: string;
  afterValue?: string;
  reason?: string;
  hero: boolean;
}

// A gentle bezier per kind: rename/kept sweep across, born sprouts from the operator,
// dropped stops short. Authored on a 0..100 box with a non-scaling stroke (stays 1px).
const CONNECTOR: Record<FlowKind, string> = {
  rename: "M0,50 C 34,28 66,72 100,50",
  kept: "M0,50 C 34,45 66,55 100,50",
  born: "M50,50 C 72,50 86,50 100,50",
  dropped: "M0,50 C 26,50 40,50 48,50",
};

const GLYPH: Record<FlowKind, string> = { rename: "→", born: "+", kept: "", dropped: "×" };

export function Lineage() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [records, setRecords] = useState<LineageRecord[]>([]);
  const [recordId, setRecordId] = useState("");
  const [trace, setTrace] = useState<LineageTrace | null>(null);
  const [selected, setSelected] = useState(2); // SETU: the canonical rename is the point
  const [drillOpen, setDrillOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [pulseKey, setPulseKey] = useState(0);
  const [armed, setArmed] = useState(false); // gate the reveal to keypress, never mount
  const [count, setCount] = useState(0);
  const [last, setLast] = useState<LastCall | null>(null);

  useEffect(() => {
    adapter.getManifest().then(setManifest);
    adapter.listLineageRecords().then((rs) => {
      setRecords(rs);
      setRecordId((cur) => cur || rs[0]?.id || "");
    });
  }, []);

  useEffect(() => {
    if (!recordId) return;
    const t0 = performance.now();
    adapter.getLineage(recordId).then((t) => {
      setTrace(t);
      setLast({ label: `getLineage(${recordId})`, ms: Math.round(performance.now() - t0) });
    });
  }, [recordId]);

  const stages = trace?.stages ?? [];
  const stage: LineageStage | undefined = stages[selected];
  const isDrillStage = stage?.stage === "KAVACH" || stage?.stage === "SETU";

  const goStage = (i: number) => {
    if (i < 0 || i >= stages.length) return;
    setSelected(i);
    setDrillOpen(false);
    setCollapsed(false);
    setArmed(true);
    setPulseKey((k) => k + 1);
  };

  const goRecord = (id: string) => {
    setRecordId(id);
    setSelected(2);
    setDrillOpen(false);
    setCollapsed(false);
    setArmed(true);
    setPulseKey((k) => k + 1);
  };

  const cycleRecord = (dir: 1 | -1) => {
    if (records.length === 0) return;
    const i = records.findIndex((r) => r.id === recordId);
    goRecord(records[(i + (dir === 1 ? 1 : records.length - 1)) % records.length].id);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key >= "1" && e.key <= "8") return goStage(Number(e.key) - 1);
      if (e.key === "ArrowRight") return goStage(selected + 1);
      if (e.key === "ArrowLeft") return goStage(selected - 1);
      if (e.key === "ArrowDown") return cycleRecord(1);
      if (e.key === "ArrowUp") return cycleRecord(-1);
      if (e.key === "Enter" && isDrillStage) return setDrillOpen((o) => !o);
      if (e.key === "Escape") return void (setDrillOpen(false), setCollapsed(false));
      if (e.key === " " && stage?.stage === "SETU" && drillOpen) {
        e.preventDefault();
        setCollapsed((c) => !c);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selected, recordId, isDrillStage, stage, drillOpen, stages.length, records]);

  // The collapse counter counts announcements down to transactions on Space, once.
  useEffect(() => {
    if (!trace) return;
    const { n_announcements, n_transactions } = trace.setu.collapse;
    if (!collapsed) return setCount(n_announcements);
    if (reduceMotion()) return setCount(n_transactions);
    const t0 = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / 420);
      const eased = 1 - Math.pow(1 - p, 3);
      setCount(Math.round(n_announcements + (n_transactions - n_announcements) * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [collapsed, trace]);

  // Pair each output field back to its input so the map reads as one flow per field:
  // renames sweep across, added fields are born, unchanged fields are kept and quiet.
  const flowRows = useMemo<FlowRow[]>(() => {
    const before = stage?.before ?? [];
    const after = stage?.after ?? [];
    const byName = new Map(before.map((f) => [f.name, f]));
    const rows: FlowRow[] = after.map((a) => {
      if (a.status === "renamed" && a.from)
        return { kind: "rename", beforeName: a.from, afterName: a.name, afterValue: a.value, hero: false };
      if (a.status === "dropped")
        return { kind: "dropped", beforeName: a.name, beforeValue: byName.get(a.name)?.value ?? a.value, reason: a.reason, hero: false };
      if (a.status === "added") return { kind: "born", afterName: a.name, afterValue: a.value, hero: false };
      return { kind: "kept", beforeName: a.name, beforeValue: byName.get(a.name)?.value ?? a.value, afterValue: a.value, hero: false };
    });
    const rank: Record<FlowKind, number> = { rename: 0, born: 1, kept: 2, dropped: 3 };
    rows.sort((x, y) => rank[x.kind] - rank[y.kind]);
    const named = rows.findIndex((r) => r.kind === "rename");
    const heroIdx = named >= 0 ? named : rows.findIndex((r) => r.kind === "born");
    if (heroIdx >= 0) rows[heroIdx].hero = true;
    return rows;
  }, [stage]);

  if (!trace || !stage) {
    return (
      <div className={styles.page}>
        <StatusBar manifest={manifest} />
        <div className={styles.loading}>loading trace…</div>
        <CommandLine last={last} />
      </div>
    );
  }

  const ok = balances(stage.counts);
  const collapse = trace.setu.collapse;
  const mean = collapse.n_announcements / collapse.n_transactions; // read from data, never 9
  const isSource = stage.before.length === 0;
  const prevName = stages[selected - 1]?.stage;
  const fork =
    stage.stage === "SETU" ? (
      <>grain splits → <span className="mono">{num(collapse.n_transactions)}</span> tx</>
    ) : stage.counts.dropped > 0 ? (
      <>− <span className="mono">{num(stage.counts.dropped)}</span> dropped</>
    ) : null;

  return (
    <div className={styles.page}>
      <StatusBar manifest={manifest} />

      <div className={styles.head}>
        <div>
          <div className={styles.h1}>Lineage</div>
          <p className={styles.sub}>
            One captured row, followed across all eight stages — every rename, enrichment, and field it gains on the way.
          </p>
        </div>
        <div className={styles.rec}>
          <span>tracing record</span>
          <span className={styles.recRow}>
            <button className={styles.recNav} onClick={() => cycleRecord(-1)} aria-label="previous record">‹</button>
            <span className={`${styles.rid} mono`}>{trace.record_id}</span>
            <button className={styles.recNav} onClick={() => cycleRecord(1)} aria-label="next record">›</button>
          </span>
        </div>
      </div>

      <div className={styles.spineWrap}>
        <div className={styles.spine} role="tablist" aria-label="pipeline stages">
          {stages.map((s, i) => (
            <button
              key={s.stage}
              className={styles.node}
              role="tab"
              aria-selected={i === selected}
              data-selected={i === selected || undefined}
              onClick={() => goStage(i)}
            >
              <span className={`${styles.nIn} mono`}>{i === 0 ? "—" : num(s.counts.in)}</span>
              <span className={styles.lampRow}>
                <span className={styles.lamp} data-on={s.complete || undefined} aria-hidden="true" />
              </span>
              <span className={styles.nName}>{s.stage}</span>
              <span className={`${styles.nOut} mono`}>{num(s.counts.out)}</span>
            </button>
          ))}
          {fork && (
            <div className={styles.fork} style={{ gridColumn: selected + 1 }}>
              {fork}
            </div>
          )}
        </div>
      </div>

      <div className={styles.trans}>
        <div className={styles.seam}>
          {isSource ? (
            stage.stage
          ) : (
            <>
              {prevName}
              <span className={styles.ar} aria-hidden="true">→</span>
              {stage.stage}
            </>
          )}
        </div>
        {stage.note && <p className={styles.say}>{stage.note}</p>}
      </div>

      {isSource ? (
        <div className={styles.origin}>
          <div className={styles.originHead}>raw capture · nothing upstream</div>
          {stage.after.map((f) => (
            <div key={f.name} className={styles.originRow}>
              <span className={`${styles.fn} mono`}>{f.name}</span>
              <span className={`${styles.fv} mono`}>{f.value}</span>
            </div>
          ))}
        </div>
      ) : (
        <>
          <div className={styles.mhead}>
            <span className={styles.mheadL}>before</span>
            <span />
            <span className={styles.mheadR}>after · {stage.stage}</span>
          </div>
          <div className={styles.map} data-armed={armed || undefined} key={`${recordId}-${selected}-${pulseKey}`}>
            {flowRows.map((r, i) => (
              <div
                key={`${r.beforeName ?? ""}-${r.afterName ?? ""}-${i}`}
                className={styles.mrow}
                data-kind={r.kind}
                data-hero={r.hero || undefined}
              >
                <div className={styles.mb}>
                  {r.beforeName && <span className={`${styles.fn} mono`}>{r.beforeName}</span>}
                  {r.beforeValue && (
                    <span
                      className={`${styles.fv} mono`}
                      data-dim={r.kind === "kept" || undefined}
                      data-strike={r.kind === "dropped" || undefined}
                    >
                      {r.beforeValue}
                    </span>
                  )}
                </div>
                <div className={styles.mc}>
                  <svg className={styles.cline} viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                    <path className={styles.clinePath} d={CONNECTOR[r.kind]} vectorEffect="non-scaling-stroke" />
                  </svg>
                  {GLYPH[r.kind] && <span className={`${styles.cmk} mono`}>{GLYPH[r.kind]}</span>}
                </div>
                <div className={styles.ma}>
                  {r.afterName && (
                    <span
                      className={`${styles.fn} mono`}
                      data-sig={r.kind === "rename" || r.kind === "born" || undefined}
                    >
                      {r.afterName}
                    </span>
                  )}
                  {r.afterValue && (
                    <span className={`${styles.fv} mono`} data-dim={r.kind === "kept" || undefined}>
                      {r.afterValue}
                    </span>
                  )}
                  {r.reason && <span className={styles.reason}>{r.reason}</span>}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      <div className={styles.balance} data-fail={!ok || undefined}>
        <span className="mono">in {num(stage.counts.in)}</span>
        <span className={styles.eq}>{ok ? "==" : "≠"}</span>
        <span className="mono">
          out {num(stage.counts.out)} + {num(stage.counts.dropped)} dropped
        </span>
        <span className={styles.ok}>{ok ? "✓" : "✕"}</span>
        <span className={styles.cap}>{ok ? "balances" : "does not balance"}</span>
      </div>

      {isDrillStage && (
        <div className={styles.drillBar}>
          <button className={styles.drillToggle} onClick={() => setDrillOpen((o) => !o)}>
            {drillOpen ? "Esc · close" : "Enter · open"} {stage.stage} detail
          </button>
          {stage.stage === "SETU" && drillOpen && (
            <button className={styles.drillToggle} onClick={() => setCollapsed((c) => !c)}>
              Space · {collapsed ? "echo shown" : "collapse announcements"}
            </button>
          )}
        </div>
      )}

      {drillOpen && stage.stage === "KAVACH" && (
        <div className={styles.drill}>
          <div className={styles.drillHead}>INTAKE · custody</div>
          <div className={styles.kavachGrid}>
            <div className={styles.stack}>
              <div className={styles.subHead}>INPUT FILES · SHA-256 IN FULL</div>
              {trace.kavach.files.map((fl) => (
                <div key={fl.name} className={styles.file}>
                  <div className={styles.fileRow}>
                    <span className={`${styles.fileName} mono`}>{fl.name}</span>
                    <span className={`${styles.fileBytes} mono`}>{gb(fl.bytes)}</span>
                  </div>
                  <HashBlock value={fl.sha256} label="sha-256" />
                </div>
              ))}
              <div className={styles.subHead}>SCHEMA MAP</div>
              <div className={styles.schema}>
                {trace.kavach.schema.map((c) => (
                  <span key={c.column} className={styles.schemaChip} data-tag={c.tag}>
                    <span className="mono">{c.column}</span>
                    <span className={styles.schemaTag}>{c.tag}</span>
                  </span>
                ))}
              </div>
            </div>
            <div className={styles.stack}>
              <div className={styles.subHead}>
                REJECTS · {num(manifest?.rows_rejected ?? 0)} run-wide, sample below
              </div>
              <DataTable rows={trace.kavach.rejects} columns={rejectColumns} getKey={(r) => String(r.row_id)} height={200} />
            </div>
          </div>
        </div>
      )}
      {drillOpen && stage.stage === "SETU" && (
        <div className={styles.drill}>
          <div className={styles.drillHead}>COLLAPSE · announcements → transactions</div>
          <div className={styles.collapseFig}>
            <div className={styles.collapseStat}>
              <span className={`${styles.collapseCount} mono`}>{num(count)}</span>
              <span className={styles.collapseUnit}>{collapsed ? "transactions" : "announcements"}</span>
            </div>
            <div className={styles.bar}>
              <div
                className={styles.barTx}
                style={{ width: collapsed ? `${(collapse.n_transactions / collapse.n_announcements) * 100}%` : "100%" }}
              />
              <div
                className={styles.barEcho}
                data-shown={collapsed || undefined}
                style={{ width: `${(collapse.n_echo / collapse.n_announcements) * 100}%` }}
              />
            </div>
            <div className={styles.collapseMeta}>
              <span className="mono">{num(collapse.n_announcements)} ann</span>
              <span className="mono">{num(collapse.n_transactions)} tx</span>
              <span className="mono">{num(collapse.n_echo)} echo</span>
              <span className={styles.meanFig}>mean {dec(mean)} ann / tx</span>
            </div>
          </div>

          <div className={styles.subHead}>ANNOUNCEMENTS PER TRANSACTION</div>
          <Histogram
            bars={collapse.announcements_per_tx.map((b) => ({ label: b.bucket, value: b.count }))}
            mean={mean}
            meanLabel={`mean ${dec(mean)}`}
          />

          <div className={styles.sparks}>
            {trace.setu.sparklines.map((sp) => (
              <Sparkline key={sp.label} points={sp.points} label={sp.label} unit={sp.unit} />
            ))}
          </div>
        </div>
      )}

      {stage.stage === "PRAMAAN" && (
        <div className={styles.merkle}>
          <HashBlock value={trace.merkle_head} label="merkle head · in full" />
        </div>
      )}

      <CommandLine last={last} />
    </div>
  );
}






