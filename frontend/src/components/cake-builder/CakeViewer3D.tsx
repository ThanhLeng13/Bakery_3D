"use client";

import { Suspense, useEffect, useMemo } from "react";
import CanvasErrorBoundary from "./CanvasErrorBoundary";
import { Canvas } from "@react-three/fiber";
import { ContactShadows, Environment, Lightformer, OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import type { Cake3DModel } from "@/types";

function previewZone(name: string): "body" | "top" | "border" | null {
  if (name.startsWith("Body")) return "body";
  if (name.startsWith("Top")) return "top";
  if (name.startsWith("Border")) return "border";
  return null;
}

function ProductCakeModel({ model }: { model: Cake3DModel }) {
  const { scene } = useGLTF(model.glb_url, false, false);
  const instance = useMemo(() => {
    const clone = scene.clone(true);
    const bounds = new THREE.Box3().setFromObject(clone);
    clone.position.y -= bounds.min.y;
    const size = bounds.getSize(new THREE.Vector3());
    clone.scale.setScalar(1.95 / Math.max(size.x, size.z, 0.01));
    const materials: THREE.Material[] = [];
    clone.traverse((object) => {
      if (!(object instanceof THREE.Mesh)) return;
      object.castShadow = true;
      object.receiveShadow = true;
      const zone = previewZone(object.name);
      if (!zone) return;
      const material = new THREE.MeshPhysicalMaterial({
        color: zone === "body" ? "#F3ECE1" : zone === "top" ? "#FDFBF7" : "#F8F3EA",
        roughness: zone === "body" ? 0.48 : 0.35,
        clearcoat: zone === "top" ? 0.72 : 0.48,
        clearcoatRoughness: 0.22,
        envMapIntensity: 0.7,
      });
      object.material = material;
      materials.push(material);
    });
    return { clone, materials };
  }, [scene]);

  useEffect(() => () => instance.materials.forEach((material) => material.dispose()), [instance]);
  return <primitive object={instance.clone} />;
}

/**
 * A read-only studio preview shown only for an explicitly mapped product model.
 *
 * The fallback boundary sits OUTSIDE <Canvas>, not inside it. `@react-three/fiber`
 * renders its children with a Three.js reconciler, so a DOM <div>/<svg>/<p>
 * returned from an inner boundary is not valid there: the reconciler treats the
 * lowercase tag as an unknown THREE element and throws again, replacing the
 * intended message with a second crash. R3F instead re-throws child errors out
 * of <Canvas> (react-three-fiber 8.18, `if (error) throw error`), which a DOM
 * parent can catch — that also covers a WebGL context that fails to create.
 */
export default function CakeViewer3D({ model }: { model: Cake3DModel }) {
  return (
    <div className="relative overflow-hidden bg-[radial-gradient(ellipse_at_50%_35%,#FFFFFF_20%,#F3EFE9_100%)]" aria-label={`Xem mẫu 3D ${model.name}`}>
      <CanvasErrorBoundary
        message="Không tải được mô hình 3D"
        detail="Ảnh và thông tin bánh vẫn hiển thị bình thường."
      >
        <Canvas camera={{ position: [2.2, 1.75, 3], fov: 32 }} dpr={[1, 1.5]} shadows>
          <ambientLight intensity={0.55} />
          <directionalLight position={[-3, 5, 4]} intensity={2.3} castShadow />
          <directionalLight position={[4, 2, 1]} intensity={0.65} />
          <Environment resolution={64}>
            <Lightformer form="rect" intensity={2} position={[-3, 4, 3]} scale={[4, 7, 1]} color="#FFFFFF" />
          </Environment>
          <Suspense fallback={null}>
            <ProductCakeModel model={model} />
          </Suspense>
          <ContactShadows position={[0, -0.03, 0]} opacity={0.22} scale={3.4} blur={2.5} far={1.2} resolution={128} frames={1} />
          <OrbitControls enablePan={false} minDistance={2.3} maxDistance={4.3} maxPolarAngle={Math.PI / 2.05} />
        </Canvas>
      </CanvasErrorBoundary>
      <span className="pointer-events-none absolute bottom-3 left-3 rounded-full bg-white/80 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-ink backdrop-blur">
        Mẫu 3D · Kéo để xoay
      </span>
    </div>
  );
}
