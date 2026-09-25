import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { adapter, type AlertRow, type AlertDetail } from "../adapter";
import { CommandLine, type LastCall } from "../components/CommandLine";
import { DataTable, type Column } from "../components/DataTable";
import { RangeBar } from "../components/RangeBar";
import { ShapBars } from "../components/ShapBars";
import { num, dec, ms } from "../format";
import styles from "./Queue.module.css";

const reduceMotion = () =>
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// Column names are terse by contract; the queue shows the human phrase.
const TYPOLOGY: Record<string, string> = {
  fan_out: "fan-out",
  rapid_hop: "rapid hop",
  peel_chain: "peel chain",
  structuring: "structuring",
  pass_through: "pass-through",
  coinjoin_like: "coinjoin-like",
};
const typ = (t: string) => TYPOLOGY[t] ?? t.replace(/_/g, " ");

const SEVERITY_RANK: Record<AlertRow["severity"], number> = { high: 3, medium: 2, low: 1 };

// A confidence with no usable interval is the defect state, not something to render as a
// bare number. One predicate, used by both the table cell and the inspector.
const hasInterval = (low: number, high: number) =>
  Number.isFinite(low) && Number.isFinite(high) && high >= low;

// ---- the inspector, exported so its defect states are testable without the whole page ----

interface InspectorProps {
  detail: AlertDetail;
  /** Called when the analyst clears a lead the counter-evidence is decisive against. */
  onClear: (caseId: string) => void;
  /** Evidence rows drill through to a screen; the queue hands the route key up. */
  onNavigate: (key: string) => void;
}

const SEVERITY_LABEL: Record<AlertRow["severity"], string> = {
  high: "high",
  medium: "medium",
  low: "low",
};

export function QueueInspector({ detail, onClear, onNavigate }: InspectorProps) {
  const cleared = detail.status === "CLEARED";
  const clearable = detail.counter.some((c) => c.would_clear);
  const conf = detail.confidence;
  const intervalOk = hasInterval(conf.low, conf.high);
  const abstain = conf.label.toUpperCase().startsWith("ABSTAIN");

  return (
    <div className={styles.inspector}>
      <header className={styles.insHead}>
        <div className={styles.insCaseRow}>
          <span className={`${styles.insCase} mono`}>{detail.case_id}</span>
          <span className={styles.sevMark} data-sev={detail.severity} title={`severity ${detail.severity}`} />
          <span className={styles.sevText} data-sev={detail.severity}>{SEVERITY_LABEL[detail.severity]}</span>
        </div>
        <p className={styles.insHeadline}>{detail.headline}</p>
      </header>

      {/* 1 · WHY — the diverging attribution, base rate marked */}
      <section className={styles.section}>
        <span className={styles.sectionTitle}>why</span>
        <ShapBars contributions={detail.why.contributions} baseRate={detail.why.base_rate} />
      </section>

      {/* 2 · EVIDENCE — the rows that drove it, each clickable through to the graph */}
      <section className={styles.section}>
        <span className={styles.sectionTitle}>evidence</span>
        <ul className={styles.evList}>
          {detail.evidence.map((e, i) => (
            <li key={i}>
              <button className={styles.evItem} onClick={() => onNavigate("4")}>
                <span className={styles.evStatement}>{e.statement}</span>
                <span className={`${styles.evRef} mono`}>{e.source_ref}</span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      {/* 3 · COUNTER-EVIDENCE — --cool, mandatory. An empty list is a pipeline defect. */}
      <section className={styles.section} data-cool data-cleared={cleared || undefined}>
        <span className={styles.sectionTitle} data-cool>counter-evidence</span>
        {detail.counter.length === 0 ? (
          <div className={styles.defect} role="alert">
            <span className={styles.defectMark}>PIPELINE DEFECT</span>
            <p className={styles.defectText}>
              This alert carries no counter-evidence. Every alert must; an empty section means
              the pipeline dropped it, not that the lead is clean.
            </p>
          </div>
        ) : (
          <ul className={styles.counterList}>
            {detail.counter.map((c, i) => (
              <li key={i} className={styles.counterItem}>
                <div className={styles.counterHead}>
                  {c.would_clear && <span className={styles.wouldClear}>WOULD CLEAR</span>}
                  <span className={`${styles.counterStrength} mono`}>{dec(c.strength)}</span>
                </div>
                <p className={styles.counterStatement}>{c.statement}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* 4 · CONFIDENCE — interval + coverage, or the defect state. Never a bare score. */}
      <section className={styles.section}>
        <span className={styles.sectionTitle}>confidence</span>
        {!intervalOk ? (
          <div className={styles.defect} role="alert">
            <span className={styles.defectMark}>NO INTERVAL</span>
            <p className={styles.defectText}>
              A score without its conformal interval is not shown. The interval is the claim; the
              point alone is not evidence.
            </p>
          </div>
        ) : (
          <div className={styles.conf}>
            <div className={styles.confFocal}>
              <span className={`${styles.confScore} mono`} data-abstain={abstain || undefined}>
                {abstain ? "ABSTAIN" : dec(conf.score)}
              </span>
              <span className={styles.confLabel} data-abstain={abstain || undefined}>{conf.label}</span>
            </div>
            <RangeBar low={conf.low} high={conf.high} point={abstain ? undefined : conf.score} />
            <span className={`${styles.confCoverage} mono`}>
              interval at {dec(conf.coverage_target)} target · {dec(conf.empirical_coverage)} empirical coverage
            </span>
          </div>
        )}
      </section>

      {/* the clear action / the cleared state — only when a counter is decisive */}
      {clearable && !cleared && (
        <button className={styles.clearBtn} onClick={() => onClear(detail.case_id)}>
          clear lead — counter-evidence is decisive
        </button>
      )}
      {cleared && (
        <div className={styles.clearedState}>
          <span className={styles.clearedMark}>CLEARED</span>
          <span className={styles.clearedWhy}>dropped on decisive counter-evidence</span>
        </div>
      )}
    </div>
  );
}

// ---- the screen ----

interface QueueProps {
  onNavigate: (key: string) => void;
}

export function Queue({ onNavigate }: QueueProps) {
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [cleared, setCleared] = useState<Set<string>>(() => new Set());
  const [selIndex, setSelIndex] = useState(0);
  const [detail, setDetail] = useState<AlertDetail | null>(null);
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("");
  const [last, setLast] = useState<LastCall | null>(null);
  const filterRef = useRef<HTMLInputElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const [tableH, setTableH] = useState(520);

  useEffect(() => {
    const t0 = performance.now();
    adapter.listAlerts().then((a) => {
      setAlerts(a);
      setLast({ label: "listAlerts", ms: Math.round(performance.now() - t0) });
    });
  }, []);

  // The table body fills the working surface; measure it so virtualisation gets a real height.
  useLayoutEffect(() => {
    const el = bodyRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => setTableH(el.clientHeight));
    ro.observe(el);
    setTableH(el.clientHeight);
    return () => ro.disconnect();
  }, []);

  const rows = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return alerts
      .filter((a) => !cleared.has(a.case_id))
      .filter(
        (a) =>
          !q ||
          a.case_id.toLowerCase().includes(q) ||
          a.headline.toLowerCase().includes(q) ||
          a.typologies.some((t) => typ(t).includes(q)),
      );
  }, [alerts, cleared, filter]);

  const selected = rows[Math.min(selIndex, rows.length - 1)] ?? null;
  const openCase = (caseId: string) => {
    const t0 = performance.now();
    adapter.getAlert(caseId).then((d) => {
      setDetail(d);
      setOpen(true);
      setLast({ label: `getAlert ${caseId}`, ms: Math.round(performance.now() - t0) });
    });
  };

  // The clear: flip the open detail to CLEARED (120ms), let the counter section hold for the
  // reveal, then drop the row from the queue (420ms). Reduced motion skips straight to gone.
  const doClear = (caseId: string) => {
    setDetail((d) => (d && d.case_id === caseId ? { ...d, status: "CLEARED" } : d));
    const remove = () => {
      setCleared((s) => new Set(s).add(caseId));
      setOpen(false);
      setDetail(null);
    };
    if (reduceMotion()) remove();
    else window.setTimeout(remove, 420);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      const typing = el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA");
      if (e.key === "/" && !typing) {
        e.preventDefault();
        filterRef.current?.focus();
        return;
      }
      if (typing) {
        if (e.key === "Escape") (el as HTMLElement).blur();
        return;
      }
      if (e.key === "j") setSelIndex((i) => Math.min(rows.length - 1, i + 1));
      else if (e.key === "k") setSelIndex((i) => Math.max(0, i - 1));
      else if (e.key === "Enter") {
        if (selected) openCase(selected.case_id);
      } else if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [rows, selected]);

  const columns: Column<AlertRow>[] = [
    { key: "rank", header: "#", numeric: true, width: "40px", render: (r) => r.rank, sortValue: (r) => r.rank },
    { key: "case", header: "case", width: "1.5fr", render: (r) => <span className="mono">{r.case_id}</span>, sortValue: (r) => r.case_id },
    {
      key: "sev", header: "sev", width: "104px", sortValue: (r) => SEVERITY_RANK[r.severity],
      render: (r) => (
        <span className={styles.sevCell}>
          <span className={styles.sevMark} data-sev={r.severity} />
          <span className={styles.sevText} data-sev={r.severity}>{r.severity}</span>
        </span>
      ),
    },
    {
      key: "score", header: "score · interval", width: "1.8fr", sortValue: (r) => r.conf_high,
      render: (r) =>
        hasInterval(r.conf_low, r.conf_high) ? (
          <RangeBar low={r.conf_low} high={r.conf_high} />
        ) : (
          <span className={styles.cellDefect}>NO INTERVAL</span>
        ),
    },
    {
      key: "typ", header: "typology", width: "1.6fr",
      render: (r) => (
        <span className={styles.chips}>
          {r.typologies.map((t) => (
            <span key={t} className={styles.chip}>{typ(t)}</span>
          ))}
        </span>
      ),
    },
    { key: "cluster", header: "cluster", numeric: true, width: "78px", render: (r) => num(r.cluster_size), sortValue: (r) => r.cluster_size },
    {
      key: "origin", header: "origin", width: "1.1fr",
      render: (r) => (
        <span className="mono">{r.origin_asn != null ? `AS${r.origin_asn} · ${r.origin_country ?? "—"}` : "—"}</span>
      ),
      sortValue: (r) => r.origin_asn ?? -1,
    },
    { key: "dwell", header: "dwell", numeric: true, width: "88px", render: (r) => ms(r.dwell_us), sortValue: (r) => r.dwell_us },
    {
      key: "status", header: "status", width: "84px",
      render: (r) => <span className={styles.statusChip} data-status={r.status}>{r.status}</span>,
      sortValue: (r) => r.status,
    },
  ];
  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <span className={styles.crumb}>
          DRISHTI · /_queue · <span className="mono">{rows.length} open</span>
        </span>
        <div className={styles.filterWrap}>
          <span className={styles.filterKey}>/</span>
          <input
            ref={filterRef}
            className={`${styles.filter} mono`}
            placeholder="filter case, typology, headline"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
      </div>

      <div className={styles.body}>
        <div className={styles.tableWrap}>
          <div className={styles.tableFill} ref={bodyRef}>
            <DataTable
              rows={rows}
              columns={columns}
              getKey={(r) => r.case_id}
              rowHeight={28}
              height={tableH}
              selectedKey={selected?.case_id}
              onSelect={(r) => {
                setSelIndex(rows.findIndex((x) => x.case_id === r.case_id));
                openCase(r.case_id);
              }}
            />
          </div>
          <p className={styles.tableNote}>
            twenty leads, ranked, each with the argument against it · j / k move · enter opens · / filters
          </p>
        </div>

        <aside className={styles.aside} data-open={open || undefined}>
          {open && detail ? (
            <QueueInspector detail={detail} onClear={doClear} onNavigate={onNavigate} />
          ) : (
            <div className={styles.asideEmpty}>
              <span className={styles.asideEmptyKey}>ENTER</span>
              <p className={styles.asideEmptyText}>
                Open a lead to see why it scored, the evidence behind it, the counter-evidence
                against it, and the confidence interval it earned.
              </p>
            </div>
          )}
        </aside>
      </div>

      <CommandLine last={last} />
    </div>
  );
}



