import * as THREE from "three";

export interface CakeDecorationTier {
  radius: number;
  height: number;
  bodyY: number;
  borderY: number;
  surfaceY: number;
  icingBottom: number;
  bodyPath: THREE.CurvePath<THREE.Vector3>;
  borderPath: THREE.CurvePath<THREE.Vector3>;
  edgeAt: (t: number) => THREE.Vector2;
  surfaceAt: (x: number, z: number) => number;
}

function closedPath(points: THREE.Vector3[]) {
  const path = new THREE.CurvePath<THREE.Vector3>();
  points.forEach((point, i) => path.add(new THREE.LineCurve3(point, points[(i + 1) % points.length])));
  return path;
}

/** Coordinates stay local to the cake, independent of its rotating scene parent. */
function detached(mesh: THREE.Mesh) {
  const result = new THREE.Mesh(mesh.geometry, mesh.material);
  result.matrixWorld.copy(mesh.matrixWorld);
  return result;
}

// The current round, heart and rounded-rectangle assets are star-shaped around
// their modelling origin. Cast from outside so concave heart notches are kept.
function outline(mesh: THREE.Mesh, y: number, reach: number) {
  const ray = new THREE.Raycaster();
  return closedPath(Array.from({ length: 192 }, (_, i) => {
    const angle = i / 192 * Math.PI * 2;
    const direction = new THREE.Vector3(Math.cos(angle), 0, Math.sin(angle));
    ray.set(direction.clone().multiplyScalar(reach).setY(y), direction.clone().negate());
    const hit = ray.intersectObject(mesh, false)[0];
    if (!hit) throw new Error(`Cannot measure cake outline at ${i}`);
    return hit.point.clone().setY(0);
  }));
}

export function measureDecorationTier(body: THREE.Mesh, top: THREE.Mesh): CakeDecorationTier {
  const bodyBounds = new THREE.Box3().setFromObject(body);
  const topBounds = new THREE.Box3().setFromObject(top);
  const dimensions = bodyBounds.getSize(new THREE.Vector3());
  const bodyY = (bodyBounds.min.y + bodyBounds.max.y) / 2;
  const surface = detached(top);
  const reach = Math.max(dimensions.x, dimensions.z) * 2;
  const topPath = outline(surface, topBounds.min.y + (topBounds.max.y - topBounds.min.y) * 0.25, reach);
  const bodyPath = outline(detached(body), bodyY, reach);
  const ray = new THREE.Raycaster();
  const surfaceAt = (x: number, z: number) => {
    ray.set(new THREE.Vector3(x, topBounds.max.y + 1, z), new THREE.Vector3(0, -1, 0));
    return ray.intersectObject(surface, false)[0]?.point.y ?? topBounds.max.y;
  };
  const edgeAt = (t: number) => {
    const point = topPath.getPointAt(((t % 1) + 1) % 1);
    return new THREE.Vector2(point.x, point.z);
  };
  const borderPath = closedPath(Array.from({ length: 192 }, (_, i) => {
    const p = edgeAt(i / 192).multiplyScalar(0.96);
    return new THREE.Vector3(p.x, surfaceAt(p.x, p.y) + 0.025, p.y);
  }));
  return {
    radius: Math.min(dimensions.x, dimensions.z) / 2, height: dimensions.y,
    bodyY, borderY: bodyBounds.max.y, surfaceY: topBounds.max.y,
    icingBottom: topBounds.min.y, bodyPath, borderPath, edgeAt, surfaceAt,
  };
}

/** A thin glaze follows the sloped icing instead of floating at its peak height. */
export function createGanacheGeometry(tier: Pick<CakeDecorationTier, "edgeAt" | "surfaceAt" | "height">) {
  const segments = 288;
  const topRows = 8;
  const stride = topRows + 2;
  const positions: number[] = [], indices: number[] = [];
  for (let i = 0; i <= segments; i++) {
    const t = i / segments;
    const edge = tier.edgeAt(t);
    const rim = edge.clone().multiplyScalar(0.998);
    const rimY = tier.surfaceAt(rim.x, rim.y);
    const phase = (((t * 15 + 0.5) % 1) - 0.5) * 2;
    const drip = Math.sqrt(Math.max(0, 1 - Math.pow(phase / 0.44, 2)));
    const length = Math.min(tier.height * 0.5, 0.035 + drip * (0.09 + 0.075 * (Math.sin(t * Math.PI * 8 + 1) + 1) / 2));
    // Follow the rounded shoulder too: a single straight quad cuts through
    // the icing between the inner and outer rim, exposing a white ring.
    for (let row = 0; row < topRows; row++) {
      const p = edge.clone().multiplyScalar(0.86 + (0.998 - 0.86) * row / (topRows - 1));
      positions.push(p.x, tier.surfaceAt(p.x, p.y) + 0.005, p.y);
    }
    positions.push(edge.x * 1.008, rimY + 0.002, edge.y * 1.008,
      edge.x * 1.008, rimY - length, edge.y * 1.008);
    if (i < segments) for (let row = 0; row < stride - 1; row++) {
      const a = i * stride + row, b = a + stride;
      indices.push(a, a + 1, b, a + 1, b + 1, b);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}
