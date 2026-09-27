import { useEffect, useMemo, useRef, useState } from "react";
import { useFrame, useThree, type ThreeEvent } from "@react-three/fiber";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";
import {
  assignEquirectUV,
  buildLandCanvas,
  fibonacciSphereDir,
  greatCircleArc,
  loadLandMaskSampler,
  makeDotTexture,
  makeSystemIcon,
  mulberry32,
  proceduralIsLand,
  type LandSampler,
} from "../../three/globe";

/**
 * ST.0 MAYAJAAL ★ — the world we built, as ONE rotating globe of peer systems.
 * A single stylized-Earth sphere (deep-sea ocean + warm-tan continents, painted
 * offline from `proceduralIsLand`) carries ~2,000 "systems" as dots on land. A
 * light scheduler makes one system broadcast a transaction to ~14 peers along
 * coral great-circle arcs every ~2.4s; a transmit ring marks the source, hit
 * peers flash butter, and a few of them *echo* it onward along dimmer teal arcs
 * — "one transaction, seen ~14 times — 93% of what you capture is echo," literal.
 *
 * Scroll assembles the world from a scattered cloud, holds while it gossips, then
 * dissolves (everything rides `vis`). Idle pointer parallax + hover-highlight +
 * mouse click-and-drag "hold and rotate" (mouse only, no pointer-capture, no
 * preventDefault) never capture scroll. Reduced-motion: static globe, one flood.
 *
 * Commit `src/assets/land-mask.png` (equirectangular, land = light) to swap the
 * stylized continents for the real ones — same code path, never hard-fails.
 */
const SLICE = STATIONS[0].slice;
const R = 1.35; // globe radius — compact (camera stays z=5 / fov45, untouched)
// Everything sizes off R so the whole globe scales as one unit.
const DOT_SIZE = R * 0.018; // peer-system dot size
const LIFT_GOSSIP = R * 0.19; // gossip arc bow height above the surface
const LIFT_ECHO = R * 0.09; // echo arc bow height (flatter than gossip)
const RING_IN = R * 0.028; // transmit ring inner radius
const RING_OUT = R * 0.042; // transmit ring outer radius
const ICON = R * 0.075; // transaction (computer) icon world size
const COUNT = 2000; // peer systems placed on land
const CANDIDATES = 12000; // fibonacci candidates filtered down to land
const K = 34; // arc pool (one flood's ~14 + echoes + overlap)
const ARC_SEG = 24; // points per great-circle arc
const FLOOD = 14; // "one tx, seen ~14 times"
const FLOOD_EVERY = 2.4; // seconds between gossip floods
const PULSE = 0.85; // seconds a pulse takes to travel source→dest
const ICON_LIFE = 1.3; // seconds a transaction icon lives (pop-in → hold → fade)
const TILT = 0.41; // ~23° axial tilt
// Rotation feel — all frame-rate independent (velocities in rad/s, exp-decay).
const AUTO_SPIN = 0.12; // idle yaw drift (rad/s)
const DRAG_SENS = 0.01; // radians turned per pixel dragged (raised → rotate more)
const PITCH_MAX = 1.45; // vertical tilt range (raised from 1.15 → rotate more)
const SPIN_FRICTION = 2.2; // fling glide (lower = longer, smoother coast)
const FLING_MAX = 9; // cap on fling velocity (rad/s) so a fast flick can't blur
const TEXW = 768; // land texture size (painted once, offline)
const TEXH = 384;

// Globe colors — deep-sea blue ocean + warm-tan land. Palette-derived (riso-blue
// + butter/paper) so it reads as a globe while staying in Riso Paper Pop.
const OCEAN: [number, number, number] = [38, 82, 148];
const LAND: [number, number, number] = [216, 198, 146];

// Optional stylized-Earth upgrade: committing src/assets/land-mask.png swaps the
// procedural world for real continents. import.meta.glob tolerates the file
// being absent (offline default), so the build never depends on it.
const maskMods = import.meta.glob("../../assets/land-mask.png", {
  eager: true,
  query: "?url",
  import: "default",
}) as Record<string, string>;
const MASK_URL: string | undefined = Object.values(maskMods)[0];

type Kind = "gossip" | "echo";
type Pulse = { slot: number; src: number; dst: number; life: number; kind: Kind; echoed: boolean; iconed: boolean };

export function Mayajaal({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const pitchGrp = useRef<THREE.Group>(null);
  const spinGrp = useRef<THREE.Group>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const { progress } = useScroll();
  const raycaster = useThree((s) => s.raycaster);

  // land source: procedural until (and unless) a committed mask loads in.
  const samplerRef = useRef<LandSampler>(proceduralIsLand);
  const [rev, setRev] = useState(0);

  // ~2,000 land systems (sphere + scatter positions, base color, unit dirs) plus
  // the stylized-Earth surface texture — all from the one shared land sampler.
  const built = useMemo(() => {
    const isLand = samplerRef.current;
    const rng = mulberry32(42);
    const dir = new THREE.Vector3();
    const dirs: THREE.Vector3[] = [];
    const spherePos: number[] = [];
    const scatterPos: number[] = [];
    for (let i = 0; i < CANDIDATES && dirs.length < COUNT; i++) {
      fibonacciSphereDir(i, CANDIDATES, dir);
      if (!isLand(dir)) continue;
      dirs.push(dir.clone());
      spherePos.push(dir.x * R * 1.008, dir.y * R * 1.008, dir.z * R * 1.008);
      const rr = R * (1.7 + rng() * 1.8);
      scatterPos.push(
        dir.x * rr + (rng() - 0.5) * 1.3,
        dir.y * rr + (rng() - 0.5) * 1.3,
        dir.z * rr + (rng() - 0.5) * 1.3,
      );
    }
    const n = dirs.length;
    const base = new THREE.Color(C.ink).lerp(new THREE.Color(C.risoBlue), 0.55);
    const colors = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      colors[i * 3] = base.r;
      colors[i * 3 + 1] = base.g;
      colors[i * 3 + 2] = base.b;
    }
    const canvas = buildLandCanvas(isLand, TEXW, TEXH, OCEAN, LAND);
    const tex = new THREE.CanvasTexture(canvas);
    tex.flipY = false;
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.wrapS = THREE.RepeatWrapping;
    const sphereGeo = new THREE.SphereGeometry(R, 120, 80);
    assignEquirectUV(sphereGeo);
    return { n, dirs, sphere: new Float32Array(spherePos), scatter: new Float32Array(scatterPos), colors, base, tex, sphereGeo };
  }, [rev]);

  // one <points> draw call — starts scattered, lerps onto the globe on scroll.
  const dotTex = useMemo(() => makeDotTexture(), []);
  const geo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(built.scatter.slice(), 3));
    g.setAttribute("color", new THREE.BufferAttribute(built.colors.slice(), 3));
    g.computeBoundingSphere();
    return g;
  }, [built]);

  const pointsMat = useMemo(
    () =>
      new THREE.PointsMaterial({
        size: DOT_SIZE,
        map: dotTex,
        alphaTest: 0.02,
        transparent: true,
        depthWrite: false,
        vertexColors: true,
        sizeAttenuation: true,
        opacity: 0,
      }),
    [dotTex],
  );
  // the planet body — one sphere, stylized-Earth texture; occludes back systems.
  const globeMat = useMemo(
    () => new THREE.MeshStandardMaterial({ map: built.tex, roughness: 0.98, metalness: 0, transparent: true, opacity: 0 }),
    [built],
  );
  // soft atmosphere rim (back-side shell) — sells "globe" without a second ball.
  const rimMat = useMemo(
    () => new THREE.MeshBasicMaterial({ color: C.risoBlue, transparent: true, opacity: 0, side: THREE.BackSide, depthWrite: false }),
    [],
  );
  // expanding ring at the broadcasting system — the "making a transaction" icon.
  const ringMat = useMemo(
    () => new THREE.MeshBasicMaterial({ color: C.coral, transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false }),
    [],
  );

  // pooled arcs — coral for the gossip flood, teal for the echo hops.
  const arcs = useMemo(
    () =>
      Array.from({ length: K }, () => {
        const positions = new Float32Array((ARC_SEG + 1) * 3);
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
        geometry.setDrawRange(0, 0);
        const material = new THREE.LineBasicMaterial({ color: new THREE.Color(C.coral), transparent: true, opacity: 0, depthWrite: false });
        const line = new THREE.Line(geometry, material);
        line.frustumCulled = false;
        line.renderOrder = 2;
        return { positions, geometry, material, line };
      }),
    [],
  );

  // cute computer icons that pop up at systems taking part in a transaction:
  // coral = the one broadcasting, butter = a receiver, teal = an echoing peer.
  const iconTex = useMemo(() => makeSystemIcon(), []);
  const icons = useMemo(
    () =>
      Array.from({ length: 18 }, () => {
        const material = new THREE.SpriteMaterial({ map: iconTex, transparent: true, opacity: 0, depthWrite: false });
        const sprite = new THREE.Sprite(material);
        sprite.visible = false;
        sprite.renderOrder = 4;
        sprite.scale.set(0.001, 0.001, 1);
        return { sprite, material, life: 0, active: false };
      }),
    [iconTex],
  );

  // gossip + heat state (refs — never trigger renders from useFrame).
  // heatSrc → coral (broadcaster), heatRcv → butter (receivers + echoers).
  const heatSrc = useMemo(() => new Float32Array(built.n), [built]);
  const heatRcv = useMemo(() => new Float32Array(built.n), [built]);
  const heatPrev = useMemo(() => new Float32Array(built.n), [built]);
  const colCoral = useMemo(() => new THREE.Color(C.coral), []);
  const colButter = useMemo(() => new THREE.Color(C.butter), []);
  const pulses = useRef<Pulse[]>([]);
  const freeSlots = useRef<number[]>([]);
  const floodTimer = useRef(0.6);
  const assembled = useRef(false);
  const staticDone = useRef(false);
  const activeRef = useRef(false);
  const hoverAt = useRef(0);

  // rotation: auto-spin + drag inertia + idle parallax (all composited in-frame).
  const dragging = useRef(false);
  const spinYaw = useRef(0);
  const spinVel = useRef(0);
  const pitch = useRef(0.15);
  const pitchVel = useRef(0);
  const parYaw = useRef(0);
  const parPitch = useRef(0);
  const lastX = useRef(0);
  const lastY = useRef(0);
  const lastT = useRef(0);

  // transmit ring state (positioned/oriented to the active source each flood).
  const srcDir = useRef(new THREE.Vector3(1, 0, 0));
  const srcLife = useRef(2);
  const _q = useMemo(() => new THREE.Quaternion(), []);
  const _zAxis = useMemo(() => new THREE.Vector3(0, 0, 1), []);

  // upgrade to real continents if a mask is committed (offline default: skip).
  useEffect(() => {
    if (!MASK_URL) return;
    let cancelled = false;
    loadLandMaskSampler(MASK_URL).then((s) => {
      if (!cancelled && s) {
        samplerRef.current = s;
        setRev((r) => r + 1);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // reset the simulation whenever the node set is (re)built.
  useEffect(() => {
    heatSrc.fill(0);
    heatRcv.fill(0);
    heatPrev.fill(0);
    pulses.current = [];
    freeSlots.current = arcs.map((_, i) => i);
    arcs.forEach((ar) => {
      ar.material.opacity = 0;
      ar.geometry.setDrawRange(0, 0);
    });
    icons.forEach((ic) => {
      ic.active = false;
      ic.sprite.visible = false;
      ic.material.opacity = 0;
    });
    floodTimer.current = 0.6;
    assembled.current = false;
    staticDone.current = false;
    srcLife.current = 2;
  }, [built, arcs, icons, heatSrc, heatRcv, heatPrev]);

  // small point-pick threshold so hover targets a single node (§10 fallback).
  useEffect(() => {
    const params = raycaster.params.Points;
    const prev = params?.threshold ?? 1;
    if (params) params.threshold = 0.05;
    return () => {
      if (params) params.threshold = prev;
    };
  }, [raycaster]);

  // stable resources — dispose only on unmount.
  useEffect(
    () => () => {
      dotTex.dispose();
      pointsMat.dispose();
      rimMat.dispose();
      ringMat.dispose();
      iconTex.dispose();
      icons.forEach((ic) => ic.material.dispose());
      arcs.forEach((ar) => {
        ar.geometry.dispose();
        ar.material.dispose();
      });
    },
    [dotTex, pointsMat, rimMat, ringMat, iconTex, icons, arcs],
  );
  // per-build resources — dispose on rebuild (mask upgrade) and on unmount.
  useEffect(
    () => () => {
      geo.dispose();
      globeMat.dispose();
      built.tex.dispose();
      built.sphereGeo.dispose();
    },
    [geo, globeMat, built],
  );

  // pop a computer icon up at a system (coral = sender, butter = receiver,
  // teal = echoer). Reuses the oldest icon if the small pool is exhausted.
  function spawnIcon(dir: THREE.Vector3, color: string) {
    let slot = -1;
    let oldest = -1;
    let oldestLife = -1;
    for (let i = 0; i < icons.length; i++) {
      if (!icons[i].active) {
        slot = i;
        break;
      }
      if (icons[i].life > oldestLife) {
        oldestLife = icons[i].life;
        oldest = i;
      }
    }
    if (slot === -1) slot = oldest;
    if (slot === -1) return;
    const ic = icons[slot];
    ic.active = true;
    ic.life = 0;
    ic.material.color.set(color);
    ic.material.opacity = 0;
    ic.sprite.visible = true;
    ic.sprite.position.copy(dir).multiplyScalar(R * 1.04);
  }

  // fire one arc src→dst into the pool (coral gossip, teal echo).
  function fireArc(src: number, dst: number, kind: Kind, presetLife: number) {
    const slot = freeSlots.current.pop();
    if (slot === undefined) return;
    const ar = arcs[slot];
    ar.material.color.set(kind === "echo" ? C.teal : C.coral);
    greatCircleArc(built.dirs[src], built.dirs[dst], ARC_SEG, R, kind === "echo" ? LIFT_ECHO : LIFT_GOSSIP, ar.positions);
    ar.geometry.attributes.position.needsUpdate = true;
    ar.geometry.computeBoundingSphere();
    pulses.current.push({ slot, src, dst, life: presetLife, kind, echoed: false, iconed: false });
  }

  // one system broadcasts a transaction to `count` random peers + lights the ring.
  function fireFloodFrom(src: number, count: number, presetLife: number) {
    const n = built.n;
    if (n < 2) return;
    heatSrc[src] = 1;
    srcDir.current.copy(built.dirs[src]);
    srcLife.current = 0;
    spawnIcon(built.dirs[src], C.coral); // the system making the transaction
    for (let k = 0; k < count; k++) {
      let dst = (Math.random() * n) | 0;
      if (dst === src) dst = (dst + 1) % n;
      fireArc(src, dst, "gossip", presetLife);
      if (freeSlots.current.length === 0) break; // pool exhausted → cap pulses
    }
  }

  useFrame((state, delta) => {
    const g = group.current;
    if (!g) return;
    const p = progress.current ?? 0;
    const { t, vis } = local(p, SLICE);
    g.visible = vis > 0.01;
    if (!g.visible) return;
    const dt = Math.min(delta, 0.05); // clamp so a tab-return doesn't jump
    const active = vis > 0.2;
    activeRef.current = active;

    // assemble: scatter → globe (deterministic from scroll `t`).
    const a = reduced ? 1 : THREE.MathUtils.smoothstep(t, 0, 0.5);
    const pos = geo.attributes.position.array as Float32Array;
    if (reduced || a >= 1) {
      if (!assembled.current) {
        pos.set(built.sphere);
        geo.attributes.position.needsUpdate = true;
        assembled.current = true;
      }
    } else {
      const s = built.scatter, sp = built.sphere;
      for (let i = 0; i < pos.length; i++) pos[i] = s[i] + (sp[i] - s[i]) * a;
      geo.attributes.position.needsUpdate = true;
      assembled.current = false;
    }

    // rotation: tilt (static, in JSX) + auto-spin + drag fling + idle parallax.
    if (reduced) {
      spinYaw.current = 0.6;
      pitch.current = 0.15;
      parYaw.current = 0;
      parPitch.current = 0;
    } else if (!dragging.current) {
      // integrate angular velocity by real time, decay it with an exponential —
      // identical glide at any frame rate, and a longer, smoother coast.
      spinYaw.current += (AUTO_SPIN + spinVel.current) * dt;
      pitch.current = THREE.MathUtils.clamp(pitch.current + pitchVel.current * dt, -PITCH_MAX, PITCH_MAX);
      const decay = Math.exp(-SPIN_FRICTION * dt);
      spinVel.current *= decay;
      pitchVel.current *= decay;
      const tx = active ? state.pointer.x * 0.12 : 0;
      const ty = active ? state.pointer.y * 0.1 : 0;
      parYaw.current = THREE.MathUtils.damp(parYaw.current, tx, 4, dt);
      parPitch.current = THREE.MathUtils.damp(parPitch.current, ty, 4, dt);
    }
    if (spinGrp.current) spinGrp.current.rotation.y = spinYaw.current + parYaw.current;
    if (pitchGrp.current) pitchGrp.current.rotation.x = pitch.current + parPitch.current;

    // gossip scheduler: one source → ~14 peers, on a light cadence.
    if (reduced) {
      if (!staticDone.current) {
        fireFloodFrom((built.n * 0.4) | 0, FLOOD, 0.66);
        staticDone.current = true;
      }
    } else {
      floodTimer.current -= dt;
      if (floodTimer.current <= 0) {
        fireFloodFrom((Math.random() * built.n) | 0, FLOOD, 0);
        floodTimer.current = FLOOD_EVERY * (0.8 + Math.random() * 0.5);
      }
    }

    // advance pulses: grow the arc, ride an opacity envelope, heat endpoints, and
    // let a few receivers echo the transaction onward (the "93% echo").
    for (let i = pulses.current.length - 1; i >= 0; i--) {
      const pu = pulses.current[i];
      if (!reduced) pu.life += dt / PULSE;
      const l = pu.life;
      const ar = arcs[pu.slot];
      const grow = THREE.MathUtils.clamp(l / 0.65, 0, 1);
      ar.geometry.setDrawRange(0, Math.max(2, Math.ceil(grow * (ARC_SEG + 1))));
      const dim = pu.kind === "echo" ? 0.5 : 1;
      const env = Math.min(1, l / 0.15) * (1 - THREE.MathUtils.smoothstep(l, 0.7, 1));
      ar.material.opacity = env * vis * dim;
      if (pu.kind === "gossip") heatSrc[pu.src] = Math.max(heatSrc[pu.src], 1);
      else heatRcv[pu.src] = Math.max(heatRcv[pu.src], 0.7);
      if (l > 0.6) {
        heatRcv[pu.dst] = Math.max(heatRcv[pu.dst], pu.kind === "echo" ? 0.6 : 0.9);
        if (!pu.iconed) {
          pu.iconed = true; // one icon decision per pulse, at arrival
          if (pu.kind === "echo") {
            if (Math.random() < 0.5) spawnIcon(built.dirs[pu.dst], C.teal); // a peer echoing it on
          } else if (Math.random() < 0.3) {
            spawnIcon(built.dirs[pu.dst], C.butter); // a system receiving the transaction
          }
        }
        if (pu.kind === "gossip" && !pu.echoed && !reduced && Math.random() < 0.4 && freeSlots.current.length > 2) {
          pu.echoed = true;
          let e = (Math.random() * built.n) | 0;
          if (e === pu.dst) e = (e + 1) % built.n;
          fireArc(pu.dst, e, "echo", 0);
        }
      }
      if (l >= 1 && !reduced) {
        ar.material.opacity = 0;
        ar.geometry.setDrawRange(0, 0);
        freeSlots.current.push(pu.slot);
        pulses.current.splice(i, 1);
      }
    }

    // heat → color: dark base flares coral (source) or butter (receiver/echo).
    const decay = reduced ? 1 : Math.exp(-dt * 3.0);
    const col = geo.attributes.color.array as Float32Array;
    const b = built.base;
    let dirty = false;
    for (let i = 0; i < built.n; i++) {
      const hs = heatSrc[i], hr = heatRcv[i];
      if (!reduced) {
        heatSrc[i] = hs * decay;
        heatRcv[i] = hr * decay;
      }
      const tot = hs + hr;
      if (tot > 0.002 || heatPrev[i] > 0.002) {
        col[i * 3] = b.r + (colCoral.r - b.r) * hs + (colButter.r - b.r) * hr * (1 - hs);
        col[i * 3 + 1] = b.g + (colCoral.g - b.g) * hs + (colButter.g - b.g) * hr * (1 - hs);
        col[i * 3 + 2] = b.b + (colCoral.b - b.b) * hs + (colButter.b - b.b) * hr * (1 - hs);
        heatPrev[i] = tot;
        dirty = true;
      }
    }
    if (dirty) geo.attributes.color.needsUpdate = true;

    // transmit ring at the active source — expands + fades once per flood.
    if (!reduced) srcLife.current += dt;
    const rl = srcLife.current;
    const ring = ringRef.current;
    if (ring) {
      if (rl < 1.1) {
        ring.visible = true;
        ring.position.copy(srcDir.current).multiplyScalar(R * 1.02);
        _q.setFromUnitVectors(_zAxis, srcDir.current);
        ring.quaternion.copy(_q);
        const sc = 1 + rl * 2.6;
        ring.scale.set(sc, sc, sc);
        ringMat.opacity = Math.max(0, 1 - rl / 1.1) * vis;
      } else {
        ring.visible = false;
      }
    }

    // transaction icons — pop in, hold, fade over ICON_LIFE (frozen + held when
    // reduced), scaled in world units and occluded behind the globe by depth.
    for (let i = 0; i < icons.length; i++) {
      const ic = icons[i];
      if (!ic.active) continue;
      if (reduced) {
        ic.sprite.scale.set(ICON, ICON, 1);
        ic.material.opacity = vis;
        continue;
      }
      ic.life += dt;
      const l = ic.life / ICON_LIFE;
      if (l >= 1) {
        ic.active = false;
        ic.sprite.visible = false;
        ic.material.opacity = 0;
        continue;
      }
      const pop = THREE.MathUtils.smoothstep(ic.life, 0, 0.18);
      const fade = 1 - THREE.MathUtils.smoothstep(l, 0.72, 1);
      const sc = ICON * (0.55 + 0.45 * pop);
      ic.sprite.scale.set(sc, sc, 1);
      ic.material.opacity = pop * fade * vis;
    }

    // everything rides `vis` (§5).
    pointsMat.opacity = vis;
    globeMat.opacity = vis;
    rimMat.opacity = vis * 0.14;
  });

  // hover-highlight: flare the system under the pointer + a small local flood.
  // pointermove only, and never while dragging → scroll + rotate stay separate.
  function onMove(e: ThreeEvent<PointerEvent>) {
    if (!activeRef.current || reduced || dragging.current) return;
    const i = e.index;
    if (i == null || i >= built.n) return;
    heatSrc[i] = 1;
    const now = performance.now() / 1000;
    if (now - hoverAt.current > 0.3) {
      hoverAt.current = now;
      fireFloodFrom(i, 7, 0);
    }
  }

  // hold-and-rotate: mouse drag spins/pitches the globe with fling inertia.
  // Mouse only (touch keeps scrolling), window listeners (no pointer-capture),
  // and no preventDefault → the golden rule holds; scroll is never captured.
  function onDown(e: ThreeEvent<PointerEvent>) {
    if (reduced || dragging.current) return;
    const ne = e.nativeEvent;
    if (ne.pointerType && ne.pointerType !== "mouse") return; // let touch scroll
    dragging.current = true;
    spinVel.current = 0;
    pitchVel.current = 0;
    lastX.current = ne.clientX;
    lastY.current = ne.clientY;
    lastT.current = performance.now();
    const move = (mv: PointerEvent) => {
      if (!dragging.current) return;
      const now = performance.now();
      const mdt = Math.max((now - lastT.current) / 1000, 1 / 120); // guard div-by-tiny
      const dx = mv.clientX - lastX.current;
      const dy = mv.clientY - lastY.current;
      lastX.current = mv.clientX;
      lastY.current = mv.clientY;
      lastT.current = now;
      spinYaw.current += dx * DRAG_SENS;
      pitch.current = THREE.MathUtils.clamp(pitch.current - dy * DRAG_SENS, -PITCH_MAX, PITCH_MAX);
      // carry the flick as an angular velocity (rad/s), so release keeps gliding.
      spinVel.current = THREE.MathUtils.clamp((dx * DRAG_SENS) / mdt, -FLING_MAX, FLING_MAX);
      pitchVel.current = THREE.MathUtils.clamp((-dy * DRAG_SENS) / mdt, -FLING_MAX, FLING_MAX);
    };
    const up = () => {
      dragging.current = false;
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  return (
    <group ref={group} visible={false}>
      {/* ~23° axial tilt → pitch group → auto-spin group → the globe itself */}
      <group rotation={[0, 0, TILT]}>
        <group ref={pitchGrp}>
          <group ref={spinGrp}>
            {/* the globe body — one sphere, stylized-Earth continents */}
            <mesh geometry={built.sphereGeo} material={globeMat} renderOrder={0} onPointerDown={onDown} />
            {/* soft atmosphere rim */}
            <mesh material={rimMat} renderOrder={3} scale={1.06}>
              <sphereGeometry args={[R, 48, 48]} />
            </mesh>
            {/* ~2,000 peer systems on land */}
            <points key={rev} geometry={geo} material={pointsMat} renderOrder={1} onPointerMove={onMove} onPointerDown={onDown} />
            {/* transmit ring at the broadcasting system */}
            <mesh ref={ringRef} material={ringMat} renderOrder={2} visible={false}>
              <ringGeometry args={[RING_IN, RING_OUT, 40]} />
            </mesh>
            {/* pooled gossip (coral) + echo (teal) arcs */}
            {arcs.map((ar, i) => (
              <primitive key={i} object={ar.line} />
            ))}
            {/* cute computer icons over systems in a transaction */}
            {icons.map((ic, i) => (
              <primitive key={`ic${i}`} object={ic.sprite} />
            ))}
          </group>
        </group>
      </group>
    </group>
  );
}







