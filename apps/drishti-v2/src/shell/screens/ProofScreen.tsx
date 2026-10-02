import { useEffect, useRef, useState } from "react";
import { useRun } from "../../data/RunContext";
import { usToIST, ownerGroupLabel, scrubOwnerWords } from "../../data/jaal";
import styles from "./ProofScreen.module.css";

/**
 * Proof · PRAMAAN (§11.5) — the court-ready sealed dossier, on paper. Left: the
 * hash-chain spine (every stage's SHA-256 printed IN FULL — BSA 2023 §63(4)).
 * Centre: THE FINDING — the {operator · region · UTC} tuple as a boxed hero, but ONLY
 * when attribution is ready (the backend's attribution_ready flag); otherwise the honest
 * not-ready state. The exact host is never the hero (§2): we lead with the network
 * operator (ASN) + region, and the masked announcing IP sits in a small officer note.
 * Right: the pre-filled BNSS 2023 §94 production notice.
 * Counter-findings live inside the exhibit (a would_clear one, if any, gets marked).
 * Identifiers are truncated to the backend display format; hashes stay whole. The
 * full IPs live only in the downloaded packet.json (the officer's machine artifact).
 */

/** DATA-CONTRACTS §9 display format — first two octets, rest masked. Never a full IP. */
const maskIp = (ip: string) =>
  ip.includes(":")
    ? ip.split(":").slice(0, 2).join(":") + ":…"
    : ip.split(".").slice(0, 2).join(".") + ".x.x";

/** observed_at_utc is an ISO string with offset → render as plain UTC (the tuple is UTC). */
const isoToUTC = (iso: string) =>
  new Date(iso).toISOString().slice(0, 19).replace("T", " ") + " UTC";

/** §3 kill-list scrub for backend-authored prose on this officer/court screen: the word
 *  "cluster"/"clustering" never shows here (shared with Leads, so the two cannot drift). */
const scrub = scrubOwnerWords;

/** The backend's estimator name is a machine token ("plain_conformal") and half of it is
 *  on the kill-list. This screen says what the interval IS; the token never renders. */
const METHOD_GLOSS: Record<string, string> = {
  plain_conformal: "shortlist interval",
};

export function ProofScreen() {
  const { fixtures, run, selectAlert } = useRun();
  const p = fixtures.packet;
  // attribution_ready is a real backend field (§6): the packet is court-ready only when the
  // backend says so — we no longer derive it from the presence of peer IP/port/timestamp.
  const [fingerprint, setFingerprint] = useState("");
  useEffect(() => {
    let live = true;
    setFingerprint("");
    const bytes = new TextEncoder().encode(JSON.stringify(p, null, 2));
    void crypto.subtle.digest("SHA-256", bytes).then((hash) => {
      if (live)
        setFingerprint(
          Array.from(new Uint8Array(hash), (b) =>
            b.toString(16).padStart(2, "0"),
          ).join(""),
        );
    });
    return () => {
      live = false;
    };
  }, [p]);
  const a = p.attribution;
  const READY = p.attribution_ready;
  const clearing = p.counter_findings.find((c) => c.would_clear);
  const [sealed, setSealed] = useState(false);
  const linkRef = useRef<HTMLAnchorElement>(null);

  // Offline "download" of the machine artifact — a Blob, never a network call.
  const generate = () => {
    const blob = new Blob([JSON.stringify(p, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const el = linkRef.current;
    if (el) {
      el.href = url;
      el.download = `packet-${p.case_id}.json`;
      el.click();
    }
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  return (
    <section className={styles.screen}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>Proof</h1>
          <span className={styles.tag}>PRAMAAN · प्रमाण</span>
        </div>
        <p className={styles.gloss}>
          One lead pressed into a signed, hash-chained document: the three
          values an ISP needs to name a subscriber, and every step that produced
          them.
        </p>
        <div className={styles.caseRow}>
          <span>
            case <strong>{p.case_id}</strong>
          </span>
          <span>
            subject{" "}
            <strong className={styles.mono}>
              {ownerGroupLabel(p.subject.subject_id)}
            </strong>
          </span>
        </div>
      </header>

      <section className={styles.inventory}>
        <div>
          <span>SELECTED EVIDENCE PACKET</span>
          <h2>{p.case_id}</h2>
          <p>
            Source run: {run.id} · {p.chain_of_custody.length} custody entries
          </p>
        </div>
        <label>
          Available signed packets
          <select
            value={p.case_id}
            onChange={(e) => selectAlert(e.target.value)}
          >
            {Object.keys(run.payload.packets ?? {}).map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </label>
        <details>
          <summary>SHA-256 of the exact JSON download</summary>
          <code>{fingerprint || "Computing local fingerprint…"}</code>
          <p>
            This fingerprint identifies the exported file bytes. Custody and
            signature fields are shown separately below.
          </p>
        </details>
      </section>
      <div className={styles.exhibit}>
        {/* ── LEFT: hash-chain spine ─────────────────────── */}
        <aside className={styles.spine}>
          <span className={styles.colLabel}>chain of custody</span>
          <div className={styles.chainItem}>
            <span className={styles.chainStage}>
              raw capture · sealed input
            </span>
            <code className={styles.hash}>{p.input.files[0].sha256}</code>
            <span className={styles.chainMeta}>
              {p.input.rows_sealed.toLocaleString("en-US")} rows sealed
            </span>
          </div>
          {p.chain_of_custody.map((s, i) => (
            <div key={s.stage} className={styles.chainItem}>
              <span className={styles.chainStage}>
                <span className={styles.chainN}>{i + 1}</span>
                {s.stage}
              </span>
              <code className={styles.hash}>{s.sha256}</code>
              <span className={styles.chainMeta}>{usToIST(s.at_us)}</span>
            </div>
          ))}
          <div className={`${styles.chainItem} ${styles.chainHead}`}>
            <span className={styles.chainStage}>merkle head</span>
            <code className={styles.hash}>{p.merkle_head}</code>
          </div>
          <div className={`${styles.chainItem} ${styles.chainHead}`}>
            <span className={styles.chainStage}>expected packet SHA-256</span>
            <code className={styles.hash}>
              {p.replay.expected_packet_sha256}
            </code>
          </div>
        </aside>

        {/* ── CENTRE: THE FINDING ────────────────────────── */}
        <div className={styles.finding}>
          <span className={styles.colLabel}>the finding</span>
          {READY ? (
            <div className={styles.tuple}>
              <div className={styles.tCell}>
                <span className={styles.tKey}>network operator</span>
                <span className={styles.tVal}>AS{a.asn}</span>
              </div>
              <span className={styles.tSep}>·</span>
              <div className={styles.tCell}>
                <span className={styles.tKey}>region</span>
                <span className={styles.tVal}>{a.geo_country}</span>
              </div>
              <span className={styles.tSep}>·</span>
              <div className={styles.tCell}>
                <span className={styles.tKey}>observed (UTC)</span>
                <span className={styles.tVal}>
                  {isoToUTC(a.observed_at_utc)}
                </span>
              </div>
            </div>
          ) : (
            <div className={styles.notReady}>
              <span className={styles.nrLabel}>attribution not ready</span>
              <p>
                We only print the {`{operator · region · UTC}`} finding when the
                backend marks it court-ready. It isn't here, so we hold it back
                rather than hand a court a half-answer.
              </p>
            </div>
          )}

          <dl className={styles.findMeta}>
            <div>
              <dt>network operator (ASN)</dt>
              <dd>
                AS{a.asn} · {a.geo_country}
              </dd>
            </div>
            <div>
              <dt>operator likelihood</dt>
              <dd>
                {(a.p_asn * 100).toFixed(2)}% · margin{" "}
                {(a.margin * 100).toFixed(2)}%
              </dd>
            </div>
            <div>
              <dt>shortlist</dt>
              <dd>{a.shortlist.length} candidate hosts</dd>
            </div>
            <div>
              <dt>announcing host (officer only)</dt>
              <dd className={styles.mono}>{maskIp(a.peer_ip)}</dd>
            </div>
          </dl>

          <div className={styles.findings}>
            <span className={styles.subLabel}>why this lead was raised</span>
            <ul>
              {p.findings.map((f, i) => (
                <li key={i}>{scrub(f.statement)}</li>
              ))}
            </ul>
          </div>

          <div className={styles.counters}>
            <span className={styles.subLabel}>why it might be innocent</span>
            {p.counter_findings.map((c, i) => (
              <div key={i} className={styles.counter}>
                <p>{scrub(c.statement)}</p>
                {c.would_clear && (
                  <span className={styles.wouldClear}>
                    one doubt is enough to close this lead
                  </span>
                )}
              </div>
            ))}
            {!clearing && (
              <p className={styles.noClear}>
                No single doubt here is enough on its own to close the lead.
              </p>
            )}
          </div>
        </div>

        {/* ── RIGHT: legal notice ────────────────────────── */}
        <aside className={styles.legal}>
          <span className={styles.colLabel}>legal basis</span>
          <div className={styles.legalBox}>
            <span className={styles.legalHead}>Production notice</span>
            <p className={styles.legalBasis}>{p.legal.basis}</p>
            <p className={styles.legalBody}>
              Directs the disclosure of subscriber records matching the network
              address, source port and timestamp in the sealed packet, from the
              operator identified as AS{a.asn}.
            </p>
          </div>
          <div className={styles.legalBox}>
            <span className={styles.legalHead}>Hash disclosure</span>
            <p className={styles.legalBasis}>{p.legal.hash_disclosure}</p>
            <p className={styles.legalBody}>
              Every SHA-256 above is printed in full, as the schedule requires.
              Nothing summarised, nothing hidden.
            </p>
          </div>
          <dl className={styles.verMeta}>
            <div>
              <dt>tool</dt>
              <dd>v{p.tool_version}</dd>
            </div>
            <div>
              <dt>code</dt>
              <dd className={styles.mono}>{p.code_version}</dd>
            </div>
            <div>
              <dt>confidence</dt>
              <dd className={styles.mono}>
                {p.confidence.method === "ranking_only" ? "Review ranking · no confidence interval" : <>
                  {METHOD_GLOSS[p.confidence.method] ?? p.confidence.method}{" "}
                  {p.confidence.low.toFixed(2)}–{p.confidence.high.toFixed(2)} at{" "}
                  {(p.confidence.coverage_target * 100).toFixed(0)}%
                </>}
              </dd>
            </div>
          </dl>
        </aside>
      </div>

      {/* ── seal + generate ──────────────────────────────── */}
      <div className={styles.footer}>
        <button
          type="button"
          className={`${styles.seal} ${sealed ? styles.sealed : ""}`}
          onClick={() => setSealed(true)}
          aria-pressed={sealed}
        >
          <span className={styles.wax} aria-hidden />
          {sealed ? "reviewed" : "Review the packet"}
        </button>
        <button
          type="button"
          className={styles.generate}
          disabled={!sealed}
          onClick={generate}
        >
          Export packet (JSON)
        </button>
        <a ref={linkRef} className={styles.srLink} aria-hidden>
          download
        </a>
        <p className={styles.provenance}>
          offline · seed {p.replay.seed} ·{" "}
          <code className={styles.mono}>{p.replay.command}</code>
        </p>
      </div>
    </section>
  );
}
