import { Suspense, type ReactNode } from "react";
import { Canvas } from "@react-three/fiber";
import { AdaptiveDpr, AdaptiveEvents } from "@react-three/drei";
import styles from "./Stage.module.css";

/**
 * The fixed-viewport stage (§5.2): ONE full-screen fixed <Canvas> that never
 * scrolls, plus a tall spacer that provides scroll distance. Every 3D scene
 * lives inside `scene` and reads the shared scrollProgress ref via useFrame.
 *
 * `overlay` holds DOM text pinned to the viewport (headline, diya line) — all
 * copy stays in the DOM so it's screen-reader reachable (§5.5), never trapped
 * in the canvas.
 *
 * `fallback` is the no-WebGL 2D path (§5.5).
 */
export function Stage({
  scene,
  overlay,
  fallback,
}: {
  scene: ReactNode;
  overlay?: ReactNode;
  fallback?: ReactNode;
}) {
  return (
    <>
      <div className={styles.stage}>
        <Canvas
          dpr={[1, 2]}
          gl={{ alpha: true, antialias: true }}
          camera={{ position: [0, 0, 5], fov: 45 }}
          fallback={fallback ?? <div>{/* 2D fallback lands here */}</div>}
        >
          <Suspense fallback={null}>{scene}</Suspense>
          <AdaptiveDpr pixelated />
          <AdaptiveEvents />
        </Canvas>
      </div>
      <div className={styles.spacer} aria-hidden="true" />
      <div className={styles.grain} aria-hidden="true" />
      {overlay ? <div className={styles.overlay}>{overlay}</div> : null}
    </>
  );
}
