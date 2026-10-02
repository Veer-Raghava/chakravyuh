import {
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  Canvas,
  useFrame,
  useThree,
  type ThreeEvent,
} from "@react-three/fiber";
import { AdaptiveDpr } from "@react-three/drei";
import * as THREE from "three";
import { C } from "../../styles/palette";
import {
  latLonToVec3,
  greatCircleArc,
  makeDotTexture,
} from "../../three/globe";
import { loadCoastlines, type CoastLine } from "../../three/globeGeo";
import {
  buildGlobeData,
  type GlobeTx,
  type GlobePoint,
} from "../../data/globe";
import { useRun } from "../../data/RunContext";
import { usePrefersReducedMotion } from "../../scroll/usePrefersReducedMotion";
import { useShell } from "../ShellContext";
import { GlobeDetail } from "./GlobeDetail";
import styles from "./GlobeScreen.module.css";

/**
 * The app-home globe (§9) — the establishing shot after login. A matte Paper
 * sphere with ink-hairline coastlines (NOT photoreal), the located announcements
 * plotted as risk/likelihood-tinted dots, grey for unlocated/Tor, fluoro-pink
 * great-circle arcs for a selected tx, India gently emphasised. Built in the
 * repo's own R3F stack (no react-globe.gl, no new dep) so it stays fully offline;
 * the coastlines come from a vendored local GeoJSON. Click a point → the shared
 * Properties drawer (never a modal). Reduced motion = completely still.
 */

const R = 1.6;
const COAST_URL = "/assets/geo/coastline-110m.geojson";
const INDIA: [number, number] = [22.5, 79.0];
const TIER_COLOR: Record<GlobePoint["tier"], string> = {
  high: C.coral,
  med: C.butter,
  low: C.risoBlue,
  unknown: C.inkSoft,
};

/** Bring `target` within ±π of `cur` so a snap lerps the short way round. */
function nearestAngle(cur: number, target: number): number {
  let d = (target - cur) % (2 * Math.PI);
  if (d > Math.PI) d -= 2 * Math.PI;
  if (d < -Math.PI) d += 2 * Math.PI;
  return cur + d;
}
/** Yaw (rotation.y) that brings a lat/lon to face the camera (+z). */
function faceYaw(lat: number, lon: number): number {
  const dir = latLonToVec3(lat, lon, 1, new THREE.Vector3());
  return Math.PI / 2 - Math.atan2(dir.z, dir.x);
}
const INITIAL_YAW = faceYaw(INDIA[0], INDIA[1]); // open India-forward
const BASE_TILT = 0.32; // gentle axial tilt
const SPIN = 0.05; // idle breathing spin (rad/s)

/** Shared pointer-drag state between the DOM handlers (outside the Canvas) and the
 *  in-scene World that reads it each frame. */
type Drive = {
  dragging: boolean;
  moved: boolean; // passed the click/drag threshold this press → suppress the dot click
  lastX: number;
};

/** Fit the globe to whatever canvas it's handed (any screen / aspect), with a little
 *  margin, instead of a hard-coded camera distance that only frames one viewport. */
function FitCamera() {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const size = useThree((s) => s.size);
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => {
    const fov = (camera.fov * Math.PI) / 180;
    const margin = 1.12; // globe fills ~89% of the tighter axis, always fully in frame
    const aspect = size.width / Math.max(1, size.height);
    const fitH = (R * margin) / Math.tan(fov / 2);
    const fitW = (R * margin) / (Math.tan(fov / 2) * aspect);
    camera.position.set(0, 0, Math.max(fitH, fitW));
    camera.updateProjectionMatrix();
    invalidate();
  }, [camera, size, invalidate]);
  return null;
}

function Sphere() {
  return (
    <mesh>
      <sphereGeometry args={[R, 64, 64]} />
      <meshBasicMaterial color={C.paperDeep} />
    </mesh>
  );
}

function Coastlines() {
  const [lines, setLines] = useState<CoastLine[]>([]);
  useEffect(() => {
    let alive = true;
    loadCoastlines(COAST_URL, R * 1.002).then((l) => alive && setLines(l));
    return () => {
      alive = false;
    };
  }, []);
  const objs = useMemo(
    () =>
      lines.map((arr) => {
        const g = new THREE.BufferGeometry();
        g.setAttribute("position", new THREE.BufferAttribute(arr, 3));
        const m = new THREE.LineBasicMaterial({
          color: C.ink,
          transparent: true,
          opacity: 0.42,
        });
        return new THREE.Line(g, m);
      }),
    [lines],
  );
  useEffect(
    () => () =>
      objs.forEach((o) => {
        o.geometry.dispose();
        (o.material as THREE.Material).dispose();
      }),
    [objs],
  );
  return (
    <>
      {objs.map((o, i) => (
        <primitive key={i} object={o} />
      ))}
    </>
  );
}

/** Subtle butter ring tangent at India — emphasis, not a giant glow. */
function IndiaMark() {
  const { pos, quat } = useMemo(() => {
    const p = latLonToVec3(INDIA[0], INDIA[1], R * 1.015, new THREE.Vector3());
    const q = new THREE.Quaternion().setFromUnitVectors(
      new THREE.Vector3(0, 0, 1),
      p.clone().normalize(),
    );
    return { pos: p, quat: q };
  }, []);
  return (
    <mesh position={pos} quaternion={quat}>
      <ringGeometry args={[0.17, 0.2, 48]} />
      <meshBasicMaterial
        color={C.butter}
        transparent
        opacity={0.32}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

/** The ambient signal field: every other real announcing IP we heard, placed at its
 *  country. One cheap draw call (a point cloud), faint so the bright candidates lead. */
function AmbientField({
  ambientPoints,
}: {
  ambientPoints: { lat: number; lon: number }[];
}) {
  const sprite = useMemo(() => makeDotTexture(), []);
  useEffect(() => () => sprite.dispose(), [sprite]);
  const geom = useMemo(() => {
    const arr = new Float32Array(ambientPoints.length * 3);
    const v = new THREE.Vector3();
    ambientPoints.forEach((p, i) => {
      latLonToVec3(p.lat, p.lon, R * 1.006, v);
      arr[i * 3] = v.x;
      arr[i * 3 + 1] = v.y;
      arr[i * 3 + 2] = v.z;
    });
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(arr, 3));
    return g;
  }, [ambientPoints]);
  useEffect(() => () => geom.dispose(), [geom]);
  return (
    <points geometry={geom}>
      <pointsMaterial
        map={sprite}
        alphaTest={0.05}
        color={C.risoBlue}
        size={0.023}
        sizeAttenuation
        transparent
        opacity={0.5}
        depthWrite={false}
      />
    </points>
  );
}

function Points({
  onSelect,
  onHover,
  locatedPoints,
}: {
  locatedPoints: { tx: GlobeTx; point: GlobePoint }[];
  onSelect: (tx: GlobeTx, p: GlobePoint) => void;
  onHover: (on: boolean) => void;
}) {
  const [hover, setHover] = useState<string | null>(null);
  const dot = useMemo(() => new THREE.CircleGeometry(1, 24), []);
  useEffect(() => () => dot.dispose(), [dot]);
  return (
    <>
      {locatedPoints.map(({ tx, point }) => {
        const pos = latLonToVec3(
          point.lat,
          point.lon,
          R * 1.012,
          new THREE.Vector3(),
        );
        const base = point.isLeader ? 0.024 : 0.014;
        const orientation = new THREE.Quaternion().setFromUnitVectors(
          new THREE.Vector3(0, 0, 1),
          pos.clone().normalize(),
        );
        const s = hover === tx.txid + point.ipSeed ? base * 1.6 : base;
        return (
          <mesh
            key={tx.txid + point.ipSeed}
            position={pos}
            quaternion={orientation}
            scale={1}
            onPointerOver={(e: ThreeEvent<PointerEvent>) => {
              e.stopPropagation();
              setHover(tx.txid + point.ipSeed);
              onHover(true);
            }}
            onPointerOut={() => {
              setHover(null);
              onHover(false);
            }}
            onClick={(e: ThreeEvent<MouseEvent>) => {
              e.stopPropagation();
              onSelect(tx, point);
            }}
          >
            <sphereGeometry args={[0.07, 12, 12]} />
            <meshBasicMaterial transparent opacity={0} depthWrite={false} />
            <mesh geometry={dot} scale={s}>
              <meshBasicMaterial
                color={TIER_COLOR[point.tier]}
                side={THREE.DoubleSide}
              />
            </mesh>
          </mesh>
        );
      })}
    </>
  );
}

/** Fluoro-pink great-circle arcs from a selected tx's hub peer to its announcers. */
function Arcs({ tx }: { tx: GlobeTx | null }) {
  const objs = useMemo(() => {
    if (!tx) return [];
    const pts = tx.points.filter((p) => p.located);
    const hub = pts.find((p) => p.isLeader) ?? pts[0];
    if (!hub) return [];
    const a = latLonToVec3(hub.lat, hub.lon, R, new THREE.Vector3());
    const SEG = 40;
    return pts
      .filter((p) => p !== hub)
      .map((p) => {
        const b = latLonToVec3(p.lat, p.lon, R, new THREE.Vector3());
        const arr = new Float32Array((SEG + 1) * 3);
        greatCircleArc(a, b, SEG, R * 1.01, 0.35, arr, 0);
        const g = new THREE.BufferGeometry();
        g.setAttribute("position", new THREE.BufferAttribute(arr, 3));
        const m = new THREE.LineBasicMaterial({
          color: C.fluoroPink,
          transparent: true,
          opacity: 0.85,
        });
        return new THREE.Line(g, m);
      });
  }, [tx]);
  useEffect(
    () => () =>
      objs.forEach((o) => {
        o.geometry.dispose();
        (o.material as THREE.Material).dispose();
      }),
    [objs],
  );
  return (
    <>
      {objs.map((o, i) => (
        <primitive key={i} object={o} />
      ))}
    </>
  );
}

/** The rotating world group. Idle: a slow continuous breathing spin. Grab it and it
 *  turns with the cursor and stays where you let go; releasing resumes the spin right
 *  away. A clicked point still snaps to face the camera. Frozen under reduced motion. */
function World({
  reduced,
  focus,
  grp,
  drive,
  children,
}: {
  reduced: boolean;
  focus: GlobePoint | null;
  grp: React.RefObject<THREE.Group>;
  drive: React.MutableRefObject<Drive>;
  children: ReactNode;
}) {
  const snap = useRef<number | null>(null);

  useEffect(() => {
    if (!focus || reduced || !grp.current) return;
    snap.current = nearestAngle(
      grp.current.rotation.y,
      faceYaw(focus.lat, focus.lon),
    );
  }, [focus, reduced, grp]);

  useFrame((_, delta) => {
    const g = grp.current;
    if (!g || reduced) return;

    if (drive.current.dragging) return; // rotation is driven by the pointer handlers
    if (snap.current != null) {
      g.rotation.y = THREE.MathUtils.lerp(g.rotation.y, snap.current, 0.1);
      if (Math.abs(g.rotation.y - snap.current) < 0.002) snap.current = null;
      return;
    }
    g.rotation.y += delta * SPIN; // continuous idle spin — no pause
  });

  return (
    <group ref={grp} rotation={[BASE_TILT, INITIAL_YAW, 0]}>
      {children}
    </group>
  );
}

function Fallback({
  locatedPoints,
}: {
  locatedPoints: { tx: GlobeTx; point: GlobePoint }[];
}) {
  return (
    <div className={styles.fallback}>
      <p>Located announcements (3D globe needs WebGL):</p>
      <ul>
        {locatedPoints.map(({ tx, point }) => (
          <li key={tx.txid + point.ipSeed}>
            {point.ipDisplay} · {point.country} · AS{point.asn} · likelihood{" "}
            {(point.pOrigin * 100).toFixed(1)}%
          </li>
        ))}
      </ul>
    </div>
  );
}

export function GlobeScreen() {
  const { openDrawer, goTo } = useShell();
  const { fixtures, selectTx, run } = useRun();
  const { globeTxs, locatedPoints, ambientPoints, unlocatedCount } = useMemo(
    () =>
      buildGlobeData(
        {
          ...fixtures,
          origin: run.payload.origin!,
          originAbstain: run.payload.originAbstain!,
        },
        Boolean(run.payload.originAbstain),
      ),
    [run.payload],
  );
  const reduced = usePrefersReducedMotion();
  const [selectedTx, setSelectedTx] = useState<GlobeTx | null>(null);
  const [focus, setFocus] = useState<GlobePoint | null>(null);
  const grp = useRef<THREE.Group>(null);
  const drive = useRef<Drive>({ dragging: false, moved: false, lastX: 0 });
  const [hovering, setHovering] = useState(false);
  const countries = useMemo(() => {
    const by = new Map<
      string,
      { count: number; point: GlobePoint; tx: GlobeTx }
    >();
    const seen = new Set<string>();
    for (const { tx, point } of locatedPoints) {
      if (seen.has(point.ipSeed)) continue;
      seen.add(point.ipSeed);
      const country = point.country ?? "Unlocated";
      const prev = by.get(country);
      by.set(country, { count: (prev?.count ?? 0) + 1, point, tx });
    }
    return [...by].sort((a, b) => b[1].count - a[1].count);
  }, [locatedPoints]);

  const onSelect = (tx: GlobeTx, point: GlobePoint) => {
    if (drive.current.moved) return; // that press was a drag, not a click
    setSelectedTx(tx);
    selectTx(tx.txid);
    setFocus(point);
    openDrawer(
      `Transaction · ${tx.txidDisplay}`,
      <GlobeDetail tx={tx} focus={point} />,
    );
  };

  // Grab-to-turn (disabled under reduced motion, which keeps the globe completely still).
  // IMPORTANT: we do NOT capture the pointer on press — a plain click must fall through to
  // the 3D dots (R3F raycasts on pointerup). We only capture once a real drag has started,
  // so a drag that wanders off the canvas keeps turning the globe.
  const onDown = (e: React.PointerEvent) => {
    if (reduced) return;
    drive.current = { dragging: true, moved: false, lastX: e.clientX };
  };
  const onMove = (e: React.PointerEvent) => {
    const d = drive.current;
    if (!d.dragging || !grp.current) return;
    const dx = e.clientX - d.lastX;
    d.lastX = e.clientX;
    if (Math.abs(dx) > 2 && !d.moved) {
      d.moved = true; // crossed the drag threshold → it's a turn, not a click
      try {
        (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
      } catch {
        /* no active pointer (synthetic event) — ignore */
      }
    }
    grp.current.rotation.y += dx * 0.006;
  };
  const onUp = (e: React.PointerEvent) => {
    drive.current.dragging = false;
    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      /* was never captured — ignore */
    }
  };

  return (
    <section className={styles.screen}>
      <div
        className={styles.canvasWrap}
        style={{
          cursor: reduced ? "default" : hovering ? "pointer" : "grab",
          touchAction: "none",
        }}
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerCancel={onUp}
      >
        <Canvas
          frameloop={reduced ? "demand" : "always"}
          dpr={[1, 2]}
          gl={{ alpha: true, antialias: true }}
          camera={{ position: [0, 0, 4.4], fov: 45 }}
          fallback={<Fallback locatedPoints={locatedPoints} />}
        >
          <Suspense fallback={null}>
            <FitCamera />
            <ambientLight intensity={0.8} />
            <directionalLight position={[3, 2, 4]} intensity={1.05} />
            <World reduced={reduced} focus={focus} grp={grp} drive={drive}>
              <Sphere />
              <Coastlines />
              <IndiaMark />
              <AmbientField ambientPoints={ambientPoints} />
              <Points
                locatedPoints={locatedPoints}
                onSelect={onSelect}
                onHover={setHovering}
              />
              <Arcs tx={selectedTx} />
            </World>
            <AdaptiveDpr pixelated />
          </Suspense>
        </Canvas>
      </div>

      <div className={styles.overlay}>
        <div className={styles.head}>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>Globe</h1>
            <span className={styles.count}>
              {fixtures.world.funnel[0].count.toLocaleString("en-US")} signals
            </span>
          </div>
          <p className={styles.gloss}>
            Follow a transaction across the peers that observed it.
          </p>
          <div className={styles.casePicker}>
            {globeTxs.map((tx) => (
              <button
                type="button"
                key={tx.txid}
                aria-pressed={selectedTx?.txid === tx.txid}
                onClick={() => {
                  setSelectedTx(tx);
                  selectTx(tx.txid);
                  setFocus(tx.points.find((p) => p.located) ?? null);
                }}
              >
                {tx.abstain ? "Unresolved origin" : "Candidate trail"}{" "}
                <small>
                  {tx.txidDisplay} · {tx.points.length} peers
                </small>
              </button>
            ))}
          </div>
        </div>

        <aside
          className={styles.observationPanel}
          aria-label="Geographic observation index"
        >
          <span className={styles.panelLabel}>OBSERVATION ATLAS</span>
          <strong>{countries.length} country regions</strong>
          <p>Candidate peers in the exported example trails</p>
          {countries.slice(0, 7).map(([country, item]) => (
            <button
              key={country}
              type="button"
              onClick={() => {
                drive.current.moved = false;
                onSelect(item.tx, item.point);
              }}
            >
              <span>{country}</span>
              <i
                style={{
                  width: `${(item.count / Math.max(1, countries[0]?.[1].count ?? 1)) * 70}%`,
                }}
              />
              <strong>{item.count}</strong>
            </button>
          ))}
          {selectedTx && (
            <div className={styles.activeTrail}>
              <span>{selectedTx.txidDisplay}</span>
              <p>
                Arcs connect peers that reported this transaction; they do not
                reconstruct a packet route.
              </p>
              <button
                type="button"
                onClick={() => {
                  selectTx(selectedTx.txid);
                  goTo("map");
                }}
              >
                Follow the money →
              </button>
              <button
                type="button"
                onClick={() => {
                  selectTx(selectedTx.txid);
                  goTo("origin");
                }}
              >
                Compare origin candidates →
              </button>
            </div>
          )}
        </aside>
        <div className={styles.footRow}>
          <div className={styles.legend} style={{ pointerEvents: "auto" }}>
            <span className={styles.key}>
              <span className={styles.swatch} style={{ background: C.coral }} />{" "}
              leading candidate
            </span>
            <span className={styles.key}>
              <span
                className={styles.swatch}
                style={{ background: C.butter }}
              />{" "}
              notable candidate
            </span>
            <span className={styles.key}>
              <span
                className={styles.swatch}
                style={{ background: C.risoBlue }}
              />{" "}
              other announcer
            </span>
            <span className={styles.key}>
              <span
                className={styles.swatch}
                style={{ background: C.inkSoft }}
              />{" "}
              unlocated / Tor
            </span>
            <p className={styles.note}>
              positions are country-level only (centroid + jitter).{" "}
              {unlocatedCount} announced from no fixed place, so they are not
              plotted.
            </p>
          </div>
          <p className={styles.diya}>
            Click a dot and I'll show you who was talking to whom.
          </p>
        </div>
      </div>

      {/* every point reachable in the DOM (§5.5), not trapped in the canvas */}
      <ul className={styles.srList} aria-label="Located announcements">
        {locatedPoints.map(({ tx, point }) => (
          <li key={tx.txid + point.ipSeed}>
            Transaction {tx.txidDisplay}: {point.ipDisplay}, {point.country}, AS
            {point.asn}, origin likelihood {(point.pOrigin * 100).toFixed(1)}{" "}
            percent.
          </li>
        ))}
      </ul>
    </section>
  );
}
