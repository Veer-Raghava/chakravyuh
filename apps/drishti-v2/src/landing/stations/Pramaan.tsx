import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";
import { fixtures } from "../../data/loader";

/**
 * ST.7 PRAMAAN — the court-ready proof (§7, the finish line). The single
 * surviving lead is pressed into a real EVIDENCE PACKET document — reproduced
 * directly from the packet layout, printed over a crumpled sheet of warm paper
 * (soft wrinkles the light catches) so it reads as a physical sealed exhibit,
 * not a glassy UI card (no backdrop blur — it "fits in" as paper). A red wax
 * chakra seal thunks down at the corner: reproducible and admissible.
 *
 * HARD RULES: on-screen identifiers are truncated (peer IP two-octet masked,
 * txid/address prefix…suffix) while every SHA-256 prints IN FULL (§9 / BSA 2023
 * §63(4)). Full IPs never reach the screen; the ASN + country carry attribution.
 * All values come from the packet fixture — nothing invented.
 */
const SLICE = STATIONS[7].slice;
const P = fixtures.packet;
const A = P.attribution;

const utc = (us: number) => new Date(us / 1000).toISOString().slice(0, 19).replace("T", " ") + "Z";
const GEN = utc(P.generated_at_us);
// two-octet mask — no full IP ever reaches the screen (§6/§9)
const PEER = A.peer_ip.split(".").slice(0, 2).join(".") + ".x.x";
// origin tx + subject already arrive truncated in the fixture statements
const ORIGIN_TX = "da4daa38…8b27";
const SUBJECT = P.subject.subject_id; // addr:bc1qge…3182
const CHAIN = P.chain_of_custody.map((c) => ({ stage: c.stage, when: utc(c.at_us), sha: c.sha256 }));
const KEY_FINDINGS = P.findings.map((f) => f.statement).slice(0, 5);
const PACKET_SHA = P.replay.expected_packet_sha256;
const ROWS = P.input.rows_sealed.toLocaleString("en-IN");

// crumpled-paper page: a subdivided plane z-displaced by layered sines so the
// directional light catches soft wrinkles — reads as pressed paper, no texture
// asset, no dep, deterministic (§4 material, offline rule).
function makePaper(w: number, h: number) {
  const g = new THREE.PlaneGeometry(w, h, 30, 40);
  const pos = g.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z =
      (Math.sin(x * 3.1 + y * 2.3) * 0.5 +
        Math.sin(x * 7.7 - y * 5.1) * 0.26 +
        Math.sin(x * 13.9 + y * 11.3) * 0.12) *
      0.045;
    pos.setZ(i, z);
  }
  g.computeVertexNormals();
  return g;
}

// ── document style atoms (crisp printed ink over paper, no glass) ──
const mono = "var(--font-mono)";
const serif = "var(--font-display)";
const sans = "var(--font-text)";
const microLabel = { fontFamily: mono, fontSize: 7, letterSpacing: "0.18em", textTransform: "uppercase" as const, color: "var(--ink-soft)" };
const datumSm = { fontFamily: mono, fontSize: 8.5, fontVariantNumeric: "tabular-nums" as const, color: "var(--ink)", letterSpacing: "0.01em" };
const sha = { fontFamily: mono, fontSize: 6, lineHeight: 1.3, color: "var(--ink-soft)", wordBreak: "break-all" as const, fontVariantNumeric: "tabular-nums" as const };
const secHead = { fontFamily: mono, fontSize: 9, letterSpacing: "0.16em", color: "var(--ink)", textTransform: "uppercase" as const, borderBottom: "1px solid var(--line)", paddingBottom: 3, marginBottom: 5, display: "flex", gap: 7, alignItems: "baseline" };
const secNo = { color: "var(--coral)", fontWeight: 700 as const };

function Badge({ title, sub }: { title: string; sub: string }) {
  return (
    <div style={{ flex: 1, border: "1px solid var(--line)", borderRadius: 4, padding: "5px 7px", background: "rgba(236,227,208,0.5)" }}>
      <div style={{ fontFamily: mono, fontSize: 7.5, letterSpacing: "0.1em", color: "var(--teal)", fontWeight: 700 }}>✓ {title}</div>
      <div style={{ fontFamily: sans, fontSize: 7.5, color: "var(--ink-soft)", marginTop: 1, lineHeight: 1.3 }}>{sub}</div>
    </div>
  );
}

// a small step in the ORIGIN ATTRIBUTION chain (arrow between steps)
function Step({ tag, value, accent }: { tag: string; value: string; accent?: boolean }) {
  return (
    <div style={{ flex: 1, textAlign: "center" }}>
      <div style={microLabel}>{tag}</div>
      <div style={{ ...datumSm, fontSize: 8, color: accent ? "var(--coral)" : "var(--ink)", marginTop: 2, fontWeight: accent ? 700 : 400 }}>{value}</div>
    </div>
  );
}

// a tiny offline "verify" glyph — deterministic QR-ish grid, not a real code
function VerifyGlyph() {
  const cells = useMemo(() => {
    const out: boolean[] = [];
    let s = 0x9f4d;
    for (let i = 0; i < 49; i++) {
      s = (s * 1103515245 + 12345) & 0x7fffffff;
      out.push((s >> 8) % 3 === 0);
    }
    return out;
  }, []);
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 4px)", gridAutoRows: "4px", gap: 0.5 }}>
      {cells.map((on, i) => (
        <div key={i} style={{ width: 4, height: 4, background: on ? "var(--ink)" : "transparent" }} />
      ))}
    </div>
  );
}

export function Pramaan({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const doc = useRef<THREE.Group>(null);
  const seal = useRef<THREE.Group>(null);
  const docHtml = useRef<HTMLDivElement>(null);
  const { progress } = useScroll();
  const [active, setActive] = useState(false);
  const activeRef = useRef(false);
  const paperGeo = useMemo(() => makePaper(4.9, 6.4), []);
  const backGeo = useMemo(() => makePaper(4.96, 6.46), []);
  const spokes = useMemo(() => Array.from({ length: 12 }, (_, i) => (i / 12) * Math.PI * 2), []);
  const mats = useMemo(
    () => ({
      paper: new THREE.MeshStandardMaterial({ color: C.paper, roughness: 0.97, metalness: 0, transparent: true, side: THREE.DoubleSide }),
      back: new THREE.MeshStandardMaterial({ color: C.paperDeep, roughness: 0.99, transparent: true, side: THREE.DoubleSide }),
      wax: new THREE.MeshStandardMaterial({ color: C.coral, roughness: 0.42, transparent: true }),
      waxDeep: new THREE.MeshStandardMaterial({ color: "#c8452e", roughness: 0.5, transparent: true }),
    }),
    [],
  );

  useFrame(() => {
    const g = group.current;
    if (!g) return;
    const p = progress.current ?? 0;
    const { t, vis } = local(p, SLICE);
    g.visible = vis > 0.01;
    const on = vis > 0.02; // gate the DOM (Html) with the slice — see Setu note
    if (on !== activeRef.current) {
      activeRef.current = on;
      setActive(on);
    }
    if (!g.visible) return;

    // the sheet settles flat with a hair of tilt easing out — precise, not floaty
    const a = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0, 0.4);
    if (doc.current) {
      doc.current.scale.setScalar(0.9 + 0.1 * a);
      doc.current.position.y = (1 - a) * -0.18;
      doc.current.rotation.x = (1 - a) * 0.16;
    }
    // ★ the wax seal thunks down over the back third, with a crisp overshoot
    const sealK = reduced ? 1 : THREE.MathUtils.clamp((t - 0.55) / 0.14, 0, 1);
    const base = THREE.MathUtils.smoothstep(sealK, 0, 1);
    const overshoot = 1 + (reduced ? 0 : Math.sin(THREE.MathUtils.clamp(sealK, 0, 1) * Math.PI) * 0.18);
    if (seal.current) {
      seal.current.scale.setScalar(0.0001 + base * overshoot);
      seal.current.rotation.z = (1 - base) * -0.5; // presses in with a slight twist
    }

    mats.paper.opacity = vis;
    mats.back.opacity = vis;
    mats.wax.opacity = vis * base;
    mats.waxDeep.opacity = vis * base;

    // the printed document fades/settles in slightly behind the sheet
    if (docHtml.current) {
      const k = reduced ? 1 : THREE.MathUtils.clamp((t - 0.12) / 0.28, 0, 1);
      docHtml.current.style.opacity = String(k * vis);
    }
  });

  return (
    <group ref={group} visible={false} position={[0, 0.1, 0]}>
      {/* the crumpled paper page (+ a slightly larger deep-paper backing) */}
      <group ref={doc}>
        <mesh geometry={paperGeo} material={mats.paper} />
        <mesh geometry={backGeo} material={mats.back} position={[0, 0, -0.05]} />
      </group>

      {/* ★ the wax chakra seal — pressed into the lower-right of the page */}
      <group ref={seal} position={[1.68, -2.42, 0.12]}>
        <mesh rotation={[Math.PI / 2, 0, 0]} material={mats.wax}>
          <cylinderGeometry args={[0.34, 0.36, 0.07, 44]} />
        </mesh>
        {/* raised rim */}
        <mesh material={mats.waxDeep}>
          <torusGeometry args={[0.32, 0.03, 12, 44]} />
        </mesh>
        {/* chakra spokes */}
        {spokes.map((th, i) => (
          <mesh key={i} rotation={[0, 0, th]} position={[Math.cos(th) * 0.16, Math.sin(th) * 0.16, 0.02]} material={mats.waxDeep}>
            <boxGeometry args={[0.28, 0.018, 0.02]} />
          </mesh>
        ))}
        {/* hub */}
        <mesh position={[0, 0, 0.03]} rotation={[Math.PI / 2, 0, 0]} material={mats.waxDeep}>
          <cylinderGeometry args={[0.06, 0.06, 0.06, 20]} />
        </mesh>
      </group>

      {active && (
        <>
          {/* the printed EVIDENCE PACKET — crisp ink over the pressed paper */}
          <Html position={[0, 0.05, 0.1]} center distanceFactor={5.2} pointerEvents="none">
            <div
              ref={docHtml}
              style={{
                width: 620,
                color: "var(--ink)",
                textAlign: "left",
                padding: "16px 22px",
                // reads as paper, not glass: near-transparent so the crumpled
                // 3D sheet shows through; no backdrop blur (§ "fit in")
                background: "rgba(246,239,224,0.28)",
                borderRadius: 2,
              }}
            >
              {/* ── running header ── */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", fontFamily: mono, fontSize: 7, letterSpacing: "0.12em", color: "var(--ink-soft)", textTransform: "uppercase" }}>
                <span>CHAKRAVYUH · Bitcoin Forensic Analysis</span>
                <span style={{ color: "var(--coral)", fontWeight: 700 }}>PRAMAAN · Evidence Packet</span>
                <span>Offline · Tamper-proof</span>
              </div>

              {/* ── title block ── */}
              <div style={{ marginTop: 14, display: "flex", justifyContent: "space-between", alignItems: "flex-end", borderBottom: "2px solid var(--ink)", paddingBottom: 8 }}>
                <div style={{ fontFamily: serif, fontWeight: 500, fontSize: 34, lineHeight: 0.95, letterSpacing: "-0.01em" }}>Evidence Packet</div>
                <div style={{ fontFamily: mono, fontSize: 8, letterSpacing: "0.22em", color: "var(--ink-soft)" }}>TRANSACTION ORIGIN ANALYSIS</div>
              </div>

              {/* ── meta row ── */}
              <div style={{ display: "flex", gap: 22, marginTop: 9 }}>
                <div><div style={microLabel}>Case ID</div><div style={datumSm}>{P.case_id}</div></div>
                <div><div style={microLabel}>Generated · UTC</div><div style={datumSm}>{GEN}</div></div>
                <div><div style={microLabel}>Version</div><div style={datumSm}>{P.tool_version}</div></div>
                <div><div style={microLabel}>Code</div><div style={datumSm}>{P.code_version}</div></div>
              </div>

              {/* ── integrity badges ── */}
              <div style={{ display: "flex", gap: 8, marginTop: 11 }}>
                <Badge title="Integrity Verified" sub="SHA-256 over sealed files" />
                <Badge title="Replayable" sub={`deterministic · seed ${P.replay.seed}`} />
                <Badge title="Tamper-proof" sub="sealed & immutable" />
              </div>

              {/* ── 01 transaction summary ── */}
              <div style={{ ...secHead, marginTop: 14 }}><span style={secNo}>01</span> Transaction Summary</div>
              <div style={{ display: "flex", gap: 22, flexWrap: "wrap" }}>
                <div><div style={microLabel}>Origin Tx</div><div style={datumSm}>{ORIGIN_TX}</div></div>
                <div><div style={microLabel}>Subject</div><div style={datumSm}>{SUBJECT}</div></div>
                <div><div style={microLabel}>Rows Sealed</div><div style={datumSm}>{ROWS}</div></div>
                <div><div style={microLabel}>Legal Basis</div><div style={datumSm}>{P.legal.basis}</div></div>
              </div>

              {/* ── 02 key findings + mini graph ── */}
              <div style={{ ...secHead, marginTop: 13 }}><span style={secNo}>02</span> Key Findings</div>
              <div style={{ display: "flex", gap: 16 }}>
                <ol style={{ flex: 1, margin: 0, paddingLeft: 16, fontFamily: sans, fontSize: 8, lineHeight: 1.5, color: "var(--ink)" }}>
                  {KEY_FINDINGS.map((f, i) => (
                    <li key={i} style={{ marginBottom: 3 }}>{f}</li>
                  ))}
                </ol>
                <div style={{ width: 118, flexShrink: 0, border: "1px solid var(--line)", borderRadius: 4, padding: 7 }}>
                  <svg width="104" height="64" viewBox="0 0 104 64">
                    <line x1="20" y1="20" x2="52" y2="40" stroke="#d8cdb8" strokeWidth="1" />
                    <line x1="84" y1="18" x2="52" y2="40" stroke="#ff48b0" strokeWidth="1.2" />
                    <line x1="52" y1="40" x2="30" y2="56" stroke="#d8cdb8" strokeWidth="1" />
                    <circle cx="52" cy="40" r="5" fill="#ff6b4a" />
                    <circle cx="20" cy="20" r="4" fill="#1b1712" />
                    <rect x="80" y="14" width="8" height="8" fill="#5a5048" />
                    <circle cx="30" cy="56" r="3.5" fill="none" stroke="#2e5eaa" strokeWidth="1.2" />
                  </svg>
                  <div style={{ fontFamily: mono, fontSize: 5.5, lineHeight: 1.5, color: "var(--ink-soft)", marginTop: 3 }}>
                    <div><span style={{ color: "#ff6b4a" }}>●</span> transaction</div>
                    <div><span style={{ color: "#1b1712" }}>●</span> wallet (cluster)</div>
                    <div><span style={{ color: "#5a5048" }}>■</span> network peer</div>
                    <div><span style={{ color: "#2e5eaa" }}>○</span> IP / ASN</div>
                  </div>
                </div>
              </div>

              {/* ── 03 origin attribution chain ── */}
              <div style={{ ...secHead, marginTop: 13 }}><span style={secNo}>03</span> Origin Attribution</div>
              <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <Step tag="Transaction" value={ORIGIN_TX} />
                <span style={{ color: "var(--ink-soft)" }}>→</span>
                <Step tag="Announcing Peer" value={`${PEER}:${A.peer_port}`} accent />
                <span style={{ color: "var(--ink-soft)" }}>→</span>
                <Step tag="Network Operator" value={`AS${A.asn} · ${A.geo_country}`} />
                <span style={{ color: "var(--ink-soft)" }}>→</span>
                <Step tag="Origin Likelihood" value={`p = ${A.p_origin.toFixed(3)}`} />
              </div>
              <div style={{ fontFamily: sans, fontSize: 7.5, color: "var(--ink-soft)", marginTop: 4, fontStyle: "italic" }}>
                margin over runner-up {A.margin.toFixed(3)} — thin. Full IP lives only in packet.json; the operator carries attribution on screen.
              </div>

              {/* ── 04 chain of custody ── */}
              <div style={{ ...secHead, marginTop: 13 }}><span style={secNo}>04</span> Chain of Custody</div>
              <div>
                <div style={{ display: "flex", ...microLabel, borderBottom: "1px solid var(--line)", paddingBottom: 2 }}>
                  <span style={{ width: 72 }}>Stage</span>
                  <span style={{ width: 132 }}>Timestamp · UTC</span>
                  <span style={{ flex: 1 }}>Artifact Hash · SHA-256 (full)</span>
                </div>
                {CHAIN.map((c) => (
                  <div key={c.stage} style={{ display: "flex", alignItems: "baseline", padding: "2px 0", borderBottom: "1px solid rgba(216,205,184,0.5)" }}>
                    <span style={{ ...datumSm, width: 72, color: "var(--coral)", textTransform: "uppercase", fontSize: 7.5, letterSpacing: "0.08em" }}>{c.stage}</span>
                    <span style={{ ...datumSm, width: 132, fontSize: 7.5, color: "var(--ink-soft)" }}>{c.when}</span>
                    <span style={{ ...sha, flex: 1 }}>{c.sha}</span>
                  </div>
                ))}
              </div>

              {/* ── footer: verify · packet hash · seal caption ── */}
              <div style={{ display: "flex", gap: 16, marginTop: 13, alignItems: "flex-start" }}>
                <div style={{ textAlign: "center" }}>
                  <VerifyGlyph />
                  <div style={{ ...microLabel, marginTop: 3 }}>Verify Offline</div>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={microLabel}>Packet Hash · SHA-256 (full)</div>
                  <div style={{ ...sha, color: "var(--riso-blue)" }}>{PACKET_SHA}</div>
                  <div style={{ ...microLabel, marginTop: 5 }}>Replay</div>
                  <div style={{ ...sha, fontSize: 6, color: "var(--ink-soft)" }}>{P.replay.command}</div>
                </div>
                <div style={{ width: 96, textAlign: "right", fontFamily: mono, fontSize: 7, color: "var(--ink-soft)", letterSpacing: "0.06em" }}>
                  <div style={{ fontFamily: serif, fontSize: 12, color: "var(--ink)" }}>Not a guess.</div>
                  <div style={{ fontFamily: serif, fontSize: 12, color: "var(--ink)", marginBottom: 3 }}>A document.</div>
                  {P.case_id} · PRAMAAN<br />PAGE 1/1
                </div>
              </div>
            </div>
          </Html>

          {/* the wax-seal caption */}
          <Html position={[1.68, -2.42, 0.18]} center distanceFactor={5.2} pointerEvents="none">
            <div style={{ fontFamily: mono, fontSize: 5, fontWeight: 700, letterSpacing: "0.14em", color: "var(--paper)", textAlign: "center", lineHeight: 1.3 }}>
              CHAKRAVYUH
              <br />
              PRAMAAN
            </div>
          </Html>
        </>
      )}
    </group>
  );
}
