"use client";

import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { createGanacheGeometry, type CakeDecorationTier } from "./cake-decoration-surface";

/** A closed, rounded profile: soft icing edges without changing cake dimensions. */
export function RoundedCylinder({ radius, height, bevel = 0.035, roundTop = true, roundBottom = true, capTop = true, capBottom = true }: {
  radius: number; height: number; bevel?: number; roundTop?: boolean; roundBottom?: boolean;
  capTop?: boolean; capBottom?: boolean;
}) {
  const points = useMemo(() => {
    const b = Math.min(bevel, height / 2);
    const half = height / 2;
    const bottom = roundBottom ? b : 0;
    const top = roundTop ? b : 0;
    const profile = capBottom ? [new THREE.Vector2(0, -half)] : [];
    profile.push(new THREE.Vector2(radius - bottom, -half));
    if (roundBottom) {
      for (let i = 1; i <= 8; i++) {
        const a = -Math.PI / 2 + i * Math.PI / 16;
        profile.push(new THREE.Vector2(radius - bottom + bottom * Math.cos(a), -half + bottom + bottom * Math.sin(a)));
      }
    }
    profile.push(new THREE.Vector2(radius, half - top));
    if (roundTop) {
      for (let i = 1; i <= 8; i++) {
        const a = i * Math.PI / 16;
        profile.push(new THREE.Vector2(radius - top + top * Math.cos(a), half - top + top * Math.sin(a)));
      }
    }
    if (capTop) profile.push(new THREE.Vector2(0, half));
    return profile;
  }, [radius, height, bevel, roundTop, roundBottom, capTop, capBottom]);
  return <latheGeometry args={[points, 96]} />;
}

/** Local, deterministic microtexture; no image request or external texture license. */
export function useIcingTexture() {
  const texture = useMemo(() => {
    const size = 128;
    const pixels = new Uint8Array(size * size * 4);
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const noise = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
        const grain = noise - Math.floor(noise);
        const stroke = Math.sin(y * 0.68 + Math.sin(x * 0.049) * 0.55);
        const value = Math.round(128 + stroke * 12 + (grain - 0.5) * 18);
        const index = (y * size + x) * 4;
        pixels.set([value, value, value, 255], index);
      }
    }
    const map = new THREE.DataTexture(pixels, size, size, THREE.RGBAFormat);
    map.wrapS = map.wrapT = THREE.RepeatWrapping;
    map.magFilter = THREE.LinearFilter;
    map.minFilter = THREE.LinearMipmapLinearFilter;
    map.generateMipmaps = true;
    map.needsUpdate = true;
    return map;
  }, []);
  useEffect(() => () => texture.dispose(), [texture]);
  return texture;
}

/** Star-nozzle buttercream shells, rendered in one instanced draw call. */
export function PipedBorder({ radius, y, color, rosettes = false, path }: {
  radius: number; y: number; color: string; rosettes?: boolean; path?: THREE.Curve<THREE.Vector3>;
}) {
  const count = Math.max(3, Math.round((path?.getLength() ?? Math.PI * 2 * radius) / (rosettes ? 0.18 : 0.105)));
  const ref = useRef<THREE.InstancedMesh>(null);
  const geometry = useMemo(() => {
    const shape = new THREE.SphereGeometry(1, 24, 16);
    const vertices = shape.attributes.position;
    for (let i = 0; i < vertices.count; i++) {
      const x = vertices.getX(i), z = vertices.getZ(i), h = vertices.getY(i);
      const angle = Math.atan2(z, x);
      const ridge = 1 + 0.16 * Math.cos(angle * 8 + (h + 1) * (rosettes ? 3 : 0.65));
      const taper = 1 - Math.max(h, 0) * 0.38;
      vertices.setXYZ(i, x * ridge * taper, h, z * ridge * taper);
    }
    shape.computeVertexNormals();
    return shape;
  }, [rosettes]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  useLayoutEffect(() => {
    if (!ref.current) return;
    const transform = new THREE.Object3D();
    for (let i = 0; i < count; i++) {
      const a = i / count * Math.PI * 2;
      transform.position.set(Math.cos(a) * radius, y, Math.sin(a) * radius);
      transform.rotation.set(0, -a, rosettes ? 0 : 0.35);
      if (path) {
        transform.position.copy(path.getPointAt(i / count));
        const tangent = path.getTangentAt(i / count);
        transform.rotation.y = Math.atan2(-tangent.x, tangent.z);
      }
      transform.scale.set(rosettes ? 0.1 : 0.064, rosettes ? 0.085 : 0.045, rosettes ? 0.1 : 0.052);
      transform.updateMatrix();
      ref.current.setMatrixAt(i, transform.matrix);
    }
    ref.current.instanceMatrix.needsUpdate = true;
    ref.current.computeBoundingSphere();
  }, [count, radius, y, rosettes, path]);
  return (
    <instancedMesh ref={ref} args={[geometry, undefined, count]} castShadow receiveShadow>
      <meshPhysicalMaterial color={color} roughness={0.57} metalness={0} clearcoat={0.12} />
    </instancedMesh>
  );
}

/** Ganache hangs over the rim, with rounded drops of alternating lengths. */
export function Ganache({ radius, surfaceY, tier }: { radius: number; surfaceY: number; tier?: CakeDecorationTier }) {
  const geometry = useMemo(() => {
    if (tier) return createGanacheGeometry(tier);
    const segments = 360;
    const positions: number[] = [], indices: number[] = [];
    for (let i = 0; i <= segments; i++) {
      const angle = i / segments * Math.PI * 2;
      const phase = (((i / segments * 15 + 0.5) % 1) - 0.5) * 2;
      const drip = Math.sqrt(Math.max(0, 1 - Math.pow(phase / 0.44, 2)));
      const length = 0.035 + drip * (0.09 + 0.075 * (Math.sin(angle * 4 + 1) + 1) / 2);
      for (const [r, y] of [[radius - 0.07, surfaceY + 0.011], [radius - 0.008, surfaceY + 0.01], [radius + 0.008, surfaceY - 0.02], [radius + 0.009, surfaceY - length]]) {
        positions.push(Math.cos(angle) * r, y, Math.sin(angle) * r);
      }
      if (i < segments) {
        for (let row = 0; row < 3; row++) {
          const a = i * 4 + row, b = a + 4;
          indices.push(a, a + 1, b, a + 1, b + 1, b);
        }
      }
    }
    const result = new THREE.BufferGeometry();
    result.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    result.setIndex(indices);
    result.computeVertexNormals();
    return result;
  }, [radius, surfaceY, tier]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return <mesh geometry={geometry} castShadow receiveShadow>
    <meshPhysicalMaterial color="#42261E" roughness={0.3} clearcoat={0.5} side={THREE.DoubleSide} />
  </mesh>;
}
