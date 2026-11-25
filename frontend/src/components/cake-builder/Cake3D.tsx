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
import CanvasErrorBoundary from "./CanvasErrorBoundary";
import { tiersForDesign } from "@/lib/price-calculator";
import type { CakeDecorationTier } from "./cake-decoration-surface";

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
        clearcoatRoughness={0.26}
        sheen={0.45}
        sheenRoughness={0.48}
        sheenColor="#FFFDF8"
        bumpMap={icingTexture}
        bumpScale={0.0042}
        envMapIntensity={0.75}
        emissive={emissiveColor}
        emissiveIntensity={emissiveIntensity}
      />
      {children}
    </mesh>
  );
}

function Flower({ p }: { p: [number, number, number] }) {
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
  return (
    <group position={p}>
      <mesh position={[-0.1, 0.105, 0]}>
        <sphereGeometry args={[0.105, 12, 12]} />
        <meshStandardMaterial color="#FF2020" emissive="#CC0000" emissiveIntensity={0.35} roughness={0.25} />
      </mesh>
      <mesh position={[0.1, 0.09, 0.035]}>
        <sphereGeometry args={[0.09, 12, 12]} />
        <meshStandardMaterial color="#FFD700" emissive="#E6B800" emissiveIntensity={0.3} roughness={0.3} />
      </mesh>
      <mesh position={[0, 0.08, -0.1]}>
        <sphereGeometry args={[0.08, 12, 12]} />
        <meshStandardMaterial color="#22CC44" emissive="#009922" emissiveIntensity={0.3} roughness={0.4} />
      </mesh>
    </group>
  );
}

function Sprinkle({ p }: { p: [number, number, number] }) {
  const colors = ["#FF69B4","#87CEEB","#98FB98","#FFD700","#FF6347","#DA70D6"];
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
  return (
    <group position={p}>
      <mesh position={[0, 0.028, 0]}>
        <cylinderGeometry args={[0.125, 0.118, 0.056, 18]} />
        <meshStandardMaterial color="#FFB6C1" emissive="#FF8FA3" emissiveIntensity={0.3} roughness={0.2} />
      </mesh>
      <mesh position={[0, 0.07, 0]}>
        <cylinderGeometry args={[0.112, 0.112, 0.028, 18]} />
        <meshStandardMaterial color="#FFF0F5" emissive="#FFD0DC" emissiveIntensity={0.2} roughness={0.15} />
      </mesh>
      <mesh position={[0, 0.112, 0]}>
        <cylinderGeometry args={[0.125, 0.118, 0.056, 18]} />
        <meshStandardMaterial color="#FFB6C1" emissive="#FF8FA3" emissiveIntensity={0.3} roughness={0.2} />
      </mesh>
    </group>
  );
}

function ChocoDrip({ p }: { p: [number, number, number] }) {
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
  return (
    <group position={p} rotation={[-Math.PI/2, 0, 0]} scale={[1.35, 1.35, 1.35]}>
      {[
        { x:-0.18, y:0, w:0.04, h:0.18, c:"#5C3D2E" },
        { x:-0.10, y:0, w:0.04, h:0.18, c:"#5C3D2E" },
        { x:-0.14, y:0, w:0.08, h:0.04, c:"#5C3D2E" },
        { x:-0.02, y:0, w:0.04, h:0.18, c:"#E8837A" },
        { x: 0.04, y:0.05, w:0.06, h:0.04, c:"#E8837A" },
        { x: 0.04, y:0, w:0.06, h:0.04, c:"#E8837A" },
        { x: 0.04, y:-0.05, w:0.06, h:0.04, c:"#E8837A" },
        { x: 0.14, y:0, w:0.04, h:0.18, c:"#5C3D2E" },
        { x: 0.20, y:0.05, w:0.06, h:0.04, c:"#5C3D2E" },
        { x: 0.20, y:-0.05, w:0.06, h:0.04, c:"#5C3D2E" },
      ].map((seg, i) => (
        <mesh key={i} position={[seg.x, seg.y, 0.014]}>
          <boxGeometry args={[seg.w, seg.h, 0.028]} />
          <meshStandardMaterial color={seg.c} emissive={seg.c} emissiveIntensity={0.5} roughness={0.3} />
        </mesh>
      ))}
    </group>
  );
}

/** Bảng chữ Socola / Fondant viền vàng kim hiển thị lời nhắn thực tế */
function ChocolatePlaque({ p, text = "Happy Birthday" }: { p: [number, number, number]; text?: string }) {
  const plaqueTexture = useMemo(() => {
    if (typeof document === "undefined") return null;
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 256;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.fillStyle = "#26120B";
      ctx.fillRect(0, 0, 512, 256);

      ctx.strokeStyle = "#E5C178";
      ctx.lineWidth = 10;
      ctx.strokeRect(16, 16, 480, 224);
      ctx.strokeStyle = "rgba(229, 193, 120, 0.48)";
      ctx.lineWidth = 3;
      ctx.strokeRect(28, 28, 456, 200);

      ctx.fillStyle = "#FFF5D6";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const cleanText = (text || "").trim() || "Happy Birthday";
      const lines =
        cleanText.length > 16 && cleanText.includes(" ")
          ? (() => {
              const words = cleanText.split(" ");
              const mid = Math.ceil(words.length / 2);
              return [words.slice(0, mid).join(" "), words.slice(mid).join(" ")];
            })()
          : [cleanText];

      ctx.font = lines.length > 1 ? "italic 700 44px Georgia, serif" : "italic 700 52px Georgia, serif";
      ctx.shadowColor = "rgba(0,0,0,0.45)";
      ctx.shadowBlur = 4;
      ctx.shadowOffsetY = 2;

      if (lines.length === 1) {
        ctx.fillText(lines[0], 256, 130, 430);
      } else {
        ctx.fillText(lines[0], 256, 98, 430);
        ctx.fillText(lines[1], 256, 160, 430);
      }
    }
    const tex = new THREE.CanvasTexture(canvas);
    tex.anisotropy = 4;
    tex.needsUpdate = true;
    return tex;
  }, [text]);

  useEffect(() => () => plaqueTexture?.dispose(), [plaqueTexture]);

  if (!plaqueTexture) return <HBDBlocks p={p} />;

  return (
    <group position={[p[0], p[1] + 0.082, p[2] + 0.06]} rotation={[-0.48, 0, 0]}>
      <mesh castShadow receiveShadow>
        <boxGeometry args={[0.42, 0.21, 0.02]} />
        <meshPhysicalMaterial
          map={plaqueTexture}
          roughness={0.22}
          clearcoat={0.68}
          clearcoatRoughness={0.18}
        />
      </mesh>
      <mesh position={[0, -0.03, -0.025]} rotation={[0.4, 0, 0]} castShadow>
        <cylinderGeometry args={[0.024, 0.034, 0.08, 12]} />
        <meshPhysicalMaterial color="#26120B" roughness={0.35} clearcoat={0.4} />
      </mesh>
    </group>
  );
}

type DecorationFile = "flower" | "strawberry" | "macaron" | "candle";

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
  const { instance, materials } = useMemo(() => {
    const clone = scene.clone(true);
    const createdMaterials: THREE.Material[] = [];
    const flowerTones = ["#E68FA5", "#F0A8BA", "#F7C5D1", "#6D8756"];
    let partIdx = 0;

    clone.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        object.castShadow = true;
        object.receiveShadow = true;
        if (file === "flower") {
          const mat = new THREE.MeshPhysicalMaterial({
            color: flowerTones[Math.min(partIdx, flowerTones.length - 1)],
            roughness: 0.42,
            clearcoat: 0.18,
            sheen: 0.35,
            side: THREE.DoubleSide,
          });
          object.material = mat;
          createdMaterials.push(mat);
          partIdx++;
        } else if (file === "candle" && object.name.includes("part_3")) {
          const flameMat = new THREE.MeshStandardMaterial({
            color: "#FFF5B8",
            emissive: "#FF9800",
            emissiveIntensity: 2.8,
            roughness: 0.1,
          });
          object.material = flameMat;
          createdMaterials.push(flameMat);
        }
      }
    });
    return { instance: clone, materials: createdMaterials };
  }, [scene, file]);

  useEffect(() => () => materials.forEach((m) => m.dispose()), [materials]);

  const scale = file === "strawberry" ? 1.55 : file === "macaron" ? 1.25 : file === "candle" ? 1.02 : 1.12;
  const s = scale * sizeScale;

  if (file === "candle") {
    return (
      <group position={p}>
        <primitive object={instance} rotation={[0, rotation, 0]} scale={s} dispose={null} />
        <mesh position={[0, 0.32 * s, 0]}>
          <sphereGeometry args={[0.032 * s, 10, 10]} />
          <meshBasicMaterial color="#FFB74D" transparent opacity={0.35} />
        </mesh>
        <pointLight position={[0, 0.34 * s, 0]} color="#FFA726" intensity={0.42} distance={1.4} decay={2} />
      </group>
    );
  }

  return <primitive object={instance} position={p} rotation={[0, rotation, 0]} scale={s} dispose={null} />;
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
function ToppingGroup({
  type,
  surfaceY,
  R,
  slot = 0,
  slots = 1,
  surfaceAt,
  edgeAt,
  specialNotes,
}: {
  type: string;
  surfaceY: number;
  R: number;
  slot?: number;
  slots?: number;
  surfaceAt?: (x: number, z: number) => number;
  edgeAt?: CakeDecorationTier["edgeAt"];
  specialNotes?: string;
}) {
  const sizeScale = Math.min(1, R / 0.78);
  const positions = useMemo<[number, number, number][]>(() => {
    const y = surfaceY + 0.005;
    const pts: [number, number, number][] = [];

    if (type === "text") {
      pts.push([0, y, 0]);
    } else {
      const count = type === "sprinkles" ? 8 : slots > 1 ? 3 : 6;
      const radius = R * 0.65;
      for (let i = 0; i < count; i++) {
        const a = ((i * slots + slot) / (count * slots)) * Math.PI * 2 + 0.42;
        const edge = edgeAt?.(a / (Math.PI * 2)).multiplyScalar(0.64);
        pts.push(edge ? [edge.x, y, edge.y] : [Math.cos(a) * radius, y, Math.sin(a) * radius]);
      }
    }
    return surfaceAt ? pts.map(([x, , z]) => [x, surfaceAt(x, z) + 0.005, z]) : pts;
  }, [type, surfaceY, R, slot, slots, surfaceAt, edgeAt]);

  const candlePositions = useMemo<[number, number, number][]>(() => {
    if (type !== "text") return [];
    const pts: [number, number, number][] = [];
    for (let i = 0; i < 3; i++) {
      const a = (i - 1) * 0.44 - Math.PI / 2;
      const r = R * 0.36;
      const x = Math.cos(a) * r;
      const z = Math.sin(a) * r;
      const y = (surfaceAt ? surfaceAt(x, z) : surfaceY) + 0.005;
      pts.push([x, y, z]);
    }
    return pts;
  }, [type, R, surfaceAt, surfaceY]);

  return (
    <group>
      {positions.map((pos, i) => {
        switch (type) {
          case "flowers":        return <ModelOrFallback key={i} file="flower" p={pos} rotation={i * 0.45} sizeScale={sizeScale} fallback={<Flower p={pos} />} />;
          case "fruits":         return <ModelOrFallback key={i} file="strawberry" p={pos} rotation={i * 0.6} sizeScale={sizeScale} fallback={<Fruit p={pos} />} />;
          case "sprinkles":      return <Sprinkle   key={i} p={pos} />;
          case "macarons":       return <ModelOrFallback key={i} file="macaron" p={pos} rotation={i * 0.45} sizeScale={sizeScale} fallback={<Macaron p={pos} />} />;
          case "chocolate drip": return <ChocoDrip  key={i} p={pos} />;
          case "text":           return (
            <group key={i}>
              <ChocolatePlaque p={pos} text={specialNotes || "Happy Birthday"} />
              {candlePositions.map((cPos, ci) => (
                <ModelOrFallback key={`candle-${ci}`} file="candle" p={cPos} rotation={0} sizeScale={sizeScale} fallback={null} />
              ))}
            </group>
          );
          default:               return null;
        }
      })}
    </group>
  );
}

// ─── Toppings mặt trên (chấp nhận mảng toppings) ─────────────────────────────
function TopToppings({
  toppings,
  surfaceY,
  R,
  surfaceAt,
  tier,
  specialNotes,
}: {
  toppings?: string[];
  surfaceY: number;
  R: number;
  surfaceAt?: (x: number, z: number) => number;
  tier?: CakeDecorationTier;
  specialNotes?: string;
}) {
  if (!toppings || toppings.length === 0) return null;
  const ringToppings = toppings.filter((type) => ["flowers", "fruits", "macarons"].includes(type));
  return (
    <group>
      {toppings.map((type) => type === "chocolate drip" ? (
        <Ganache key={type} radius={R} surfaceY={surfaceY} tier={tier} />
      ) : (
        <ToppingGroup key={type} type={type} surfaceY={surfaceY} R={R} surfaceAt={surfaceAt} edgeAt={tier?.edgeAt}
          slot={Math.max(0, ringToppings.indexOf(type))} slots={Math.max(1, ringToppings.length)}
          specialNotes={specialNotes} />
      ))}
    </group>
  );
}

function getVisibleToppings(design: CakeDesign): string[] {
  if (Array.isArray(design.zones?.top?.toppings)) {
    return Array.from(new Set(design.zones?.top?.toppings)).filter(Boolean);
  }
  const legacyToppings = Array.isArray(design.topping_type) ? design.topping_type : [];
  return Array.from(new Set(legacyToppings)).filter(Boolean);
}

function BorderDecor({ type, color, R, y, path }: { type: string; color: string; R: number; y: number; path?: THREE.Curve<THREE.Vector3> }) {
  const N = 24;
  const pts = useMemo(() =>
    Array.from({ length: N }, (_, i) => {
      const a = (i / N) * Math.PI * 2;
      const point = path?.getPointAt(i / N);
      return { x: point?.x ?? Math.cos(a) * (R + 0.06), z: point?.z ?? Math.sin(a) * (R + 0.06), y: point?.y ?? y, a };
    }), [R, y, path]);

  const pearlGeo   = useMemo(() => new THREE.SphereGeometry(0.048, 14, 14),   []);
  const pearlMat   = useMemo(() => new THREE.MeshPhysicalMaterial({ color: "#FFFDF6", roughness: 0.22, metalness: 0.18, clearcoat: 0.65 }), []);

  const spkGeo     = useMemo(() => new THREE.CylinderGeometry(0.015, 0.015, 0.052, 6), []);
  useEffect(() => () => {
    pearlGeo.dispose();
    pearlMat.dispose();
    spkGeo.dispose();
  }, [pearlGeo, pearlMat, spkGeo]);

  switch (type) {
    case "piping":
      return <PipedBorder radius={R} y={y} color={color} path={path} />;
    case "rosettes":
      return <PipedBorder radius={R} y={y} color={color} rosettes path={path} />;
    case "pearls":
      return (
        <group>
          {pts.map((p, i) => (
            <mesh key={i} position={[p.x, p.y, p.z]} geometry={pearlGeo} material={pearlMat} />
          ))}
        </group>
      );
    case "sprinkles": {
      const sc = ["#FF69B4","#87CEEB","#98FB98","#FFD700"];
      return (
        <group>
          {pts.map((p, i) => (
            <mesh key={i} position={[p.x, p.y+(i%3-1)*0.022, p.z]} rotation={[Math.PI/2, 0, p.a]} geometry={spkGeo}>
              <meshStandardMaterial color={sc[i%4]} roughness={0.55} />
            </mesh>
          ))}
        </group>
      );
    }
    case "ribbon":
      if (path) return <mesh>
        <tubeGeometry args={[path, 192, 0.025, 8, true]} />
        <meshPhysicalMaterial color={color} roughness={0.42} clearcoat={0.25} />
      </mesh>;
      return (
        <mesh position={[0, y, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[R + 0.04, 0.04, 10, 80]} />
          <meshPhysicalMaterial color={color} roughness={0.42} clearcoat={0.25} />
        </mesh>
      );
    default:
      return null;
  }
}

// ─── Hoa văn thân bánh nổi 3D (tự tạo tương phản khi bánh màu sáng) ────────────
function BodyPattern({
  type,
  R,
  H,
  y,
  path,
  bodyColor = "#FAF3E6",
  borderColor = "#F5E6CC",
}: {
  type: string;
  R: number;
  H: number;
  y: number;
  path?: THREE.Curve<THREE.Vector3>;
  bodyColor?: string;
  borderColor?: string;
}) {
  const accentColor = useMemo(() => {
    const cleanBody = (bodyColor || "#FAF3E6").toUpperCase();
    const cleanBorder = (borderColor || "#F5E6CC").toUpperCase();
    if (cleanBorder !== cleanBody && cleanBorder !== "#F2F1EE" && cleanBorder !== "#FFFFFF") {
      return borderColor;
    }
    const c = new THREE.Color(bodyColor || "#FAF3E6");
    const lum = c.r * 0.299 + c.g * 0.587 + c.b * 0.114;
    return lum > 0.78 ? "#DEAF66" : "#FFFBF0";
  }, [bodyColor, borderColor]);

  switch (type) {
    case "stripes":
      return (
        <group>
          {Array.from({ length: 18 }, (_, i) => {
            const a = (i / 18) * Math.PI * 2;
            const p = path?.getPointAt(i / 18).multiplyScalar(1.005);
            return (
              <mesh
                key={i}
                position={[p?.x ?? Math.cos(a) * (R + 0.004), y, p?.z ?? Math.sin(a) * (R + 0.004)]}
                castShadow
              >
                <cylinderGeometry args={[0.009, 0.009, H * 0.82, 10]} />
                <meshPhysicalMaterial color={accentColor} roughness={0.3} clearcoat={0.45} />
              </mesh>
            );
          })}
        </group>
      );
    case "dots":
      return (
        <group>
          {Array.from({ length: 30 }, (_, i) => {
            const a = (i / 30) * Math.PI * 2;
            const yOff = ((i % 3) - 1) * (H * 0.24);
            const p = path?.getPointAt(i / 30).multiplyScalar(1.006);
            return (
              <mesh
                key={i}
                position={[p?.x ?? Math.cos(a) * (R + 0.004), y + yOff, p?.z ?? Math.sin(a) * (R + 0.004)]}
                castShadow
              >
                <sphereGeometry args={[0.022, 12, 12]} />
                <meshPhysicalMaterial color={accentColor} roughness={0.22} metalness={0.38} clearcoat={0.75} />
              </mesh>
            );
          })}
        </group>
      );
    case "waves":
      if (path) return <group>
        {[-0.24, 0, 0.24].map((fraction, i) => <mesh key={i} position={[0, y + fraction * H, 0]} castShadow>
          <tubeGeometry args={[path, 192, 0.014, 10, true]} />
          <meshPhysicalMaterial color={accentColor} roughness={0.3} clearcoat={0.45} />
        </mesh>)}
      </group>;
      return (
        <group>
          {[0.24, 0.0, -0.24].map((off, i) => (
            <mesh key={i} position={[0, y+off, 0]} rotation={[Math.PI / 2, 0, 0]} castShadow>
              <torusGeometry args={[R*1.002, 0.014, 10, 80]} />
              <meshPhysicalMaterial color={accentColor} roughness={0.3} clearcoat={0.45} />
            </mesh>
          ))}
        </group>
      );
    default:
      return null;
  }
}

// ─── Toàn bộ mô hình bánh (Fallback khi đang tải GLB) ─────────────────────────
function CakeMesh({ design, activeZone, hoveredZone, onZoneClick, onZoneHover }: Cake3DProps) {
  const rawBody = design.zones?.body?.color || design.cream_color || "#FAF3E6";
  const bodyColor   = rawBody === "#F2F1EE" ? "#FAF3E6" : rawBody;
  const rawBorder = design.zones?.border?.color || "#F5E6CC";
  const borderColor = rawBorder === "#F2F1EE" ? "#F5E6CC" : rawBorder;
  const rawTop = design.zones?.top?.color || bodyColor;
  const topColor    = rawTop === "#F2F1EE" ? "#FFFDF8" : rawTop;

  const size = design.size;
  const tiers = tiersForDesign(design);
  const zoneProps = { onZoneClick, onZoneHover, activeZone, hoveredZone };

  const activeToppings = getVisibleToppings(design);

  if (tiers >= 2) {
    const R1 = 0.9;
    const bodyH1 = 0.55;
    const borderH1 = 0.075;
    const topH1 = 0.06;

    const bodyY1 = 0;
    const borderY1 = -(bodyH1 / 2 + borderH1 / 2);
    const topY1 = bodyH1 / 2 + topH1 / 2;
    const topSurface1 = bodyH1 / 2 + topH1;

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
        <group position={[0, bodyY1, 0]}>
          <ZoneMesh zone="body" color={bodyColor} roughness={0.42} clearcoat={0.25}
            geometry={<RoundedCylinder radius={R1} height={bodyH1} roundTop={false} capTop={false} />} {...zoneProps} />
          <BodyPattern type={design.zones?.body?.decoration || ""} R={R1} H={bodyH1} y={0} bodyColor={bodyColor} borderColor={borderColor} />
        </group>

        <group position={[0, borderY1, 0]}>
          <ZoneMesh zone="border" color={borderColor} roughness={0.38} clearcoat={0.3}
            geometry={<RoundedCylinder radius={R1 + 0.01} height={borderH1} bevel={0.025} />} {...zoneProps} />
          <BorderDecor type={design.zones?.border?.decoration || "piping"} color={borderColor} R={R1 + 0.014} y={0} />
        </group>

        <group position={[0, topY1, 0]}>
          <ZoneMesh zone="top" color={topColor} roughness={0.34} clearcoat={0.42}
            geometry={<RoundedCylinder radius={R1} height={topH1} bevel={0.028} roundBottom={false} capBottom={false} />} {...zoneProps} />
        </group>

        <group position={[0, bodyY2, 0]}>
          <ZoneMesh zone="body" color={bodyColor} roughness={0.42} clearcoat={0.25}
            geometry={<RoundedCylinder radius={R2} height={bodyH2} roundTop={false} capTop={false} />} {...zoneProps} />
          <BodyPattern type={design.zones?.body?.decoration || ""} R={R2} H={bodyH2} y={0} bodyColor={bodyColor} borderColor={borderColor} />
        </group>

        <group position={[0, borderY2, 0]}>
          <ZoneMesh zone="border" color={borderColor} roughness={0.38} clearcoat={0.3}
            geometry={<RoundedCylinder radius={R2 + 0.01} height={borderH2} bevel={0.02} />} {...zoneProps} />
          <BorderDecor type={design.zones?.border?.decoration || "piping"} color={borderColor} R={R2 + 0.014} y={0.055} />
        </group>

        <group position={[0, topY2, 0]}>
          <ZoneMesh zone="top" color={topColor} roughness={0.34} clearcoat={0.42}
            geometry={<RoundedCylinder radius={R2} height={topH2} bevel={0.028} roundBottom={false} capBottom={false} />} {...zoneProps} />
        </group>

        <TopToppings toppings={activeToppings} surfaceY={topSurface2} R={R2} specialNotes={design.special_notes} />

        <mesh position={[0, borderY1 - borderH1 / 2 - 0.02, 0]}>
          <RoundedCylinder radius={R1 + 0.23} height={0.035} bevel={0.012} />
          <meshPhysicalMaterial color="#F3ECE0" roughness={0.25} clearcoat={0.6} />
        </mesh>
        <mesh position={[0, borderY1 - borderH1 / 2 - 0.012, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[R1 + 0.23, 0.008, 12, 80]} />
          <meshPhysicalMaterial color="#D4A64E" roughness={0.18} metalness={0.88} clearcoat={0.75} />
        </mesh>
      </group>
    );
  }

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
      <group position={[0, bodyY, 0]}>
        <ZoneMesh zone="body" color={bodyColor} roughness={0.42} clearcoat={0.25}
          geometry={<RoundedCylinder radius={R} height={bodyH} roundTop={false} capTop={false} />} {...zoneProps} />
        <BodyPattern type={design.zones?.body?.decoration || ""} R={R} H={bodyH} y={0} bodyColor={bodyColor} borderColor={borderColor} />
      </group>

      <group position={[0, borderY, 0]}>
        <ZoneMesh zone="border" color={borderColor} roughness={0.38} clearcoat={0.3}
          geometry={<RoundedCylinder radius={R + 0.01} height={borderH} bevel={0.025} />} {...zoneProps} />
        <BorderDecor type={design.zones?.border?.decoration || "piping"} color={borderColor} R={R + 0.014} y={0} />
      </group>

      <group position={[0, topY, 0]}>
        <ZoneMesh zone="top" color={topColor} roughness={0.34} clearcoat={0.42}
          geometry={<RoundedCylinder radius={R} height={topH} bevel={0.035} roundBottom={false} capBottom={false} />} {...zoneProps} />
      </group>

      <TopToppings toppings={activeToppings} surfaceY={topSurface} R={R} specialNotes={design.special_notes} />

      <mesh position={[0, borderY - borderH/2 - 0.02, 0]}>
        <RoundedCylinder radius={R + 0.23} height={0.035} bevel={0.012} />
        <meshPhysicalMaterial color="#F3ECE0" roughness={0.25} clearcoat={0.6} />
      </mesh>
      <mesh position={[0, borderY - borderH/2 - 0.012, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[R + 0.23, 0.008, 12, 80]} />
        <meshPhysicalMaterial color="#D4A64E" roughness={0.18} metalness={0.88} clearcoat={0.75} />
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
    if (previousProps.children !== this.props.children && this.state.hasError) {
      this.setState({ hasError: false });
    }
  }

  render() {
    return this.state.hasError ? this.props.fallback : this.props.children;
  }
}

function SelectedCakeBody(props: Cake3DProps) {
  const toppings = getVisibleToppings(props.design);
  const bodyColor = props.design.zones?.body?.color || props.design.cream_color || "#FAF3E6";
  const borderColor = props.design.zones?.border?.color || "#F5E6CC";
  return (
    <CakeBodyFallbackBoundary fallback={<CakeMesh {...props} />}>
      <Suspense fallback={<CakeMesh {...props} />}>
        <GlbCakeBody {...props} renderDecorations={(tiers) => (
          <group>
            {tiers.map((tier, index) => (
              <group key={index}>
                <BodyPattern
                  type={props.design.zones?.body?.decoration || ""}
                  R={tier.radius}
                  H={tier.height}
                  y={tier.bodyY}
                  path={tier.bodyPath}
                  bodyColor={bodyColor}
                  borderColor={borderColor}
                />
                <BorderDecor
                  type={props.design.zones?.border?.decoration || ""}
                  color={borderColor === "#F2F1EE" ? "#F5E6CC" : borderColor}
                  R={tier.radius}
                  y={tier.borderY}
                  path={tier.borderPath}
                />
                {index === tiers.length - 1 && <TopToppings
                  toppings={toppings}
                  R={tier.radius}
                  surfaceY={tier.surfaceY}
                  surfaceAt={tier.surfaceAt}
                  tier={tier}
                  specialNotes={props.design.special_notes}
                />}
              </group>
            ))}
          </group>
        )} />
      </Suspense>
    </CakeBodyFallbackBoundary>
  );
}

const FIXED_VIEWS: Record<string, [number, number, number]> = {
  front: [0, 1.1, 3.4],
  top: [0.01, 3.2, 1.1],
  side: [3.4, 1.1, 0.01],
  back: [0, 1.1, -3.4],
};

function spinView(view: string): [number, number, number] | null {
  const match = /^spin-([0-7])$/.exec(view);
  if (!match) return null;
  const angle = (Number(match[1]) * Math.PI) / 4;
  const distance = 3.4;
  return [Math.sin(angle) * distance, 1.1, Math.cos(angle) * distance];
}

function useFixedCamera(): [number, number, number] | null {
  if (typeof window === "undefined") return null;
  const view = new URLSearchParams(window.location.search).get("view");
  if (!view) return null;
  if (FIXED_VIEWS[view]) return FIXED_VIEWS[view];
  return spinView(view);
}

function RotatingCake(props: Cake3DProps) {
  const groupRef  = useRef<THREE.Group>(null!);
  const rotating  = useRef(true);
  const fixedView = useFixedCamera();

  useFrame((_, dt) => {
    const spinning =
      props.autoRotate !== false && rotating.current && groupRef.current && !fixedView;
    if (spinning) {
      groupRef.current.rotation.y += dt * 0.28;
    }
  });

  return (
    <group ref={groupRef} rotation={fixedView ? [0, 0, 0] : undefined}>
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
      <group scale={tiersForDesign(props.design) >= 2 || props.design.size === "24cm" ? 0.9 : 1}
        position={[0, tiersForDesign(props.design) >= 2 ? -0.16 : props.design.size === "24cm" ? 0.09 : 0, 0]}>
        <SelectedCakeBody {...props} />
      </group>
    </group>
  );
}

// ─── Scene lighting (Patisserie Studio ấm áp & nổi khối) ─────────────────────
function Scene(props: Cake3DProps) {
  const shadowY = tiersForDesign(props.design) >= 2
    ? -0.52
    : {
        "16cm": -0.47,
        "20cm": -0.55,
        "24cm": -0.46,
        "2-tier": -0.52,
      }[props.design.size];

  return (
    <>
      <hemisphereLight args={["#FFFDF8", "#E2D7C7", 0.82]} />
      <directionalLight position={[-3.2, 5.0, 3.8]} intensity={2.35} color="#FFFBF0" castShadow
        shadow-mapSize={[1024, 1024]} shadow-bias={-0.0003} shadow-normalBias={0.02}
        shadow-camera-left={-2} shadow-camera-right={2} shadow-camera-top={2} shadow-camera-bottom={-2}
        shadow-camera-near={0.5} shadow-camera-far={12} shadow-radius={4} shadow-blurSamples={8} />
      <directionalLight position={[4.0, 2.0, 1.4]} intensity={0.68} color="#FFF1DC" />
      <directionalLight position={[0.4, 3.6, -4.0]} intensity={1.0} color="#F5F8FF" />
      <Environment resolution={128}>
        <Lightformer form="rect" intensity={2.0} position={[-3.2, 4.2, 3]} scale={[4.2, 7, 1]} color="#FFFDF8" />
        <Lightformer form="rect" intensity={1.1} position={[4, 2, 1.2]} scale={[3.2, 6, 1]} color="#FFF4E4" />
        <Lightformer form="circle" intensity={4.5} position={[1.5, 3.6, 2.4]} scale={0.6} color="#FFFFFF" />
      </Environment>
      <RotatingCake {...props} />
      <ContactShadows
        key={props.design.size}
        position={[0, shadowY, 0]}
        opacity={0.28}
        scale={4.2}
        blur={2.6}
        far={1.4}
        resolution={256}
        frames={1}
        color="#352B22"
      />
    </>
  );
}

// ─── Component chính ──────────────────────────────────────────────────────────
export default function Cake3D(props: Cake3DProps) {
  const fixedCamera = useFixedCamera();

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
        background: "radial-gradient(ellipse at 50% 36%, #FFFDF9 22%, #F4EDE2 72%, #E8DFD1 100%)",
        cursor: props.enableControls === false ? "default" : "grab",
      }}
    >
      <CanvasErrorBoundary
        message="Không hiển thị được mô hình 3D"
        detail="Bạn vẫn có thể tùy chỉnh bánh bằng các nút bên cạnh."
      >
        <Canvas
          camera={fixedCamera
            ? { position: fixedCamera, fov: 30 }
            : { position: [2.2, 2, 3.2] as [number, number, number], fov: 30 }}
          shadows="variance"
          dpr={[1, 1.5]}
          gl={{ antialias: true, alpha: true }}
          role="img"
          aria-label="Xem trước bánh kem 3D; dùng các nút tùy chỉnh để chọn vùng bánh"
          style={{ width:"100%", height:"100%" }}
        >
          <Suspense fallback={<CakeMesh {...props} />}>
            <Scene {...props} />
          </Suspense>
        </Canvas>
      </CanvasErrorBoundary>
    </div>
  );
}
