import { Suspense, useEffect, useMemo, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { AdaptiveDpr } from "@react-three/drei";
import gsap from "gsap";
import { C } from "../../styles/palette";
import { leadIds, buildLeadFor, buildOverviewAll, buildGraphAll, satsToBTC } from "../../data/jaal";
import { usePrefersReducedMotion } from "../../scroll/usePrefersReducedMotion";
import { useShell } from "../ShellContext";
import { LeadScene, LeadDetail, type LeadSelection } from "./LeadView";
import { OverviewScene } from "./OverviewScene";
import { GraphScene } from "./GraphScene";
import styles from "./MapScreen.module.css";

/**
 * MAP · JAAL — the visual investigation tool (§10, readability-first). The MAIN view is
 * the GRAPH: the whole run as one field of transactions over time, linked by the money
 * that flowed between them (§10 signature moment #2). Two calmer companions ride alongside:
 *   GRAPH     the product — many txs + their money relations, read iso / top / front.
 *   OVERVIEW  a side view — the ranked leads alone as a calm spiral, no edges.
 *   LEAD      click any node in either and it opens as a lit diorama: WHO → SENT WHAT →
 *             TO WHOM → WHICH IPs saw it → WHY. The individual, in full.
 * Every view drills into LEAD; LEAD steps through the ranked leads.
 */

type View = "graph" | "overview" | "lead";
type LeadPreset = "side" | "iso" | "top";
type OvMode = "iso" | "top" | "flat";
type GraphMode = "iso" | "top" | "front";

const PRESETS: Record<"iso" | "side" | "top", [number, number, number]> = {
  iso: [4.6, 4.4, 7.0], // depth visible — fans, floors and the spiral all legible
  side: [0.02, 0.35, 8.4], // THE lead pitch shot — wire above, money below, pink between
  top: [0, 8.6, 0.001], // collapses to a clean flow / bird's-eye field
};

/** Presets only — no free-fly. GSAP-tweens between fixed viewpoints; reduced motion
 *  jumps straight there. Always looks at the diorama's centre. */
function CameraRig({
  pos,
  targetY,
  reduced,
}: {
  pos: [number, number, number];
  targetY: number;
  reduced: boolean;
}) {
  const cam = useThree((s) => s.camera);
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => {
    const [x, y, z] = pos;
    if (reduced) {
      cam.position.set(x, y, z);
      cam.lookAt(0, targetY, 0);
      invalidate();
      return;
    }
    const o = { x: cam.position.x, y: cam.position.y, z: cam.position.z };
    const tw = gsap.to(o, {
      x,
      y,
      z,
      duration: 0.8,
      ease: "power2.inOut",
      onUpdate: () => {
        cam.position.set(o.x, o.y, o.z);
        cam.lookAt(0, targetY, 0);
      },
    });
    return () => {
      tw.kill();
    };
  }, [pos, targetY, reduced, cam, invalidate]);
  return null;
}

export function MapScreen() {
  const { openDrawer, closeDrawer } = useShell();
  const reduced = usePrefersReducedMotion();
  const [view, setView] = useState<View>("graph");
  const [leadPreset, setLeadPreset] = useState<LeadPreset>("iso");
  const [ovMode, setOvMode] = useState<OvMode>("iso");
  const [graphMode, setGraphMode] = useState<GraphMode>("iso");
  const [leadTxId, setLeadTxId] = useState<string>(leadIds[0]);
  const [leadSel, setLeadSel] = useState<LeadSelection | null>(null);
  const [hovering, setHovering] = useState(false);

  const overview = useMemo(() => buildOverviewAll(), []);
  const graph = useMemo(() => buildGraphAll(), []);
  const lead = useMemo(() => buildLeadFor(leadTxId), [leadTxId]);
  const leadRank = leadIds.indexOf(leadTxId); // -1 when the tx isn't a ranked lead

  const clearSel = () => {
    setLeadSel(null);
    closeDrawer();
  };

  // drill into any transaction's flow — works for a ranked lead or any node in the graph
  const openTx = (txId: string) => {
    setLeadTxId(txId);
    setLeadSel({ type: "tx" });
    setView("lead");
    setLeadPreset("iso");
    openDrawer("transaction", <LeadDetail lead={buildLeadFor(txId)} sel={{ type: "tx" }} />);
  };

  const toGraph = () => {
    setView("graph");
    clearSel();
  };
  const toOverview = () => {
    setView("overview");
    clearSel();
  };

  // prev / next cycles the ranked leads; if we're on an off-list tx, start at its neighbours
  const step = (d: number) => {
    const at = leadIds.indexOf(leadTxId);
    const next = at < 0 ? (d > 0 ? 0 : leadIds.length - 1) : (at + d + leadIds.length) % leadIds.length;
    setLeadTxId(leadIds[next]);
    clearSel();
  };

  const onLeadSelect = (sel: LeadSelection) => {
    setLeadSel(sel);
    const title =
      sel.type === "tx"
        ? "transaction"
        : sel.type === "money"
          ? `${sel.node.role} · ${sel.node.label.replace(/^addr:/, "")}`
          : `the IP that told us · ${sel.ann.label.replace(/^peer:/, "")}`;
    openDrawer(title, <LeadDetail lead={lead} sel={sel} />);
  };

  const flat = view === "overview" && ovMode === "flat";
  const camPos: [number, number, number] =
    view === "lead"
      ? PRESETS[leadPreset]
      : view === "graph"
        ? graphMode === "iso"
          ? PRESETS.iso
          : graphMode === "top"
            ? PRESETS.top
            : PRESETS.side // "front" — look along Z at time × height
        : ovMode === "iso"
          ? PRESETS.iso
          : PRESETS.top;
  const targetY =
    view === "lead"
      ? leadPreset === "iso"
        ? 0.1
        : leadPreset === "side"
          ? 0.2
          : 0
      : view === "graph"
        ? 0.6
        : 0;

  const headline =
    view === "lead"
      ? lead.why
      : view === "graph"
        ? `${graph.count} transactions across the run · ${graph.bridged} linked by the money that moved between them`
        : `${overview.count} transactions worth a look · the loudest was seen by ${overview.loudest} IPs on the wire`;

  const title = view === "graph" ? "Graph" : view === "overview" ? "Overview" : "Lead";

  return (
    <section className={styles.screen}>
      <div
        className={styles.canvasWrap}
        style={{ cursor: hovering ? "pointer" : "default", touchAction: "none" }}
      >
        <Canvas
          frameloop={reduced ? "demand" : "always"}
          dpr={[1, 2]}
          gl={{ alpha: true, antialias: true }}
          camera={{ position: PRESETS.iso, fov: 42 }}
          fallback={<div className={styles.fallback}>This view needs WebGL. The transaction data is listed below the canvas.</div>}
          onPointerMissed={() => view === "lead" && clearSel()}
        >
          <Suspense fallback={null}>
            <CameraRig pos={camPos} targetY={targetY} reduced={reduced} />
            <ambientLight intensity={0.9} />
            <directionalLight position={[4, 6, 5]} intensity={1.05} castShadow />
            <directionalLight position={[-5, 3, -2]} intensity={0.35} color={C.risoBlue} />
            {view === "graph" ? (
              <GraphScene data={graph} reduced={reduced} activeId={null} onPick={openTx} onHover={setHovering} />
            ) : view === "overview" ? (
              <OverviewScene
                data={overview}
                flat={flat}
                activeId={leadRank >= 0 ? leadTxId : null}
                onPick={openTx}
                onHover={setHovering}
              />
            ) : (
              <LeadScene lead={lead} reduced={reduced} selection={leadSel} onSelect={onLeadSelect} onHover={setHovering} />
            )}
            <AdaptiveDpr pixelated />
          </Suspense>
        </Canvas>
      </div>

      <div className={styles.overlay}>
        <div className={styles.head}>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>{title}</h1>
            {view === "lead" && leadRank >= 0 && <span className={styles.count}>lead {leadRank + 1} of {leadIds.length}</span>}
          </div>
          <p className={styles.why}>{headline}</p>
          {view === "graph" && (
            <p className={styles.gloss}>the whole run as one graph — blue threads are value moving from one transaction to the next · click any ◆ to open its flow</p>
          )}
          {view === "overview" && (
            <p className={styles.gloss}>a calm map of the whole run — click any mark to open it in full</p>
          )}
          {view === "lead" && (
            <p className={styles.gloss}>
              {satsToBTC(lead.totalInSats)} in from {lead.senders.length}, out to {lead.receivers.length} · seen by {lead.announcers.length} IPs on the wire
            </p>
          )}
        </div>

        {/* the views — GRAPH is the product; OVERVIEW is the calm side view; LEAD the drill-in.
            In LEAD the switcher doubles as "back to the map". */}
        <div className={styles.views} style={{ pointerEvents: "auto" }}>
          <button
            type="button"
            className={`${styles.viewBtn} ${view === "graph" ? styles.viewOn : ""}`}
            onClick={toGraph}
          >
            ⬡ graph
          </button>
          <button
            type="button"
            className={`${styles.viewBtn} ${view === "overview" ? styles.viewOn : ""}`}
            onClick={toOverview}
          >
            ◎ overview
          </button>
          <button
            type="button"
            className={`${styles.viewBtn} ${view === "lead" ? styles.viewOn : ""}`}
            onClick={() => setView("lead")}
          >
            ◆ lead
          </button>
        </div>

        {view === "lead" && (
          <div className={styles.stepper} style={{ pointerEvents: "auto" }}>
            <button type="button" className={styles.step} onClick={() => step(-1)} aria-label="Previous lead">
              ‹ prev
            </button>
            <button type="button" className={styles.step} onClick={() => step(1)} aria-label="Next lead">
              next ›
            </button>
          </div>
        )}

        {/* camera / dimensionality — graph & overview each read three ways, lead keeps its three shots */}
        <div className={styles.presets} style={{ pointerEvents: "auto" }}>
          {view === "graph"
            ? (["iso", "top", "front"] as GraphMode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  className={`${styles.preset} ${graphMode === m ? styles.presetOn : ""}`}
                  onClick={() => setGraphMode(m)}
                >
                  {m === "iso" ? "◈ isometric" : m === "top" ? "◈ top-down" : "◈ front"}
                </button>
              ))
            : view === "overview"
              ? (["iso", "top", "flat"] as OvMode[]).map((m) => (
                  <button
                    key={m}
                    type="button"
                    className={`${styles.preset} ${ovMode === m ? styles.presetOn : ""}`}
                    onClick={() => setOvMode(m)}
                  >
                    {m === "iso" ? "◈ isometric 3D" : m === "top" ? "◈ top-down 3D" : "◈ flat 2D"}
                  </button>
                ))
              : (["side", "iso", "top"] as LeadPreset[]).map((p) => (
                  <button
                    key={p}
                    type="button"
                    className={`${styles.preset} ${leadPreset === p ? styles.presetOn : ""}`}
                    onClick={() => setLeadPreset(p)}
                  >
                    {p === "side" ? "◈ side-on" : p === "iso" ? "◈ isometric" : "◈ top-down"}
                  </button>
                ))}
        </div>

        {view === "lead" && (
          <div className={styles.legend} style={{ pointerEvents: "auto" }}>
            <span className={styles.key}><span className={styles.dot} style={{ background: C.risoBlue }} /> sender</span>
            <span className={styles.key}><span className={styles.dot} style={{ background: C.coral }} /> the transaction</span>
            <span className={styles.key}><span className={styles.dot} style={{ background: C.butter }} /> receiver</span>
            <span className={styles.key}><span className={styles.dot} style={{ background: C.inkSoft }} /> change · back to self</span>
            <span className={styles.key}><span className={styles.dot} style={{ background: C.fluoroPink }} /> the IP that told us</span>
          </div>
        )}

        {view === "graph" && (
          <div className={styles.legend} style={{ pointerEvents: "auto" }}>
            <span className={styles.key}><span className={styles.dot} style={{ background: C.coral }} /> a transaction</span>
            <span className={styles.key}><span className={styles.dot} style={{ background: C.risoBlue }} /> value moved tx → tx</span>
            <span className={styles.keyPlain}>left → right = time · taller = more IPs saw it · bright = part of a money chain</span>
          </div>
        )}

        {view === "overview" && (
          <div className={styles.legend} style={{ pointerEvents: "auto" }}>
            <span className={styles.key}><span className={styles.dot} style={{ background: C.coral }} /> a transaction</span>
            <span className={styles.keyPlain}>bigger = more money · taller = more IPs saw it · centre = most suspicious</span>
          </div>
        )}
      </div>

      {/* all data reachable in the DOM (§5.5), not trapped in the canvas */}
      <ul className={styles.srList} aria-label="Map data">
        {view === "graph" &&
          graph.nodes.map((n) => (
            <li key={n.id}>
              transaction {n.label.replace(/^tx:/, "")}, {satsToBTC(n.inSats)} in, seen by {n.announcers} IPs{n.connected ? ", linked to another transaction" : ""}
            </li>
          ))}
        {view === "overview" &&
          overview.nodes.map((n) => (
            <li key={n.txId}>
              transaction {n.label.replace(/^tx:/, "")}, {satsToBTC(n.inSats)} in, seen by {n.announcers} IPs
            </li>
          ))}
        {view === "lead" && (
          <>
            <li>transaction {lead.txLabel.replace(/^tx:/, "")}, {lead.why}</li>
            {lead.senders.map((s) => <li key={s.id}>sender {s.label.replace(/^addr:/, "")} {satsToBTC(s.sats)}</li>)}
            {lead.receivers.map((r) => <li key={r.id}>{r.role} {r.label.replace(/^addr:/, "")} {satsToBTC(r.sats)}</li>)}
            {lead.announcers.map((a) => <li key={a.id}>announced by IP {a.label.replace(/^peer:/, "")}</li>)}
          </>
        )}
      </ul>
    </section>
  );
}
