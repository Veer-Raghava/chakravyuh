import { useEffect, useState } from "react";
import { adapter, type Packet as PacketT } from "../adapter";
import { CommandLine, type LastCall } from "../components/CommandLine";
import { HashBlock } from "../components/HashBlock";
import { Lamp, type LampState } from "../components/Lamp";
import { RangeBar } from "../components/RangeBar";
import { dec } from "../format";
import styles from "./Packet.module.css";

const lamp = (ok: boolean): LampState => (ok ? "ok" : "fail");

// A confidence with no usable interval is the defect state, not a bare number; and an empty
// counter-findings section is a dropped argument, never a clean subject. Both must show.
const hasInterval = (low: number, high: number) =>
  Number.isFinite(low) && Number.isFinite(high) && high >= low;

// Format the microsecond generated_at as a UTC instant for the notice footer.
const utc = (us: number) => new Date(us / 1000).toISOString().replace(".000Z", "Z");

/** The rendered packet + its production notice. Exported so both the verified and the
 *  replay-mismatch states are testable without the whole screen. */
export function PacketView({ packet, onCopyReplay }: { packet: PacketT; onCopyReplay: () => void }) {
  const v = packet.verification;
  const allVerified = v.hash_verified && v.signature_valid && v.replay_matched;
  const a = packet.attribution;

  return (
    <div className={styles.body}>
      {/* LEFT — the rendered, signed packet */}
      <section className={styles.packet} aria-label="evidence packet">
        <header className={styles.pktHead}>
          <span className={`${styles.case} mono`}>{packet.case_id}</span>
          <span className={styles.gen}>
            generated {utc(packet.generated_at_us)} · tool {packet.tool_version} · code {packet.code_version}
          </span>
        </header>

        <div className={styles.lamps} role="status">
          <Lamp label="hash verified" state={lamp(v.hash_verified)} detail="sha-256 recomputed over sealed bytes" />
          <Lamp label="signature valid" state={lamp(v.signature_valid)} detail="ed25519 verify · vk in packet header" />
          <Lamp label="replay matched" state={lamp(v.replay_matched)} detail={packet.replay.command} />
        </div>

        {!allVerified && (
          <div className={styles.mismatch} role="alert">
            <span className={styles.mismatchMark}>DO NOT SERVE</span>
            <p className={styles.mismatchText}>
              {v.replay_matched
                ? "A verification check did not hold."
                : "The rendered packet did not reproduce from its seed: the replay hash does not match the expected value."}{" "}
              This packet is not court-ready until every lamp is green.
            </p>
          </div>
        )}

        <div className={styles.section}>
          <span className={styles.secTitle}>subject</span>
          <div className={styles.kv}><span className={styles.k}>subject</span><span className={`${styles.val} mono`}>{packet.subject.subject_id}</span></div>
          <div className={styles.kv}><span className={styles.k}>cluster</span><span className={`${styles.val} mono`}>{packet.subject.cluster_id}</span></div>
          <div className={styles.kv}>
            <span className={styles.k}>addresses</span>
            <span className={styles.addrs}>
              {packet.subject.addresses.map((ad) => <code key={ad} className={`${styles.val} mono`}>{ad}</code>)}
            </span>
          </div>
        </div>

        <div className={styles.section}>
          <span className={styles.secTitle}>attribution</span>
          <div className={styles.kv}><span className={styles.k}>origin peer</span><span className={`${styles.val} mono`}>{a.peer_ip}:{a.peer_port}</span></div>
          <div className={styles.kv}><span className={styles.k}>observed</span><span className={`${styles.val} mono`}>{a.observed_at_utc}</span></div>
          <div className={styles.kv}><span className={styles.k}>network</span><span className={`${styles.val} mono`}>{a.asn != null ? `AS${a.asn}` : "—"}{a.as_org ? ` · ${a.as_org}` : ""} · {a.geo_country ?? "—"} · {a.net_class}</span></div>
          <div className={styles.kv}><span className={styles.k}>p(origin)</span><span className={`${styles.val} mono`}>{dec(a.p_origin)} · margin {dec(a.margin)}</span></div>
        </div>

        <div className={styles.section}>
          <span className={styles.secTitle}>findings</span>
          <ul className={styles.list}>
            {packet.findings.map((f, i) => (
              <li key={i} className={styles.finding}>
                <span className={styles.stmt}>{f.statement}</span>
                <span className={`${styles.ref} mono`}>{f.kind} · {f.source_ref}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className={styles.section} data-cool>
          <span className={styles.secTitle} data-cool>counter-findings</span>
          {packet.counter_findings.length === 0 ? (
            <div className={styles.mismatch} role="alert">
              <span className={styles.mismatchMark}>PIPELINE DEFECT</span>
              <p className={styles.mismatchText}>
                This packet carries no counter-findings. Every packet must; an empty section means
                the pipeline dropped the argument against, not that none exists.
              </p>
            </div>
          ) : (
            <ul className={styles.list}>
              {packet.counter_findings.map((c, i) => (
                <li key={i} className={styles.finding}>
                  {c.would_clear && <span className={styles.wouldClear}>WOULD CLEAR</span>}
                  <span className={styles.stmt}>{c.statement}</span>
                  <span className={`${styles.ref} mono`}>{c.kind}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className={styles.section}>
          <span className={styles.secTitle}>confidence</span>
          {!hasInterval(packet.confidence.low, packet.confidence.high) ? (
            <div className={styles.mismatch} role="alert">
              <span className={styles.mismatchMark}>NO INTERVAL</span>
              <p className={styles.mismatchText}>
                A score without its conformal interval is not shown. The interval is the claim; the
                point alone is not evidence.
              </p>
            </div>
          ) : (
            <>
              <RangeBar low={packet.confidence.low} high={packet.confidence.high} />
              <span className={`${styles.cov} mono`}>
                [{dec(packet.confidence.low)}, {dec(packet.confidence.high)}] at {dec(packet.confidence.coverage_target)} target · {packet.confidence.method}
              </span>
            </>
          )}
        </div>

        <div className={styles.section}>
          <span className={styles.secTitle}>hash chain</span>
          <HashBlock label="merkle head · in full" value={packet.merkle_head} />
          <HashBlock label="ed25519 signature" value={packet.ed25519_signature} />
        </div>

        <div className={styles.section}>
          <span className={styles.secTitle}>replay</span>
          <div className={styles.replay}>
            <code className={`${styles.cmd} mono`}>{packet.replay.command}</code>
            <button className={styles.copy} onClick={onCopyReplay} title="copy replay command (c)">COPY · c</button>
          </div>
          <span className={`${styles.seed} mono`}>seed {packet.replay.seed}</span>
          <HashBlock label="expected packet sha-256" value={packet.replay.expected_packet_sha256} />
        </div>
      </section>

      {/* RIGHT — the production notice an investigator serves */}
      <aside className={styles.notice} aria-label="production notice">
        <div className={styles.noticeDoc}>
          <div className={styles.noticeHead}>
            <span className={styles.noticeStatute}>NOTICE UNDER SECTION 94</span>
            <span className={styles.noticeAct}>The Bharatiya Nagarik Suraksha Sanhita, 2023</span>
          </div>

          <p className={styles.para}><span className={styles.para_k}>To:</span> {packet.notice.exchange}</p>
          <p className={styles.para}><span className={styles.para_k}>Re:</span> account(s) controlling cluster <span className="mono">{packet.subject.cluster_id}</span></p>

          <p className={styles.para}>
            Pursuant to Section 94 of the Bharatiya Nagarik Suraksha Sanhita, 2023, you are
            required to produce the following records, which are necessary for the purposes of an
            investigation into the transaction attributed below:
          </p>

          <ol className={styles.records}>
            {packet.notice.requested_records.map((r, i) => <li key={i} className={styles.record}>{r}</li>)}
          </ol>

          <p className={styles.para}>
            The transaction was announced from <span className="mono">{a.peer_ip}:{a.peer_port}</span>
            {a.as_org ? <> ({a.as_org}{a.asn != null ? `, AS${a.asn}` : ""})</> : null} on{" "}
            <span className="mono">{a.observed_at_utc}</span>, estimated as the originating node with
            probability <span className="mono">{dec(a.p_origin)}</span>.
          </p>

          <p className={styles.legal}>
            Legal basis: {packet.legal.basis}. Hash disclosure: {packet.legal.hash_disclosure}.
          </p>

          <div className={styles.noticeFoot}>
            <span>Case <span className="mono">{packet.case_id}</span>. Accompanying evidence packet sealed and signed (Ed25519); Merkle root as printed opposite.</span>
          </div>
        </div>
      </aside>
    </div>
  );
}

export function Packet() {
  const [packet, setPacket] = useState<PacketT | null>(null);
  const [last, setLast] = useState<LastCall | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    adapter.listAlerts().then((rows) => {
      const caseId = rows[0]?.case_id ?? "";
      const t0 = performance.now();
      adapter.getPacket(caseId).then((p) => {
        setPacket(p);
        setLast({ label: `getPacket(${p.case_id})`, ms: Math.round(performance.now() - t0) });
      });
    });
  }, []);

  const copyReplay = () => {
    if (!packet) return;
    navigator.clipboard?.writeText(packet.replay.command).then(
      () => { setCopied(true); setTimeout(() => setCopied(false), 1200); },
      () => {},
    );
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA")) return;
      if (e.key === "c") copyReplay();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [packet]);

  if (!packet) {
    return (
      <div className={styles.page}>
        <div className={styles.loading}>loading packet…</div>
        <CommandLine last={last} />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <span className={styles.crumb}>DRISHTI · /_packet · <span className="mono">{packet.case_id}</span></span>
        <span className={styles.copyHint} data-copied={copied || undefined}>{copied ? "replay command copied" : "c — copy replay command"}</span>
      </div>
      <PacketView packet={packet} onCopyReplay={copyReplay} />
      <CommandLine last={last} />
    </div>
  );
}
