import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { C } from "../../styles/palette";
import { useScroll } from "../../scroll/ScrollContext";
import { STATIONS, local } from "../stations";

/**
 * ST.0 MAYAJAAL ★ — the signature-shader moment (craft-move #3, §7). ~4,000
 * instanced signal points rendered in ONE draw call by a custom GLSL
 * "illusion-net": a caustic, water-like light rippling across the whole field
 * (the maya/illusion made literal). As you scroll the field organises from a
 * scattered cloud toward a faint lattice — order becoming possible.
 *
 * The caustic ripple + scatter→lattice morph run entirely on the GPU (one
 * ShaderMaterial, two position attributes), so it holds 60fps at 4k points.
 * Reduced-motion: time is frozen (static caustic frame), the scroll morph stays.
 *
 * // ponytail: skipped the peer-to-peer "gossip arcs" garnish — the shader is
 * // the awe; add arcs only if the station reads empty on the demo machine.
 */
const COUNT = 4000;
const SLICE = STATIONS[0].slice;

const vert = /* glsl */ `
  uniform float uTime;
  uniform float uProgress;
  uniform float uSize;
  attribute vec3 aTarget;
  attribute vec3 aColor;
  attribute float aSeed;
  varying vec3 vColor;
  varying float vBright;
  void main() {
    vColor = aColor;
    vec3 pos = mix(position, aTarget, uProgress);
    // illusion-net: layered sines = caustic light through water
    float w = sin(pos.x * 1.3 + uTime * 0.9 + aSeed * 6.2831)
            + sin(pos.y * 1.7 - uTime * 0.7)
            + sin((pos.x + pos.y) * 0.9 + uTime * 0.5);
    pos.z += w * 0.06 * (0.4 + 0.6 * (1.0 - uProgress));
    vBright = 0.55 + 0.45 * sin(w * 1.7 + uTime);
    vec4 mv = modelViewMatrix * vec4(pos, 1.0);
    gl_PointSize = uSize * (240.0 / -mv.z) * (0.8 + 0.4 * vBright);
    gl_Position = projectionMatrix * mv;
  }
`;

const frag = /* glsl */ `
  uniform float uOpacity;
  varying vec3 vColor;
  varying float vBright;
  void main() {
    // soft round point — no hard square edges
    float r = length(gl_PointCoord - 0.5);
    float a = smoothstep(0.5, 0.12, r);
    // brightness rides the ALPHA, not the colour — keeps the hue clean instead
    // of clipping to pure white/red. Normal blend (additive washes near-white Paper).
    gl_FragColor = vec4(vColor, a * uOpacity * (0.35 + 0.5 * vBright));
  }
`;

export function Mayajaal({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const { progress } = useScroll();

  const { geometry, material } = useMemo(() => {
    const scatter = new Float32Array(COUNT * 3);
    const target = new Float32Array(COUNT * 3);
    const color = new Float32Array(COUNT * 3);
    const seed = new Float32Array(COUNT);
    const coral = new THREE.Color(C.coral);
    const blue = new THREE.Color(C.risoBlue);
    const butter = new THREE.Color(C.butter);

    // faint jittered lattice on a disc = the "order becoming possible" target
    const cols = Math.ceil(Math.sqrt(COUNT));
    for (let i = 0; i < COUNT; i++) {
      // scattered cloud (chaos)
      const rr = Math.cbrt(Math.random()) * 3.6;
      const th = Math.random() * Math.PI * 2;
      const ph = Math.acos(2 * Math.random() - 1);
      scatter[i * 3] = rr * Math.sin(ph) * Math.cos(th);
      scatter[i * 3 + 1] = rr * Math.sin(ph) * Math.sin(th) * 0.7;
      scatter[i * 3 + 2] = rr * Math.cos(ph) - 1.5;

      // lattice target (ordered but organic)
      const gx = (i % cols) / (cols - 1) - 0.5;
      const gy = Math.floor(i / cols) / (cols - 1) - 0.5;
      const jx = Math.sin(i * 12.9) * 0.012;
      const jy = Math.cos(i * 7.7) * 0.012;
      const tx = gx * 6.2 + jx;
      const ty = gy * 4.2 + jy;
      target[i * 3] = tx;
      target[i * 3 + 1] = ty;
      target[i * 3 + 2] = -1.4 + Math.sin(i) * 0.15;

      // coral (energy) and riso-blue (data) speckled through the field with a
      // little butter — a riso "pop" spread, not one flat red cloud. Per-point
      // random mix + a faint blue bias toward the calm centre.
      const rad = Math.hypot(tx, ty) / 3.5;
      const mix = THREE.MathUtils.clamp(Math.random() * 0.7 + rad * 0.4, 0, 1);
      const c = coral.clone().lerp(blue, mix);
      if (i % 11 === 0) c.lerp(butter, 0.6); // sparse butter highlights
      color[i * 3] = c.r;
      color[i * 3 + 1] = c.g;
      color[i * 3 + 2] = c.b;
      seed[i] = Math.random();
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(scatter, 3));
    geo.setAttribute("aTarget", new THREE.BufferAttribute(target, 3));
    geo.setAttribute("aColor", new THREE.BufferAttribute(color, 3));
    geo.setAttribute("aSeed", new THREE.BufferAttribute(seed, 1));

    const mat = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uProgress: { value: 0 },
        uSize: { value: 0.12 },
        uOpacity: { value: 0 },
      },
      vertexShader: vert,
      fragmentShader: frag,
      transparent: true,
      depthWrite: false,
    });
    return { geometry: geo, material: mat };
  }, []);

  useFrame((_, delta) => {
    const g = group.current;
    if (!g) return;
    const p = progress.current ?? 0;
    const { t, vis } = local(p, SLICE);
    g.visible = vis > 0.01;
    if (!g.visible) return;
    const u = material.uniforms;
    if (!reduced) u.uTime.value += delta;
    u.uProgress.value = THREE.MathUtils.smoothstep(t, 0, 1);
    u.uOpacity.value = vis;
    if (!reduced) g.rotation.z += delta * 0.01;
  });

  return (
    <group ref={group} visible={false}>
      <points geometry={geometry} material={material} />
    </group>
  );
}
