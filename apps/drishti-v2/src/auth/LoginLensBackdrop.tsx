import { Canvas } from "@react-three/fiber";
import { Suspense } from "react";
import { Lens } from "../landing/Hero/Lens";

/**
 * The dimmed hero lens behind the login card (§8) — "stepping through the lens."
 * A fresh, tiny <Canvas> (the landing's canvas has unmounted with the story) that
 * reuses the one hero Lens component, held still (reduced) and cooled toward
 * Riso-Blue by the overlay above it. Offline: no HDRI/env, just the glass.
 */
export function LoginLensBackdrop() {
  return (
    <div aria-hidden="true" style={{ position: "fixed", inset: 0, opacity: 0.5 }}>
      <Canvas
        dpr={[1, 2]}
        gl={{ alpha: true, antialias: true }}
        camera={{ position: [0, 0, 5], fov: 45 }}
        frameloop="always"
      >
        <Suspense fallback={null}>
          {/* soft key so the resolved glass reads without the landing's full rig */}
          <ambientLight intensity={0.6} />
          <directionalLight position={[3, 4, 5]} intensity={1.1} />
          <Lens reduced />
        </Suspense>
      </Canvas>
    </div>
  );
}
