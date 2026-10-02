import { Suspense, useEffect, useMemo, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { AdaptiveDpr } from "@react-three/drei";
import gsap from "gsap";
import { C } from "../../styles/palette";
import { buildJaalData, satsToBTC } from "../../data/jaal";
import type { LaidNode } from "../../three/jaalLayout";
import { usePrefersReducedMotion } from "../../scroll/usePrefersReducedMotion";
import { useShell } from "../ShellContext";
import { LeadScene, LeadDetail, type LeadSelection } from "./LeadView";
import { OverviewScene } from "./OverviewScene";
import { GraphScene, GraphDetail } from "./GraphScene";
import { useRun } from "../../data/RunContext";
import { FlowAtlas } from "./FlowAtlas";
import styles from "./MapScreen.module.css";

/**
 * MAP · JAAL — the visual investigation tool (§10, readability-first). The MAIN view is
 * the GRAPH: the whole run as ONE two-floor diorama — every announcing peer ▲ on the wire
 * above, every transaction ◆ on the money floor below, and the pink announce threads the
 * only thing crossing between (§10 signature moment #2). It stays calm at rest and REVEALS
 * on touch: hover/focus a tx and its coins fan out, its money flows light, its pink threads
 * rain up to the peers that saw it; focus a peer and its threads drop onto every tx it saw;
 * focus an address and its likely-same-owner ties show as honest teal links, gated by a dial.
 *   GRAPH     the product — the whole run, read iso / top / front, owners folded in as a dial.
 *   OVERVIEW  a calm side view — the ranked leads alone as a spiral, no edges.
 *   LEAD      click any ◆ and it opens as a lit diorama: WHO → SENT WHAT → TO WHOM →
 *             WHICH IPs saw it → WHY. The individual, in full.
 * Every view drills into LEAD; LEAD steps through the ranked leads.
 */

type View = "atlas" | "graph" | "overview" | "lead";
type LeadPreset = "side" | "iso" | "top";
type OvMode = "iso" | "top" | "flat";
type GraphMode = "iso" | "top" | "front";

const PRESETS: Record<"iso" | "side" | "top", [number, number, number]> = {
  iso: [4.6, 4.4, 7.0], // depth visible — fans, floors and the spiral all legible
  side: [0.02, 0.35, 8.4], // THE lead pitch shot — wire above, money below, pink between
  top: [0, 8.6, 0.001], // collapses to a clean flow / bird's-eye field
};

// GRAPH camera — the two-floor diorama centred on y=0 (wire at +1.5, money at −1.5):
// front reads it as the pitch shot (wire above / money below), iso adds the depth of the
// lanes, top separates the money floor into a clean flow field.
const GRAPH_PRESETS: Record<
  GraphMode,
  { pos: [number, number, number]; targetY: number }
> = {
  front: { pos: [0, 0.2, 9.4], targetY: 0 },
  iso: { pos: [5.8, 4.6, 8.0], targetY: 0 },
  top: { pos: [0, 9.6, 0.001], targetY: 0 },
};

/** Presets only — no free-fly. GSAP-tweens between fixed viewpoints; reduced motion
 *  jumps straight there. Always looks at the diorama's centre. */
function CameraRig({
  pos,
  targetY,
  reduced,
  fit = false,
}: {
  fit?: boolean;
  pos: [number, number, number];
  targetY: number;
  reduced: boolean;
}) {
  const cam = useThree((s) => s.camera);
  const invalidate = useThree((s) => s.invalidate);
  const size = useThree((s) => s.size);
  useEffect(() => {
    const scale = fit ? Math.max(1, 1.25 / (size.width / size.height)) : 1;
    const [x, y, z] = pos.map(n => n * scale);
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
  }, [pos, targetY, reduced, cam, invalidate, fit, size.width, size.height]);
  return null;
}

export function MapScreen() {
  const { openDrawer, closeDrawer } = useShell();
  const reduced = usePrefersReducedMotion();
  const { fixtures, selectedTx, selectTx, run } = useRun();
  const { atlasRaw, jaal, counts, leadIds, buildLeadFor, buildOverviewAll } =
    useMemo(
      () =>
        buildJaalData(
          { graphAddress: fixtures.graphAddress },
          run.payload.focusedGraphs,
        ),
      [fixtures.graphAddress, run.payload.focusedGraphs],
    );
  const [view, setView] = useState<View>("atlas");
  const [leadPreset, setLeadPreset] = useState<LeadPreset>("iso");
  const [ovMode, setOvMode] = useState<OvMode>("iso");
  const [graphMode, setGraphMode] = useState<GraphMode>("front");
  const [leadTxId, setLeadTxId] = useState<string>(
    selectedTx &&
      leadIds.includes(
        selectedTx.startsWith("tx:") ? selectedTx : `tx:${selectedTx}`,
      )
      ? selectedTx.startsWith("tx:")
        ? selectedTx
        : `tx:${selectedTx}`
      : leadIds[0],
  );
  const [tracePages, setTracePages] = useState({
    inputs: 0,
    outputs: 0,
    peers: 0,
  });
  const [leadSel, setLeadSel] = useState<LeadSelection | null>(null);
  const [focusId, setFocusId] = useState<string | null>(null); // pinned graph node (peer/addr)
  const [hovering, setHovering] = useState(false);

  const overview = useMemo(() => buildOverviewAll(), [buildOverviewAll]);
  const lead = useMemo(() => buildLeadFor(leadTxId), [leadTxId, buildLeadFor]);
  const sceneLead = useMemo(() => {
    const money = (nodes: typeof lead.senders, page: number, x: number) =>
      nodes
        .slice(page * 4, page * 4 + 4)
        .map((n, i, a) => ({
          ...n,
          pos: [x, -1.05, (i - (a.length - 1) / 2) * 1.25] as [
            number,
            number,
            number,
          ],
        }));
    const senders = money(lead.senders, tracePages.inputs, -2.7);
    const receivers = money(lead.receivers, tracePages.outputs, 2.7);
    const announcers = lead.announcers
      .slice(tracePages.peers * 6, tracePages.peers * 6 + 6)
      .map((n, i, a) => ({
        ...n,
        pos: [(i - (a.length - 1) / 2) * 0.85, 1.75, 0] as [
          number,
          number,
          number,
        ],
      }));
    return {
      ...lead,
      senders,
      receivers,
      announcers,
      flows: [
        ...senders.map((n) => ({
          from: n.pos,
          to: lead.txPos,
          sats: n.sats,
          role: n.role,
        })),
        ...receivers.map((n) => ({
          from: lead.txPos,
          to: n.pos,
          sats: n.sats,
          role: n.role,
        })),
      ],
      threads: announcers.map((n) => ({ from: n.pos, to: lead.txPos })),
    };
  }, [lead, tracePages]);
  const leadRank = leadIds.indexOf(leadTxId); // -1 when the tx isn't a ranked lead

  const clearLead = () => {
    setLeadSel(null);
    closeDrawer();
  };
  const clearFocus = () => {
    setFocusId(null);
    closeDrawer();
  };

  // drill into any transaction's flow — works for a ranked lead or any ◆ in the graph
  const openTx = (txId: string) => {
    setLeadTxId(txId);
    setTracePages({ inputs: 0, outputs: 0, peers: 0 });
    selectTx(txId);
    setLeadSel({ type: "tx" });
    setView("lead");
    setLeadPreset("iso");
    closeDrawer();
  };

  // pin a peer/address on the graph — spotlight it and read its properties (no flow of its
  // own, so it opens the drawer rather than pretending to drill into a transaction)
  const onFocus = (node: LaidNode | null) => {
    if (!node || node.kind === "transaction") {
      clearFocus();
      return;
    }
    setFocusId(node.id);
    const title =
      node.kind === "peer"
        ? `the IP that told us · ${node.label.replace(/^peer:/, "")}`
        : `address · ${node.label.replace(/^addr:/, "")}`;
    openDrawer(title, <GraphDetail node={node} jaal={jaal} />);
  };

  const toGraph = () => {
    setView("graph");
    clearLead();
  };
  const toOverview = () => {
    setView("overview");
    clearLead();
    clearFocus();
  };

  // prev / next cycles the ranked leads; if we're on an off-list tx, start at its neighbours
  const step = (d: number) => {
    const at = leadIds.indexOf(leadTxId);
    const next =
      at < 0
        ? d > 0
          ? 0
          : leadIds.length - 1
        : (at + d + leadIds.length) % leadIds.length;
    setTracePages({ inputs: 0, outputs: 0, peers: 0 });
    setLeadTxId(leadIds[next]);
    selectTx(leadIds[next]);
    clearLead();
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

  const camPos: [number, number, number] =
    view === "lead"
      ? PRESETS[leadPreset]
      : view === "graph"
        ? GRAPH_PRESETS[graphMode].pos
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
        ? GRAPH_PRESETS[graphMode].targetY
        : 0;

  const flat = view === "overview" && ovMode === "flat";

  const headline =
    view === "lead"
      ? lead.why
      : view === "graph"
        ? `${counts.transaction} transactions, ${counts.peer} IPs that saw them`
        : `${overview.count} worth a look`;

  const title =
    view === "graph" ? "Graph" : view === "overview" ? "Leads" : "Trace";

  if (view === "atlas")
    return (
      <FlowAtlas
        lead={lead}
        ids={leadIds}
        raw={atlasRaw}
        onPick={(id) => {
          setLeadTxId(id);
          selectTx(id);
          closeDrawer();
        }}
        onSpatial={() => {
          clearLead();
          setView("graph");
        }}
        onTrace={() => openTx(leadTxId)}
      />
    );
  return (
    <section className={styles.screen}>
      <div
        className={styles.canvasWrap}
        style={{
          cursor: hovering ? "pointer" : "default",
          touchAction: "none",
        }}
      >
        <Canvas
          frameloop={reduced ? "demand" : "always"}
          dpr={[1, 2]}
          gl={{ alpha: true, antialias: true }}
          camera={{ position: PRESETS.iso, fov: 42 }}
          fallback={
            <div className={styles.fallback}>
              This view needs WebGL. The transaction data is listed below the
              canvas.
            </div>
          }
          onPointerMissed={() => {
            if (view === "lead") clearLead();
            else if (view === "graph") clearFocus();
          }}
        >
          <Suspense fallback={null}>
            <CameraRig pos={camPos} targetY={targetY} reduced={reduced} fit={view === "lead"} />
            <ambientLight intensity={0.9} />
            <directionalLight
              position={[4, 6, 5]}
              intensity={1.05}
              castShadow
            />
            <directionalLight
              position={[-5, 3, -2]}
              intensity={0.35}
              color={C.risoBlue}
            />
            {view === "graph" ? (
              <GraphScene
                jaal={jaal}
                reduced={reduced}
                focusId={focusId}
                onFocus={onFocus}
                onPickTx={openTx}
                onHover={setHovering}
              />
            ) : view === "overview" ? (
              <OverviewScene
                data={overview}
                flat={flat}
                activeId={leadRank >= 0 ? leadTxId : null}
                onPick={openTx}
                onHover={setHovering}
              />
            ) : (
              <LeadScene
                lead={sceneLead}
                reduced={reduced}
                selection={leadSel}
                onSelect={onLeadSelect}
                onHover={setHovering}
              />
            )}
            <AdaptiveDpr pixelated />
          </Suspense>
        </Canvas>
      </div>

      <div className={styles.overlay}>
        <div className={styles.head}>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>{title}</h1>
            {view === "lead" && leadRank >= 0 && (
              <span className={styles.count}>
                lead {leadRank + 1} of {leadIds.length}
              </span>
            )}
          </div>
          <p className={styles.why}>{headline}</p>
          {view === "overview" && (
            <p className={styles.gloss}>click any mark to open it in full</p>
          )}
          {view === "lead" && (
            <p className={styles.gloss}>
              {satsToBTC(lead.totalInSats)} in from {lead.senders.length}, out
              to {lead.receivers.length} · seen by {lead.announcers.length} IPs
            </p>
          )}
        </div>

        {/* the views — GRAPH is the product; OVERVIEW is the calm side view; LEAD the drill-in.
            In LEAD the switcher doubles as "back to the map". */}
        <div className={styles.views} style={{ pointerEvents: "auto" }}>
          <button
            type="button"
            className={styles.viewBtn}
            onClick={() => {
              clearLead();
              setView("atlas");
            }}
          >
            ↗ flow atlas
          </button>
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
            ◎ leads
          </button>
          <button
            type="button"
            className={`${styles.viewBtn} ${view === "lead" ? styles.viewOn : ""}`}
            onClick={() => setView("lead")}
          >
            ◆ trace
          </button>
        </div>

        {view === "lead" && (
          <div className={styles.tracePages}>
            {(
              [
                {
                  key: "inputs",
                  label: "Inputs",
                  nodes: lead.senders,
                  size: 4,
                },
                {
                  key: "outputs",
                  label: "Outputs",
                  nodes: lead.receivers,
                  size: 4,
                },
                {
                  key: "peers",
                  label: "Observed peers",
                  nodes: lead.announcers,
                  size: 6,
                },
              ] as const
            ).map((section) => {
              const page = tracePages[section.key];
              const count = section.nodes.length;
              return (
                <div key={section.key}>
                  <strong>{section.label}</strong>
                  <span>
                    {count ? page * section.size + 1 : 0}–
                    {Math.min(count, (page + 1) * section.size)} of {count}
                  </span>
                  <button
                    type="button"
                    aria-label={`Previous ${section.label}`}
                    disabled={page === 0}
                    onClick={() => {
                      clearLead();
                      setTracePages((p) => ({ ...p, [section.key]: page - 1 }));
                    }}
                  >
                    ‹
                  </button>
                  <button
                    type="button"
                    aria-label={`Next ${section.label}`}
                    disabled={(page + 1) * section.size >= count}
                    onClick={() => {
                      clearLead();
                      setTracePages((p) => ({ ...p, [section.key]: page + 1 }));
                    }}
                  >
                    ›
                  </button>
                </div>
              );
            })}
            <small>
              Browse every object. Totals above cover the complete transaction.
            </small>
          </div>
        )}
        {view === "lead" && (
          <div className={styles.stepper} style={{ pointerEvents: "auto" }}>
            <button
              type="button"
              className={styles.step}
              onClick={() => step(-1)}
              aria-label="Previous lead"
            >
              ‹ prev
            </button>
            <button
              type="button"
              className={styles.step}
              onClick={() => step(1)}
              aria-label="Next lead"
            >
              next ›
            </button>
          </div>
        )}

        {/* camera / dimensionality — graph & overview each read three ways, lead keeps its three shots. */}
        <div className={styles.presets} style={{ pointerEvents: "auto" }}>
          {view === "graph"
            ? (["front", "iso", "top"] as GraphMode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  className={`${styles.preset} ${graphMode === m ? styles.presetOn : ""}`}
                  onClick={() => setGraphMode(m)}
                >
                  {m === "front"
                    ? "◈ wire × money"
                    : m === "iso"
                      ? "◈ isometric"
                      : "◈ top-down"}
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
                    {m === "iso"
                      ? "◈ isometric 3D"
                      : m === "top"
                        ? "◈ top-down 3D"
                        : "◈ flat 2D"}
                  </button>
                ))
              : (["side", "iso", "top"] as LeadPreset[]).map((p) => (
                  <button
                    key={p}
                    type="button"
                    className={`${styles.preset} ${leadPreset === p ? styles.presetOn : ""}`}
                    onClick={() => setLeadPreset(p)}
                  >
                    {p === "side"
                      ? "◈ side-on"
                      : p === "iso"
                        ? "◈ isometric"
                        : "◈ top-down"}
                  </button>
                ))}
        </div>

        {view === "graph" && (
          <div className={styles.legend} style={{ pointerEvents: "auto" }}>
            <span className={styles.key}>
              <span className={styles.dot} style={{ background: C.coral }} />{" "}
              transaction
            </span>
            <span className={styles.key}>
              <span
                className={styles.dot}
                style={{ background: C.fluoroPink }}
              />{" "}
              IP that saw it
            </span>
          </div>
        )}

        {view === "overview" && (
          <div className={styles.legend} style={{ pointerEvents: "auto" }}>
            <span className={styles.key}>
              <span className={styles.dot} style={{ background: C.coral }} />{" "}
              transaction
            </span>
            <span className={styles.keyPlain}>
              bigger is more money, taller saw more IPs, centre is most
              suspicious
            </span>
          </div>
        )}
      </div>

      {/* all data reachable in the DOM (§5.5), not trapped in the canvas */}
      <ul className={styles.srList} aria-label="Map data">
        {view === "graph" &&
          jaal.nodes
            .filter((n) => n.kind === "transaction")
            .map((n) => (
              <li key={n.id}>transaction {n.label.replace(/^tx:/, "")}</li>
            ))}
        {view === "overview" &&
          overview.nodes.map((n) => (
            <li key={n.txId}>
              transaction {n.label.replace(/^tx:/, "")}, {satsToBTC(n.inSats)}{" "}
              in, seen by {n.announcers} IPs
            </li>
          ))}
        {view === "lead" && (
          <>
            <li>
              transaction {lead.txLabel.replace(/^tx:/, "")}, {lead.why}
            </li>
            {lead.senders.map((s) => (
              <li key={s.id}>
                sender {s.label.replace(/^addr:/, "")} {satsToBTC(s.sats)}
              </li>
            ))}
            {lead.receivers.map((r) => (
              <li key={r.id}>
                {r.role} {r.label.replace(/^addr:/, "")} {satsToBTC(r.sats)}
              </li>
            ))}
            {lead.announcers.map((a) => (
              <li key={a.id}>
                announced by IP {a.label.replace(/^peer:/, "")}
              </li>
            ))}
          </>
        )}
      </ul>
    </section>
  );
}
