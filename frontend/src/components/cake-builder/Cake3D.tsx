"use client";

/**
 * Cake3D - Fixed version.
 * Key fixes:
 * 1. Use onPointerDown+onPointerUp with distance check (OrbitControls intercepts onClick)
 * 2. Use ref for rotating flag (avoid re-render losing click events)
 * 3. Put click handlers on visible meshes directly (more reliable than invisible hit areas)
 * 4. No Environment HDR (requires internet)
 * 5. No shadows (deprecation warnings)
 * 6. Large, emissive decorations for clear visibility
 */

import { useRef, useMemo, Suspense } from "react";
import { Canvas, useFrame, ThreeEvent } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import type { CakeDesign } from "@/types";
import { type CakeZone } from "./CakeSVG";

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
  zone, geometry, color, roughness, metalness,
  onZoneClick, onZoneHover, activeZone, hoveredZone,
  children,
}: {
  zone: CakeZone;
  geometry: React.ReactNode;
  color: string; roughness: number; metalness: number;
  onZoneClick: (z: CakeZone) => void;
  onZoneHover: (z: CakeZone | null) => void;
  activeZone: CakeZone | null;
  hoveredZone: CakeZone | null;
  children?: React.ReactNode;
}) {
  const isActive  = activeZone  === zone;
  const isHovered = hoveredZone === zone;
  const { onPointerDown, onPointerUp } = useMeshClick(() => onZoneClick(zone));

  const emissiveColor = isActive ? "#E8837A" : isHovered ? "#D4837A" : "#000000";
  const emissiveIntensity = isActive ? 0.22 : isHovered ? 0.12 : 0;

  return (
    <mesh
      onPointerDown={onPointerDown}
      onPointerUp={onPointerUp}
      onPointerEnter={(e) => { e.stopPropagation(); onZoneHover(zone); }}
      onPointerLeave={(e) => { e.stopPropagation(); onZoneHover(null); }}
    >
      {geometry}
      <meshStandardMaterial
        color={color}
        roughness={roughness}
        metalness={metalness}
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
            <meshStandardMaterial color={colors[i%6]} emissive={colors[i%6]} emissiveIntensity={0.4} roughness={0.3} />
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

// ─── ToppingGroup cho từng loại topping cụ thể ──────────────────────────────
function ToppingGroup({ type, surfaceY, R }: { type: string; surfaceY: number; R: number }) {
  const positions = useMemo<[number, number, number][]>(() => {
    // Lift toppings above the surface so selected decorations stay visible in 3D.
    const y = surfaceY + 0.035;

    // Phân bổ góc lệch cho từng loại để nếu chọn nhiều topping chúng không chồng khít lên nhau
    let offsetAngle = 0;
    if (type === "flowers") offsetAngle = 0;
    else if (type === "fruits") offsetAngle = 0.5;
    else if (type === "sprinkles") offsetAngle = 1.0;
    else if (type === "macarons") offsetAngle = 1.5;
    else if (type === "chocolate drip") offsetAngle = 2.0;

    const pts: [number, number, number][] = [];

    if (type === "text") {
      // Chữ viết chỉ đặt duy nhất ở tâm bánh
      pts.push([0, y, 0]);
    } else {
      // Vòng tròn 1
      for (let i = 0; i < 5; i++) {
        const a = (i / 5) * Math.PI * 2 + offsetAngle;
        pts.push([Math.cos(a) * R * 0.45, y, Math.sin(a) * R * 0.45]);
      }
      // Vòng tròn 2
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * Math.PI * 2 + 0.2 + offsetAngle;
        pts.push([Math.cos(a) * R * 0.75, y, Math.sin(a) * R * 0.75]);
      }
    }
    return pts;
  }, [type, surfaceY, R]);

  return (
    <group>
      {positions.map((pos, i) => {
        switch (type) {
          case "flowers":        return <Flower     key={i} p={pos} />;
          case "fruits":         return <Fruit      key={i} p={pos} />;
          case "sprinkles":      return <Sprinkle   key={i} p={pos} />;
          case "macarons":       return <Macaron    key={i} p={pos} />;
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
  return (
    <group>
      {toppings.map((toppingType) => (
        <ToppingGroup key={toppingType} type={toppingType} surfaceY={surfaceY} R={R} />
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

  // Shared geometry + material instances — one each, reused across all N meshes
  const pipingGeo  = useMemo(() => new THREE.SphereGeometry(0.06, 10, 10),    []);
  const pipingMat  = useMemo(() => new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.25, roughness: 0.25 }), [color]);

  const rOuter     = useMemo(() => new THREE.SphereGeometry(0.07, 10, 10),    []);
  const rOuterMat  = useMemo(() => new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.15, transparent: true, opacity: 0.85, roughness: 0.25 }), [color]);
  const rInner     = useMemo(() => new THREE.SphereGeometry(0.038, 8, 8),     []);
  const rInnerMat  = useMemo(() => new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.35, roughness: 0.15 }), [color]);

  const pearlGeo   = useMemo(() => new THREE.SphereGeometry(0.052, 12, 12),   []);
  const pearlMat   = useMemo(() => new THREE.MeshStandardMaterial({ color: "#FFFDD0", emissive: "#FFFACD", emissiveIntensity: 0.45, roughness: 0.03, metalness: 0.6 }), []);

  const spkGeo     = useMemo(() => new THREE.CylinderGeometry(0.015, 0.015, 0.052, 6), []);

  switch (type) {
    case "piping":
      return (
        <group>
          {pts.map((p, i) => (
            <mesh key={i} position={[p.x, y, p.z]} geometry={pipingGeo} material={pipingMat} />
          ))}
        </group>
      );
    case "rosettes":
      return (
        <group>
          {pts.map((p, i) => (
            <group key={i} position={[p.x, y, p.z]}>
              <mesh geometry={rOuter} material={rOuterMat} />
              <mesh geometry={rInner} material={rInnerMat} />
            </group>
          ))}
        </group>
      );
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
              <meshStandardMaterial color={sc[i%4]} emissive={sc[i%4]} emissiveIntensity={0.4} roughness={0.3} />
            </mesh>
          ))}
        </group>
      );
    }
    case "ribbon":
      return (
        <mesh position={[0, y, 0]}>
          <torusGeometry args={[R + 0.04, 0.04, 10, 80]} />
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} transparent opacity={0.92} roughness={0.15} />
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
            <mesh key={i} position={[0, y+off, 0]}>
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
  const bodyColor   = design.zones?.body?.color   || design.cream_color || "#E8837A";
  const borderColor = design.zones?.border?.color || "#D4A574";
  const topColor    = design.zones?.top?.color    || bodyColor;

  const size = design.size;
  const zoneProps = { onZoneClick, onZoneHover, activeZone, hoveredZone };

  const activeToppings = getVisibleToppings(design);

  if (size === "2-tier") {
    // Bottom Tier Dimensions
    const R1 = 0.9;
    const bodyH1 = 0.55;
    const borderH1 = 0.20;
    const topH1 = 0.06;

    const bodyY1 = 0;
    const borderY1 = -(bodyH1 / 2 + borderH1 / 2);
    const topY1 = bodyH1 / 2 + topH1 / 2;
    const topSurface1 = bodyH1 / 2 + topH1;

    // Top Tier Dimensions
    const R2 = 0.60;
    const bodyH2 = 0.45;
    const borderH2 = 0.16;
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
          <ZoneMesh zone="body" color={bodyColor} roughness={0.35} metalness={0.05}
            geometry={<cylinderGeometry args={[R1, R1, bodyH1, 64]} />} {...zoneProps} />
          <BodyPattern type={design.zones?.body?.decoration || ""} R={R1} H={bodyH1} y={0} />
        </group>

        {/* Viền dưới tầng dưới */}
        <group position={[0, borderY1, 0]}>
          <ZoneMesh zone="border" color={borderColor} roughness={0.28} metalness={0.1}
            geometry={<cylinderGeometry args={[R1 + 0.028, R1 + 0.028, borderH1, 64]} />} {...zoneProps} />
          {design.zones?.border?.decoration && (
            <BorderDecor type={design.zones.border.decoration} color={borderColor} R={R1 + 0.028} y={0.05} />
          )}
        </group>

        {/* Mặt trên tầng dưới */}
        <group position={[0, topY1, 0]}>
          <ZoneMesh zone="top" color={topColor} roughness={0.22} metalness={0.05}
            geometry={<cylinderGeometry args={[R1, R1, topH1, 64]} />} {...zoneProps} />
        </group>


        {/* ─── TẦNG TRÊN (Top Tier) ─── */}
        {/* Thân bánh tầng trên */}
        <group position={[0, bodyY2, 0]}>
          <ZoneMesh zone="body" color={bodyColor} roughness={0.35} metalness={0.05}
            geometry={<cylinderGeometry args={[R2, R2, bodyH2, 64]} />} {...zoneProps} />
          <BodyPattern type={design.zones?.body?.decoration || ""} R={R2} H={bodyH2} y={0} />
        </group>

        {/* Viền dưới tầng trên */}
        <group position={[0, borderY2, 0]}>
          <ZoneMesh zone="border" color={borderColor} roughness={0.28} metalness={0.1}
            geometry={<cylinderGeometry args={[R2 + 0.028, R2 + 0.028, borderH2, 64]} />} {...zoneProps} />
          {design.zones?.border?.decoration && (
            <BorderDecor type={design.zones.border.decoration} color={borderColor} R={R2 + 0.028} y={0.04} />
          )}
        </group>

        {/* Mặt trên tầng trên */}
        <group position={[0, topY2, 0]}>
          <ZoneMesh zone="top" color={topColor} roughness={0.22} metalness={0.05}
            geometry={<cylinderGeometry args={[R2, R2, topH2, 64]} />} {...zoneProps} />
        </group>

        {/* Highlight mặt trên cùng */}
        <mesh position={[0, topSurface2 + 0.003, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <circleGeometry args={[R2 * 0.55, 40]} />
          <meshStandardMaterial color="#FFFFFF" transparent opacity={0.18} roughness={0.1} depthWrite={false} />
        </mesh>

        {/* ── Toppings mặt trên cùng ── */}
        <TopToppings toppings={activeToppings} surfaceY={topSurface2} R={R2 * 0.82} />

        {/* ── Đĩa bánh ── */}
        <mesh position={[0, borderY1 - borderH1 / 2 - 0.02, 0]}>
          <cylinderGeometry args={[R1 + 0.30, R1 + 0.30, 0.035, 64]} />
          <meshStandardMaterial color="#F8F4E8" roughness={0.55} />
        </mesh>
        <mesh position={[0, borderY1 - borderH1 / 2 - 0.038, 0]}>
          <cylinderGeometry args={[R1 + 0.32, R1 + 0.32, 0.007, 64]} />
          <meshStandardMaterial color="#D4A574" roughness={0.36} />
        </mesh>
      </group>
    );
  }

  // Single Tier Dimensions (16cm, 20cm, 24cm)
  let R = 0.82;
  let bodyH = 0.86;
  let borderH = 0.22;
  let topH = 0.08;

  if (size === "16cm") {
    R = 0.65;
    bodyH = 0.72;
    borderH = 0.18;
    topH = 0.06;
  } else if (size === "24cm") {
    R = 1.0;
    bodyH = 0.96;
    borderH = 0.25;
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
        <ZoneMesh zone="body" color={bodyColor} roughness={0.35} metalness={0.05}
          geometry={<cylinderGeometry args={[R, R, bodyH, 64]} />} {...zoneProps} />
        <BodyPattern type={design.zones?.body?.decoration || ""} R={R} H={bodyH} y={0} />
      </group>

      {/* ── Viền dưới (clickable) ── */}
      <group position={[0, borderY, 0]}>
        <ZoneMesh zone="border" color={borderColor} roughness={0.28} metalness={0.1}
          geometry={<cylinderGeometry args={[R+0.028, R+0.028, borderH, 64]} />} {...zoneProps} />
        {design.zones?.border?.decoration && (
          <BorderDecor type={design.zones.border.decoration} color={borderColor} R={R+0.028} y={0.05} />
        )}
      </group>

      {/* ── Mặt trên (clickable) ── */}
      <group position={[0, topY, 0]}>
        <ZoneMesh zone="top" color={topColor} roughness={0.22} metalness={0.05}
          geometry={<cylinderGeometry args={[R, R, topH, 64]} />} {...zoneProps} />
      </group>

      {/* Highlight mặt trên */}
      <mesh position={[0, topSurface+0.003, 0]} rotation={[-Math.PI/2, 0, 0]}>
        <circleGeometry args={[R*0.55, 40]} />
        <meshStandardMaterial color="#FFFFFF" transparent opacity={0.18} roughness={0.1} depthWrite={false} />
      </mesh>

      {/* ── Toppings mặt trên ── */}
      <TopToppings toppings={activeToppings} surfaceY={topSurface} R={R*0.82} />

      {/* ── Đĩa bánh ── */}
      <mesh position={[0, borderY - borderH/2 - 0.02, 0]}>
        <cylinderGeometry args={[R+0.30, R+0.30, 0.035, 64]} />
        <meshStandardMaterial color="#F8F4E8" roughness={0.55} />
      </mesh>
      <mesh position={[0, borderY - borderH/2 - 0.038, 0]}>
        <cylinderGeometry args={[R+0.32, R+0.32, 0.007, 64]} />
        <meshStandardMaterial color="#D4A574" roughness={0.36} />
      </mesh>
    </group>
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
        maxPolarAngle={Math.PI * 0.80}
        dampingFactor={0.1}
        enableDamping
        onStart={() => { rotating.current = false; }}
        onEnd={()   => { rotating.current = true;  }}
      />
      <CakeMesh {...props} />
    </group>
  );
}

// ─── Scene lighting ───────────────────────────────────────────────────────────
function Scene(props: Cake3DProps) {
  return (
    <>
      <ambientLight intensity={1.0} />
      <directionalLight position={[4, 6, 4]}  intensity={1.5} color="#FFFAF0" />
      <directionalLight position={[-3, 3, -3]} intensity={0.6} color="#FFD0C0" />
      <directionalLight position={[0, -2, 3]}  intensity={0.3} color="#FFF0E8" />
      <pointLight position={[0, 4, 0]} intensity={0.8} color="#FFFBF0" />
      <RotatingCake {...props} />
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
        background: "transparent",
        cursor: props.enableControls === false ? "default" : "grab",
      }}
    >
      {/* Canvas */}
      <Canvas
        camera={{ position: [0, 1.1, 4.2], fov: 30 }}
        gl={{ antialias: true, alpha: true }}
        style={{ width:"100%", height:"100%" }}
      >
        <Suspense fallback={null}>
          <Scene {...props} />
        </Suspense>
      </Canvas>
    </div>
  );
}
