import { useMemo, useRef, useState, type ReactNode } from "react";
import styles from "./DataTable.module.css";

export interface Column<T> {
  key: string;
  header: string;
  /** Right-align and render mono with tabular figures. */
  numeric?: boolean;
  /** grid-template-columns track, e.g. "48px" or "1fr". Defaults to "1fr". */
  width?: string;
  render: (row: T) => ReactNode;
  /** Return a comparable; omit to make the column unsortable. */
  sortValue?: (row: T) => number | string;
}

interface Props<T> {
  rows: T[];
  columns: Column<T>[];
  getKey: (row: T) => string;
  /** Fixed row height in px; virtualisation depends on it being constant. */
  rowHeight?: number;
  /** Scroll viewport height in px. */
  height?: number;
  selectedKey?: string;
  onSelect?: (row: T) => void;
}

const OVERSCAN = 6;

/** A dense virtualised table. Rows are a constant height so only the visible window
 *  renders — a million rows cost the same as one screenful.
 *  ponytail: hand-rolled fixed-height windowing, reach for a lib only if rows ever vary. */
export function DataTable<T>({
  rows,
  columns,
  getKey,
  rowHeight = 28,
  height = 320,
  selectedKey,
  onSelect,
}: Props<T>) {
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 } | null>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const viewport = useRef<HTMLDivElement>(null);

  const template = columns.map((c) => c.width ?? "1fr").join(" ");

  const sorted = useMemo(() => {
    if (!sort) return rows;
    const col = columns.find((c) => c.key === sort.key);
    if (!col?.sortValue) return rows;
    const val = col.sortValue;
    return [...rows].sort((a, b) => {
      const av = val(a);
      const bv = val(b);
      if (av < bv) return -1 * sort.dir;
      if (av > bv) return 1 * sort.dir;
      return 0;
    });
  }, [rows, columns, sort]);

  const toggleSort = (col: Column<T>) => {
    if (!col.sortValue) return;
    setSort((s) => (s?.key === col.key ? { key: col.key, dir: s.dir === 1 ? -1 : 1 } : { key: col.key, dir: 1 }));
  };

  const total = sorted.length;
  const start = Math.max(0, Math.floor(scrollTop / rowHeight) - OVERSCAN);
  const visibleCount = Math.ceil(height / rowHeight) + OVERSCAN * 2;
  const end = Math.min(total, start + visibleCount);
  const window = sorted.slice(start, end);

  return (
    <div className={styles.table}>
      <div className={styles.header} style={{ gridTemplateColumns: template }}>
        {columns.map((c) => {
          const active = sort?.key === c.key;
          return (
            <button
              key={c.key}
              className={styles.th}
              data-numeric={c.numeric || undefined}
              data-sortable={!!c.sortValue || undefined}
              data-active={active || undefined}
              onClick={() => toggleSort(c)}
            >
              {c.header}
              {active && <span className={styles.caret}>{sort!.dir === 1 ? "▲" : "▼"}</span>}
            </button>
          );
        })}
      </div>

      <div
        ref={viewport}
        className={styles.body}
        style={{ height }}
        onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
      >
        <div style={{ height: total * rowHeight, position: "relative" }}>
          <div style={{ transform: `translateY(${start * rowHeight}px)` }}>
            {window.map((row) => {
              const k = getKey(row);
              return (
                <div
                  key={k}
                  className={styles.row}
                  style={{ gridTemplateColumns: template, height: rowHeight }}
                  data-selected={selectedKey === k || undefined}
                  onClick={() => onSelect?.(row)}
                >
                  {columns.map((c) => (
                    <div
                      key={c.key}
                      className={c.numeric ? `${styles.cell} ${styles.numeric} mono` : styles.cell}
                    >
                      {c.render(row)}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
