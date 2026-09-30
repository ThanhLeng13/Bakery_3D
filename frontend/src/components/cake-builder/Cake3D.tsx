"use client";

/**
 * Interactive procedural cake with soft buttercream surfaces and local GLB toppings.
 * Pointer distance checks distinguish selection from OrbitControls dragging.
 * Studio illumination is generated locally; no remote HDR or decoder is required.
 */

import { Component, useEffect, useRef, useMemo, Suspense } from "react";
import { Canvas, useFrame, ThreeEvent } from "@react-three/fiber";
import { ContactShadows, Environment, Lightformer, OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import type { CakeDesign } from "@/types";
import { type CakeZone } from "./CakeSVG";
import { Ganache, PipedBorder, RoundedCylinder, useIcingTexture } from "./CakeFinish";
import GlbCakeBody from "./GlbCakeBody";

interface Cake3DProps {
  design: CakeDesign;
  activeZone: CakeZone | null;
  hoveredZone: CakeZone | null;
  onZoneClick: (zone: CakeZone) => void;
  onZoneHover: (zone: CakeZone | null) => void;
  autoRotate?: boolean;
  enableControls?: boolean;
}

// ─── Click detection based on time duration + pointer distance ────────────────
// A click must satisfy BOTH: elapsed < 250ms AND pointer moved < 5px.
// This prevents fast swipes/drags from triggering accidental clicks.
function useMeshClick(onConfirm: () => void) {
  const downTime = useRef<number>(0);
  const downPos = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  const onPointerDown = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    downTime.current = Date.now();
    downPos.current = { x: e.clientX, y: e.clientY };
  };

  const onPointerUp = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    const elapsed = Date.now() - downTime.current;
    const dx = e.clientX - downPos.current.x;
    const dy = e.clientY - downPos.current.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    // True click: short duration AND minimal pointer movement
    if (elapsed < 250 && distance < 5) {
      onConfirm();
    }
  };

  return { onPointerDown, onPointerUp };
}

// ─── Clickable mesh với highlight khi hover / active ─────────────────────────
function ZoneMesh({
  zone, geometry, color, roughness, clearcoat,
  onZoneClick, onZoneHover, activeZone, hoveredZone,
  children,
}: {
  zone: CakeZone;
  geometry: React.ReactNode;
  color: string; roughness: number; clearcoat: number;
  onZoneClick: (z: CakeZone) => void;
  onZoneHover: (z: CakeZone | null) => void;
  activeZone: CakeZone | null;
  hoveredZone: CakeZone | null;
  children?: React.ReactNode;
}) {
  const isActive  = activeZone  === zone;
  const isHovered = hoveredZone === zone;
  const { onPointerDown, onPointerUp } = useMeshClick(() => onZoneClick(zone));
  const icingTexture = useIcingTexture();

  const emissiveColor = isActive ? "#6B6B6A" : isHovered ? "#8F8F8E" : "#000000";
  const emissiveIntensity = isActive ? 0.14 : isHovered ? 0.08 : 0;

  return (
    <mesh
      castShadow
      receiveShadow
      onPointerDown={onPointerDown}
      onPointerUp={onPointerUp}
      onPointerEnter={(e) => { e.stopPropagation(); onZoneHover(zone); }}
      onPointerLeave={(e) => { e.stopPropagation(); onZoneHover(null); }}
    >
      {geometry}
      <meshPhysicalMaterial
        color={color}
        roughness={roughness}
        metalness={0}
        clearcoat={clearcoat}
        clearcoatRoughness={0.28}
        bumpMap={icingTexture}
        bumpScale={0.003}
        envMapIntensity={0.65}
        emissive={emissiveColor}
        emissiveIntensity={emissiveIntensity}
      />
      {children}
    </mesh>
  );
}
// ─── Note on geometries ──────────────────────────────────────────────────────
// We use inline JSX geometry tags (e.g. <sphereGeometry args={[...]} />) inside
// each sub-component instead of module-level THREE.js instances. This ensures:
// (a) geometries are bound to the active WebGL context of the current <Canvas>,
//     so remounting the Canvas (page navigation) never causes blank/broken renders;
// (b) R3F automatically disposes GPU buffers when the component unmounts,
//     preventing memory leaks.

function Flower({ p }: { p: [number, number, number] }) {
  // Đáy của nhụy hoa (bán kính 0.08) nằm khớp trên mặt bánh tại y = surfaceY
  return (
    <group position={p}>
      <mesh position={[0, 0.105, 0]}>
        <sphereGeometry args={[0.105, 12, 12]} />
        <meshStandardMaterial color="#FFD700" emissive="#FFB800" emissiveIntensity={0.5} roughness={0.2} />
      </mesh>
      {[0,1,2,3,4,5].map(i => {
        const a = (i / 6) * Math.PI * 2;
        return (
          <mesh key={i} position={[Math.cos(a) * 0.18, 0.12, Math.sin(a) * 0.18]}>
            <sphereGeometry args={[0.085, 10, 10]} />
            <meshStandardMaterial color="#FF9EC4" emissive="#FF6B9D" emissiveIntensity={0.35} roughness={0.3} />
          </mesh>
        );
      })}
    </group>
  );
}

function Fruit({ p }: { p: [number, number, number] }) {
  // Định vị các phần trái cây để phần đáy tiếp xúc trực tiếp với mặt bánh, không chìm xuống dưới
  return (
    <group position={p}>
      {/* Quả dâu đỏ */}
      <mesh position={[-0.1, 0.105, 0]}>
        <sphereGeometry args={[0.105, 12, 12]} />
        <meshStandardMaterial color="#FF2020" emissive="#CC0000" emissiveIntensity={0.35} roughness={0.25} />
      </mesh>
      {/* Mảnh cam vàng */}
      <mesh position={[0.1, 0.09, 0.035]}>
        <sphereGeometry args={[0.09, 12, 12]} />
        <meshStandardMaterial color="#FFD700" emissive="#E6B800" emissiveIntensity={0.3} roughness={0.3} />
      </mesh>
      {/* Quả kiwi xanh */}
      <mesh position={[0, 0.08, -0.1]}>
        <sphereGeometry args={[0.08, 12, 12]} />
        <meshStandardMaterial color="#22CC44" emissive="#009922" emissiveIntensity={0.3} roughness={0.4} />
      </mesh>
    </group>
  );
}

function Sprinkle({ p }: { p: [number, number, number] }) {
  const colors = ["#FF69B4","#87CEEB","#98FB98","#FFD700","#FF6347","#DA70D6"];
  // Xoay dẹt và đặt nằm ngang sát mặt bánh (đáy tiếp xúc trực tiếp tại y = surfaceY)
  return (
    <group position={p}>
      {[0,1,2,3,4,5,6].map(i => {
        const a = (i / 7) * Math.PI * 2;
        const r = 0.075 + (i % 2) * 0.06;
        return (
          <mesh key={i} position={[Math.cos(a)*r, 0.03, Math.sin(a)*r]} rotation={[Math.PI/2, 0, a+0.5]}>
            <cylinderGeometry args={[0.026, 0.026, 0.11, 6]} />
            <meshStandardMaterial color={colors[i%6]} roughness={0.5} />
          </mesh>
        );
      })}
    </group>
  );
}

function Macaron({ p }: { p: [number, number, number] }) {
  // Xếp macarons đứng nằm sát mặt bánh
  return (
    <group position={p}>
      {/* Phần bánh dưới */}
      <mesh position={[0, 0.028, 0]}>
        <cylinderGeometry args={[0.125, 0.118, 0.056, 18]} />
        <meshStandardMaterial color="#FFB6C1" emissive="#FF8FA3" emissiveIntensity={0.3} roughness={0.2} />
      </mesh>
      {/* Phần nhân kem giữa */}
      <mesh position={[0, 0.07, 0]}>
        <cylinderGeometry args={[0.112, 0.112, 0.028, 18]} />
        <meshStandardMaterial color="#FFF0F5" emissive="#FFD0DC" emissiveIntensity={0.2} roughness={0.15} />
      </mesh>
      {/* Phần bánh trên */}
      <mesh position={[0, 0.112, 0]}>
        <cylinderGeometry args={[0.125, 0.118, 0.056, 18]} />
        <meshStandardMaterial color="#FFB6C1" emissive="#FF8FA3" emissiveIntensity={0.3} roughness={0.2} />
      </mesh>
    </group>
  );
}

function ChocoDrip({ p }: { p: [number, number, number] }) {
  // Sốt chocolate chảy nhẹ từ mặt bánh (dollop nổi trên mặt và chảy dài xuống)
  return (
    <group position={p}>
      <mesh position={[0, 0.105, 0]}>
        <sphereGeometry args={[0.11, 12, 12]} />
        <meshStandardMaterial color="#3D1F0E" emissive="#1A0A00" emissiveIntensity={0.4} roughness={0.4} metalness={0.15} />
      </mesh>
      <mesh position={[0, -0.04, 0]}>
        <cylinderGeometry args={[0.04, 0.015, 0.14, 8]} />
        <meshStandardMaterial color="#3D1F0E" emissive="#1A0A00" emissiveIntensity={0.3} roughness={0.5} />
      </mesh>
    </group>
  );
}

function HBDBlocks({ p }: { p: [number, number, number] }) {
  // Khối chữ nổi nằm ngang, nâng lên một chút để tránh z-fighting
  return (
    <group position={p} rotation={[-Math.PI/2, 0, 0]} scale={[1.35, 1.35, 1.35]}>
      {[
        { x:-0.18, y:0, w:0.04, h:0.18, c:"#5C3D2E" }, // H left
        { x:-0.10, y:0, w:0.04, h:0.18, c:"#5C3D2E" }, // H right
        { x:-0.14, y:0, w:0.08, h:0.04, c:"#5C3D2E" }, // H mid
        { x:-0.02, y:0, w:0.04, h:0.18, c:"#E8837A" }, // B left
        { x: 0.04, y:0.05, w:0.06, h:0.04, c:"#E8837A" }, // B top
        { x: 0.04, y:0, w:0.06, h:0.04, c:"#E8837A" }, // B mid
        { x: 0.04, y:-0.05, w:0.06, h:0.04, c:"#E8837A" }, // B bot
        { x: 0.14, y:0, w:0.04, h:0.18, c:"#5C3D2E" }, // D left
        { x: 0.20, y:0.05, w:0.06, h:0.04, c:"#5C3D2E" }, // D top
        { x: 0.20, y:-0.05, w:0.06, h:0.04, c:"#5C3D2E" }, // D bot
      ].map((seg, i) => (
        <mesh key={i} position={[seg.x, seg.y, 0.014]}>
          <boxGeometry args={[seg.w, seg.h, 0.028]} />
          <meshStandardMaterial color={seg.c} emissive={seg.c} emissiveIntensity={0.5} roughness={0.3} />
        </mesh>
      ))}
    </group>
  );
}

type DecorationFile = "flower" | "strawberry" | "macaron";

function DecorationAsset({
  file,
  p,
  rotation,
  sizeScale,
}: {
  file: DecorationFile;
  p: [number, number, number];
  rotation: number;
  sizeScale: number;
}) {
  // These original GLBs use no Draco or Meshopt compression. Avoid initializing
  // the Meshopt WebAssembly decoder, which production CSP intentionally blocks.
  const { scene } = useGLTF(`/models/decorations/${file}.glb?v=20260930`, false, false);
  const instance = useMemo(() => {
    const clone = scene.clone(true);
    clone.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        object.castShadow = true;
        object.receiveShadow = true;
      }
    });
    return clone;
  }, [scene]);
  const scale = file === "strawberry" ? 1.6 : file === "macaron" ? 1.3 : 1.15;
  return <primitive object={instance} position={p} rotation={[0, rotation, 0]} scale={scale * sizeScale} dispose={null} />;
}

class DecorationAssetBoundary extends Component<
  { children: React.ReactNode; fallback: React.ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

function ModelOrFallback({
  file,
  p,
  rotation,
  fallback,
  sizeScale,
}: {
  file: DecorationFile;
  p: [number, number, number];
  rotation: number;
  fallback: React.ReactNode;
  sizeScale: number;
}) {
  return (
    <DecorationAssetBoundary fallback={fallback}>
      <Suspense fallback={fallback}>
        <DecorationAsset file={file} p={p} rotation={rotation} sizeScale={sizeScale} />
      </Suspense>
    </DecorationAssetBoundary>
  );
}

// ─── ToppingGroup cho từng loại topping cụ thể ──────────────────────────────
function ToppingGroup({ type, surfaceY, R, slot = 0, slots = 1 }: { type: string; surfaceY: number; R: number; slot?: number; slots?: number }) {
  const sizeScale = Math.min(1, R / 0.78);
  const positions = useMemo<[number, number, number][]>(() => {
    // Model origins sit at the bottom of each decoration, just above the icing.
    const y = surfaceY + 0.005;

    const pts: [number, number, number][] = [];

    if (type === "text") {
      // Chữ viết chỉ đặt duy nhất ở tâm bánh
      pts.push([0, y, 0]);
    } else {
      const count = type === "sprinkles" ? 8 : slots > 1 ? 2 : 5;
      const radius = R * 0.64;
      for (let i = 0; i < count; i++) {
        const a = ((i * slots + slot) / (count * slots)) * Math.PI * 2 + 0.35;
        pts.push([Math.cos(a) * radius, y, Math.sin(a) * radius]);
      }
    }
    return pts;
  }, [type, surfaceY, R, slot, slots]);

  return (
    <group>
      {positions.map((pos, i) => {
        switch (type) {
          case "flowers":        return <ModelOrFallback key={i} file="flower" p={pos} rotation={i * 0.45} sizeScale={sizeScale} fallback={<Flower p={pos} />} />;
          case "fruits":         return <ModelOrFallback key={i} file="strawberry" p={pos} rotation={i * 0.6} sizeScale={sizeScale} fallback={<Fruit p={pos} />} />;
          case "sprinkles":      return <Sprinkle   key={i} p={pos} />;
          case "macarons":       return <ModelOrFallback key={i} file="macaron" p={pos} rotation={i * 0.45} sizeScale={sizeScale} fallback={<Macaron p={pos} />} />;
          case "chocolate drip": return <ChocoDrip  key={i} p={pos} />;
          case "text":           return <HBDBlocks  key={i} p={[pos[0], pos[1] + 0.005, pos[2]]} />;
          default:               return null;
        }
      })}
    </group>
  );
}

// ─── Toppings mặt trên (chấp nhận mảng toppings) ─────────────────────────────
function TopToppings({ toppings, surfaceY, R }: { toppings?: string[]; surfaceY: number; R: number }) {
  if (!toppings || toppings.length === 0) return null;
  const ringToppings = toppings.filter((type) => ["flowers", "fruits", "macarons"].includes(type));
  return (
    <group>
      {toppings.map((type) => type === "chocolate drip" ? (
        <Ganache key={type} radius={R} surfaceY={surfaceY} />
      ) : (
        <ToppingGroup key={type} type={type} surfaceY={surfaceY} R={R}
          slot={Math.max(0, ringToppings.indexOf(type))} slots={Math.max(1, ringToppings.length)} />
      ))}
    </group>
  );
}

// ─── Viền trang trí ───────────────────────────────────────────────────────────
// useMemo creates ONE geometry and ONE material instance per decoration type.
// Without this, each mesh in the .map() loop (N=22) would instantiate its own
// GPU buffer and material, multiplying VRAM usage and draw-call overhead by N.
// R3F allows sharing geometry/material objects across multiple <mesh> nodes.
function getVisibleToppings(design: CakeDesign): string[] {
  if (Array.isArray(design.zones?.top?.toppings)) {
    return Array.from(new Set(design.zones?.top?.toppings)).filter(Boolean);
  }
  const legacyToppings = Array.isArray(design.topping_type) ? design.topping_type : [];
  return Array.from(new Set(legacyToppings)).filter(Boolean);
}

function BorderDecor({ type, color, R, y }: { type: string; color: string; R: number; y: number }) {
  const N = 22;
  const pts = useMemo(() =>
    Array.from({ length: N }, (_, i) => {
      const a = (i / N) * Math.PI * 2;
      return { x: Math.cos(a) * (R + 0.06), z: Math.sin(a) * (R + 0.06), a };
    }), [R]);

  const pearlGeo   = useMemo(() => new THREE.SphereGeometry(0.052, 12, 12),   []);
  const pearlMat   = useMemo(() => new THREE.MeshPhysicalMaterial({ color: "#FAFAF9", roughness: 0.28, metalness: 0.1, clearcoat: 0.4 }), []);

  const spkGeo     = useMemo(() => new THREE.CylinderGeometry(0.015, 0.015, 0.052, 6), []);
  useEffect(() => () => {
    pearlGeo.dispose();
    pearlMat.dispose();
    spkGeo.dispose();
  }, [pearlGeo, pearlMat, spkGeo]);

  switch (type) {
    case "piping":
      return <PipedBorder radius={R} y={y} color={color} />;
    case "rosettes":
      return <PipedBorder radius={R} y={y} color={color} rosettes />;
    case "pearls":
      return (
        <group>
          {pts.map((p, i) => (
            <mesh key={i} position={[p.x, y, p.z]} geometry={pearlGeo} material={pearlMat} />
          ))}
        </group>
      );
    case "sprinkles": {
      const sc = ["#FF69B4","#87CEEB","#98FB98","#FFD700"];
      // Sprinkles vary per-item color so material must stay inline; geometry is shared.
      return (
        <group>
          {pts.map((p, i) => (
            <mesh key={i} position={[p.x, y+(i%3-1)*0.022, p.z]} rotation={[Math.PI/2, 0, p.a]} geometry={spkGeo}>
              <meshStandardMaterial color={sc[i%4]} roughness={0.55} />
            </mesh>
          ))}
        </group>
      );
    }
    case "ribbon":
      return (
        <mesh position={[0, y, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[R + 0.04, 0.04, 10, 80]} />
          <meshPhysicalMaterial color={color} roughness={0.5} clearcoat={0.1} />
        </mesh>
      );
    default:
      return null;
  }
}

// ─── Hoa văn thân bánh ────────────────────────────────────────────────────────
function BodyPattern({ type, R, H, y }: { type: string; R: number; H: number; y: number }) {
  switch (type) {
    case "stripes":
      return (
        <group>
          {Array.from({ length: 12 }, (_, i) => {
            const a = (i / 12) * Math.PI * 2;
            return (
              <mesh key={i} position={[Math.cos(a)*(R-0.005), y, Math.sin(a)*(R-0.005)]} rotation={[0, -a+Math.PI/2, 0]}>
                <planeGeometry args={[0.02, H*0.9]} />
                <meshStandardMaterial color="#FFFFFF" transparent opacity={0.32} side={THREE.FrontSide} emissive="#FFFFFF" emissiveIntensity={0.15} />
              </mesh>
            );
          })}
        </group>
      );
    case "dots":
      return (
        <group>
          {Array.from({ length: 24 }, (_, i) => {
            const a = (i / 24) * Math.PI * 2;
            const yOff = (i%4 - 1.5) * (H/4);
            return (
              <mesh key={i} position={[Math.cos(a)*R*0.97, y+yOff, Math.sin(a)*R*0.97]}>
                <sphereGeometry args={[0.034, 7, 7]} />
                <meshStandardMaterial color="#FFFFFF" transparent opacity={0.45} emissive="#FFFFFF" emissiveIntensity={0.2} />
              </mesh>
            );
          })}
        </group>
      );
    case "waves":
      return (
        <group>
          {[0.28, 0.0, -0.28].map((off, i) => (
            <mesh key={i} position={[0, y+off, 0]} rotation={[Math.PI / 2, 0, 0]}>
              <torusGeometry args={[R*0.994, 0.018, 8, 80]} />
              <meshStandardMaterial color="#FFFFFF" transparent opacity={0.38} emissive="#FFFFFF" emissiveIntensity={0.12} />
            </mesh>
          ))}
        </group>
      );
    default:
      return null;
  }
}

// ─── Toàn bộ mô hình bánh ─────────────────────────────────────────────────────
function CakeMesh({ design, activeZone, hoveredZone, onZoneClick, onZoneHover }: Cake3DProps) {
  const bodyColor   = design.zones?.body?.color   || design.cream_color || "#F2F1EE";
  const borderColor = design.zones?.border?.color || "#F2F1EE";
  const topColor    = design.zones?.top?.color    || bodyColor;

  const size = design.size;
  const zoneProps = { onZoneClick, onZoneHover, activeZone, hoveredZone };

  const activeToppings = getVisibleToppings(design);

  if (size === "2-tier") {
    // Bottom Tier Dimensions
    const R1 = 0.9;
    const bodyH1 = 0.55;
    const borderH1 = 0.075;
    const topH1 = 0.06;

    const bodyY1 = 0;
    const borderY1 = -(bodyH1 / 2 + borderH1 / 2);
    const topY1 = bodyH1 / 2 + topH1 / 2;
    const topSurface1 = bodyH1 / 2 + topH1;

    // Top Tier Dimensions
    const R2 = 0.60;
    const bodyH2 = 0.45;
    const borderH2 = 0.055;
    const topH2 = 0.06;

    const bodyY2 = topSurface1 + bodyH2 / 2;
    const borderY2 = bodyY2 - (bodyH2 / 2 + borderH2 / 2);
    const topY2 = bodyY2 + bodyH2 / 2 + topH2 / 2;
    const topSurface2 = bodyY2 + bodyH2 / 2 + topH2;

    return (
      <group>
        {/* ─── TẦNG DƯỚI (Bottom Tier) ─── */}
        {/* Thân bánh tầng dưới */}
        <group position={[0, bodyY1, 0]}>
          <ZoneMesh zone="body" color={bodyColor} roughness={0.48} clearcoat={0.24}
            geometry={<RoundedCylinder radius={R1} height={bodyH1} roundTop={false} capTop={false} />} {...zoneProps} />
          <BodyPattern type={design.zones?.body?.decoration || ""} R={R1} H={bodyH1} y={0} />
        </group>

        {/* Viền dưới tầng dưới */}
        <group position={[0, borderY1, 0]}>
          <ZoneMesh zone="border" color={borderColor} roughness={0.45} clearcoat={0.3}
            geometry={<RoundedCylinder radius={R1 + 0.01} height={borderH1} bevel={0.025} />} {...zoneProps} />
          <BorderDecor type={design.zones?.border?.decoration || "piping"} color={borderColor} R={R1 + 0.014} y={0} />
        </group>

        {/* Mặt trên tầng dưới */}
        <group position={[0, topY1, 0]}>
          <ZoneMesh zone="top" color={topColor} roughness={0.4} clearcoat={0.38}
            geometry={<RoundedCylinder radius={R1} height={topH1} bevel={0.028} roundBottom={false} capBottom={false} />} {...zoneProps} />
        </group>


        {/* ─── TẦNG TRÊN (Top Tier) ─── */}
        {/* Thân bánh tầng trên */}
        <group position={[0, bodyY2, 0]}>
          <ZoneMesh zone="body" color={bodyColor} roughness={0.48} clearcoat={0.24}
            geometry={<RoundedCylinder radius={R2} height={bodyH2} roundTop={false} capTop={false} />} {...zoneProps} />
          <BodyPattern type={design.zones?.body?.decoration || ""} R={R2} H={bodyH2} y={0} />
        </group>

        {/* Viền dưới tầng trên */}
        <group position={[0, borderY2, 0]}>
          <ZoneMesh zone="border" color={borderColor} roughness={0.45} clearcoat={0.3}
            geometry={<RoundedCylinder radius={R2 + 0.01} height={borderH2} bevel={0.02} />} {...zoneProps} />
          <BorderDecor type={design.zones?.border?.decoration || "piping"} color={borderColor} R={R2 + 0.014} y={0.055} />
        </group>

        {/* Mặt trên tầng trên */}
        <group position={[0, topY2, 0]}>
          <ZoneMesh zone="top" color={topColor} roughness={0.4} clearcoat={0.38}
            geometry={<RoundedCylinder radius={R2} height={topH2} bevel={0.028} roundBottom={false} capBottom={false} />} {...zoneProps} />
        </group>

        {/* ── Toppings mặt trên cùng ── */}
        <TopToppings toppings={activeToppings} surfaceY={topSurface2} R={R2} />

        {/* ── Đĩa bánh ── */}
        <mesh position={[0, borderY1 - borderH1 / 2 - 0.02, 0]}>
          <RoundedCylinder radius={R1 + 0.23} height={0.035} bevel={0.012} />
          <meshStandardMaterial color="#FAFAF9" roughness={0.55} />
        </mesh>
        <mesh position={[0, borderY1 - borderH1 / 2 - 0.038, 0]}>
          <RoundedCylinder radius={R1 + 0.23} height={0.007} bevel={0.003} />
          <meshStandardMaterial color="#D5D5D2" roughness={0.45} metalness={0.05} />
        </mesh>
      </group>
    );
  }

  // Single Tier Dimensions (16cm, 20cm, 24cm)
  let R = 0.82;
  let bodyH = 0.86;
  let borderH = 0.075;
  let topH = 0.08;

  if (size === "16cm") {
    R = 0.65;
    bodyH = 0.72;
    borderH = 0.065;
    topH = 0.06;
  } else if (size === "24cm") {
    R = 1.0;
    bodyH = 0.96;
    borderH = 0.085;
    topH = 0.10;
  }

  const bodyY      = 0;
  const borderY    = -(bodyH/2 + borderH/2);
  const topY       = bodyH/2 + topH/2;
  const topSurface = bodyH/2 + topH;

  return (
    <group>
      {/* ── Thân bánh (clickable) ── */}
      <group position={[0, bodyY, 0]}>
          <ZoneMesh zone="body" color={bodyColor} roughness={0.48} clearcoat={0.24}
          geometry={<RoundedCylinder radius={R} height={bodyH} roundTop={false} capTop={false} />} {...zoneProps} />
        <BodyPattern type={design.zones?.body?.decoration || ""} R={R} H={bodyH} y={0} />
      </group>

      {/* ── Viền dưới (clickable) ── */}
      <group position={[0, borderY, 0]}>
          <ZoneMesh zone="border" color={borderColor} roughness={0.45} clearcoat={0.3}
          geometry={<RoundedCylinder radius={R + 0.01} height={borderH} bevel={0.025} />} {...zoneProps} />
        <BorderDecor type={design.zones?.border?.decoration || "piping"} color={borderColor} R={R + 0.014} y={0} />
      </group>

      {/* ── Mặt trên (clickable) ── */}
      <group position={[0, topY, 0]}>
          <ZoneMesh zone="top" color={topColor} roughness={0.4} clearcoat={0.38}
          geometry={<RoundedCylinder radius={R} height={topH} bevel={0.035} roundBottom={false} capBottom={false} />} {...zoneProps} />
      </group>

      {/* ── Toppings mặt trên ── */}
      <TopToppings toppings={activeToppings} surfaceY={topSurface} R={R} />

      {/* ── Đĩa bánh ── */}
      <mesh position={[0, borderY - borderH/2 - 0.02, 0]}>
        <RoundedCylinder radius={R + 0.23} height={0.035} bevel={0.012} />
          <meshStandardMaterial color="#FAFAF9" roughness={0.55} />
      </mesh>
      <mesh position={[0, borderY - borderH/2 - 0.038, 0]}>
        <RoundedCylinder radius={R + 0.23} height={0.007} bevel={0.003} />
          <meshStandardMaterial color="#D5D5D2" roughness={0.45} metalness={0.05} />
      </mesh>
    </group>
  );
}

class CakeBodyFallbackBoundary extends Component<{
  children: React.ReactNode;
  fallback: React.ReactNode;
}, { hasError: boolean }> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidUpdate(previousProps: Readonly<{ children: React.ReactNode }>) {
    // A new selected GLB gets a fresh attempt instead of permanently retaining
    // the previous failed model's fallback.
    if (previousProps.children !== this.props.children && this.state.hasError) {
      this.setState({ hasError: false });
    }
  }

  render() {
    return this.state.hasError ? this.props.fallback : this.props.children;
  }
}

function SelectedCakeBody(props: Cake3DProps) {
  return (
    <CakeBodyFallbackBoundary fallback={<CakeMesh {...props} />}>
      <Suspense fallback={<CakeMesh {...props} />}>
        <GlbCakeBody {...props} />
      </Suspense>
    </CakeBodyFallbackBoundary>
  );
}

// ─── Slow auto-rotate bằng ref (không gây re-render) ─────────────────────────
function RotatingCake(props: Cake3DProps) {
  const groupRef  = useRef<THREE.Group>(null!);
  const rotating  = useRef(true);

  useFrame((_, dt) => {
    if (props.autoRotate !== false && rotating.current && groupRef.current) {
      groupRef.current.rotation.y += dt * 0.28;
    }
  });

  return (
    <group ref={groupRef}>
      {/* Expose rotating ref to OrbitControls via a separate child */}
      <OrbitControls
        makeDefault
        enablePan={false}
        enableRotate={props.enableControls !== false}
        enableZoom={props.enableControls !== false}
        minDistance={2.2}
        maxDistance={5.5}
        minPolarAngle={Math.PI * 0.10}
        maxPolarAngle={Math.PI * 0.48}
        dampingFactor={0.1}
        enableDamping
        onStart={() => { rotating.current = false; }}
        onEnd={()   => { rotating.current = true;  }}
      />
      <group scale={props.design.size === "2-tier" || props.design.size === "24cm" ? 0.9 : 1}
        position={[0, props.design.size === "2-tier" ? -0.16 : props.design.size === "24cm" ? 0.09 : 0, 0]}>
        <SelectedCakeBody {...props} />
      </group>
    </group>
  );
}

// ─── Scene lighting ───────────────────────────────────────────────────────────
function Scene(props: Cake3DProps) {
  const shadowY = {
    "16cm": -0.47,
    "20cm": -0.55,
    "24cm": -0.46,
    "2-tier": -0.52,
  }[props.design.size];

  return (
    <>
      <hemisphereLight args={["#FFFFFF", "#E5E5E3", 0.9]} />
      <directionalLight position={[-3, 5, 4]} intensity={2.7} color="#FFFFFF" castShadow
        shadow-mapSize={[1024, 1024]} shadow-bias={-0.0003} shadow-normalBias={0.02}
        shadow-camera-left={-2} shadow-camera-right={2} shadow-camera-top={2} shadow-camera-bottom={-2}
        shadow-camera-near={0.5} shadow-camera-far={12} shadow-radius={4} shadow-blurSamples={8} />
      <directionalLight position={[4, 2, 1]} intensity={0.65} color="#FFFFFF" />
      <directionalLight position={[0, 3, -4]} intensity={0.9} color="#FFFFFF" />
      <Environment resolution={128}>
        <Lightformer form="rect" intensity={2.2} position={[-3, 4, 3]} scale={[4, 7, 1]} color="#FFFFFF" />
        <Lightformer form="rect" intensity={1.1} position={[4, 2, 1]} scale={[3, 6, 1]} color="#F5F5F4" />
      </Environment>
      <RotatingCake {...props} />
      <ContactShadows
        key={props.design.size}
        position={[0, shadowY, 0]}
        opacity={0.24}
        scale={4.2}
        blur={2.8}
        far={1.4}
        resolution={256}
        frames={1}
        color="#2B2B2A"
      />
    </>
  );
}

// ─── Component chính ──────────────────────────────────────────────────────────
export default function Cake3D(props: Cake3DProps) {
  return (
    <div
      data-cake3d="true"
      className="aspect-square max-w-[760px] md:aspect-[16/10] 2xl:aspect-[16/9] 2xl:max-w-[1000px]"
      style={{
        position: "relative",
        width: "100%",
        margin: "0 auto",
        borderRadius: 0,
        overflow: "hidden",
        background: "radial-gradient(ellipse at 50% 38%, #FFFFFF 30%, #F5F5F4 100%)",
        cursor: props.enableControls === false ? "default" : "grab",
      }}
    >
      {/* Canvas */}
      <Canvas
        camera={{ position: [2.2, 2, 3.2], fov: 30 }}
        shadows="variance"
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true }}
        role="img"
        aria-label="Xem trước bánh kem 3D; dùng các nút tùy chỉnh để chọn vùng bánh"
        style={{ width:"100%", height:"100%" }}
      >
        <Suspense fallback={null}>
          <Scene {...props} />
        </Suspense>
      </Canvas>
    </div>
  );
}
