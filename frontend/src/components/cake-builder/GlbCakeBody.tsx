"use client";

import { useEffect, useMemo, type ReactNode } from "react";
import { ThreeEvent } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import type { CakeDesign } from "@/types";
import { getCakeBodyModel } from "@/lib/cake-body-models";
import type { CakeZone } from "./CakeSVG";
import { measureDecorationTier, type CakeDecorationTier } from "./cake-decoration-surface";

interface GlbCakeBodyProps {
  design: CakeDesign;
  activeZone: CakeZone | null;
  hoveredZone: CakeZone | null;
  onZoneClick: (zone: CakeZone) => void;
  onZoneHover: (zone: CakeZone | null) => void;
  renderDecorations?: (tiers: CakeDecorationTier[]) => ReactNode;
}

const ZONE_STYLE: Record<CakeZone, { roughness: number; clearcoat: number; clearcoatRoughness: number }> = {
  body: { roughness: 0.48, clearcoat: 0.24, clearcoatRoughness: 0.28 },
  top: { roughness: 0.4, clearcoat: 0.38, clearcoatRoughness: 0.22 },
  border: { roughness: 0.45, clearcoat: 0.3, clearcoatRoughness: 0.24 },
};

function zoneOf(name: string): CakeZone | null {
  if (name.startsWith("Body")) return "body";
  if (name.startsWith("Top")) return "top";
  if (name.startsWith("Border")) return "border";
  return null;
}

function zoneColor(design: CakeDesign, zone: CakeZone): string {
  const bodyColor = design.zones?.body?.color || design.cream_color || "#F2F1EE";
  if (zone === "body") return bodyColor;
  if (zone === "top") return design.zones?.top?.color || bodyColor;
  return design.zones?.border?.color || "#F2F1EE";
}

/**
 * Browser-safe selected GLB base. It clones Drei's cache before assigning
 * materials, so changing a customer's colors never mutates the next visitor's
 * cached asset. The procedural CakeMesh remains an ErrorBoundary fallback.
 */
export default function GlbCakeBody({
  design,
  activeZone,
  hoveredZone,
  onZoneClick,
  onZoneHover,
  renderDecorations,
}: GlbCakeBodyProps) {
  const definition = getCakeBodyModel(design.model_slug);
  const { scene } = useGLTF(definition.glbUrl, false, false);

  const model = useMemo(() => {
    const clone = scene.clone(true);
    // Generator coordinates start at y=0. Shift every body so its plate rests
    // on the same visual ground as the proven procedural fallback.
    const sourceBounds = new THREE.Box3().setFromObject(clone);
    clone.position.y -= sourceBounds.min.y;
    const sourceSize = sourceBounds.getSize(new THREE.Vector3());
    const desiredWidth = design.size === "16cm" ? 1.55 : design.size === "24cm" ? 2.35 : design.size === "2-tier" ? 2.05 : 1.92;
    const scale = desiredWidth / Math.max(sourceSize.x, sourceSize.z, 0.01);
    clone.scale.setScalar(scale);
    const materials: THREE.Material[] = [];
    clone.traverse((object) => {
      if (!(object instanceof THREE.Mesh)) return;
      object.castShadow = true;
      object.receiveShadow = true;
      const zone = zoneOf(object.name);
      if (!zone) return;
      // Replace the baked border only when a matching custom border is drawn.
      if (zone === "border" && renderDecorations && design.zones?.border?.decoration) {
        object.visible = false;
      }

      const style = ZONE_STYLE[zone];
      const highlighted = activeZone === zone || hoveredZone === zone;
      const material = new THREE.MeshPhysicalMaterial({
        color: zoneColor(design, zone),
        // Lathed warehouse icing has inward winding. It is a thin surface,
        // so render/raycast both sides instead of missing the top entirely.
        side: zone === "top" ? THREE.DoubleSide : THREE.FrontSide,
        metalness: 0,
        roughness: style.roughness,
        clearcoat: style.clearcoat,
        clearcoatRoughness: style.clearcoatRoughness,
        envMapIntensity: 0.65,
        emissive: activeZone === zone ? "#6B6B6A" : hoveredZone === zone ? "#8F8F8E" : "#000000",
        emissiveIntensity: activeZone === zone ? 0.14 : highlighted ? 0.08 : 0,
      });
      object.material = material;
      materials.push(material);
    });
    clone.updateMatrixWorld(true);
    const tiers: CakeDecorationTier[] = [];
    clone.traverse((object) => {
      if (!(object instanceof THREE.Mesh) || !object.name.startsWith("Body")) return;
      const suffix = object.name.slice(4);
      const top = clone.getObjectByName(`Top${suffix}`);
      if (!(top instanceof THREE.Mesh)) return;
      const bodyBounds = new THREE.Box3().setFromObject(object);
      const gap = new THREE.Box3().setFromObject(top).min.y - bodyBounds.max.y;
      // Some extruded warehouse tops start above the body. Close that gap on
      // the instance only; leave the cached/downloaded asset untouched.
      if (gap > 0) {
        top.position.y -= (gap + 0.002) / scale;
        top.updateMatrixWorld(true);
      }
      tiers.push(measureDecorationTier(object, top));
    });
    tiers.sort((a, b) => a.surfaceY - b.surfaceY);
    return { clone, materials, tiers };
  }, [activeZone, design, hoveredZone, scene, renderDecorations]);

  useEffect(() => () => model.materials.forEach((material) => material.dispose()), [model]);

  const handlePointerDown = (event: ThreeEvent<PointerEvent>) => {
    const zone = zoneOf(event.object.name);
    if (!zone) return;
    event.stopPropagation();
    onZoneClick(zone);
  };

  const handlePointerEnter = (event: ThreeEvent<PointerEvent>) => {
    const zone = zoneOf(event.object.name);
    if (!zone) return;
    event.stopPropagation();
    onZoneHover(zone);
  };

  const handlePointerLeave = (event: ThreeEvent<PointerEvent>) => {
    if (!zoneOf(event.object.name)) return;
    event.stopPropagation();
    onZoneHover(null);
  };

  return (
    <group>
      <primitive
        object={model.clone}
        onPointerDown={handlePointerDown}
        onPointerEnter={handlePointerEnter}
        onPointerLeave={handlePointerLeave}
      />
      {renderDecorations?.(model.tiers)}
    </group>
  );
}
