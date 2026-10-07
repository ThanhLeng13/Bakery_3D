/**
 * Original decoration assets for the Cake Builder. No downloaded model or texture.
 * Run from frontend/: node scripts/generate-decoration-models.js
 * The models have a ground-level origin so they can be placed on any cake top.
 */

if (typeof globalThis.FileReader === "undefined") {
  globalThis.FileReader = class FileReader {
    readAsArrayBuffer(blob) {
      blob.arrayBuffer().then((buffer) => {
        this.result = buffer;
        this.onloadend?.();
      });
    }
  };
}

const THREE = require("three");
const { GLTFExporter } = require("three/examples/jsm/exporters/GLTFExporter.js");
const { mergeGeometries } = require("three/examples/jsm/utils/BufferGeometryUtils.js");
const fs = require("fs");
const path = require("path");

const outputDir = path.join(__dirname, "..", "public", "models", "decorations");

function material(color, roughness = 0.55, clearcoat = 0.08) {
  return new THREE.MeshPhysicalMaterial({
    color,
    roughness,
    metalness: 0,
    clearcoat,
    clearcoatRoughness: 0.38,
  });
}

function ellipsoid(parent, name, color, position, scale, rotation = [0, 0, 0], roughness = 0.55, segments = [18, 12]) {
  const mesh = new THREE.Mesh(
    new THREE.SphereGeometry(1, ...segments),
    material(color, roughness),
  );
  mesh.name = name;
  mesh.position.set(...position);
  mesh.scale.set(...scale);
  mesh.rotation.set(...rotation);
  parent.add(mesh);
  return mesh;
}

/** A sampled surface with UVs, so thin petals can be merged with other meshes. */
function surface(columns, rows, sample) {
  const positions = [], uvs = [], indices = [];
  for (let row = 0; row <= rows; row++) {
    for (let column = 0; column <= columns; column++) {
      const u = column / columns, v = row / rows;
      positions.push(...sample(u, v));
      uvs.push(u, v);
      if (row < rows && column < columns) {
        const a = row * (columns + 1) + column, b = a + columns + 1;
        indices.push(a, b, a + 1, a + 1, b, b + 1);
      }
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function leaf(parent, name, angle, y, length, width, color, offset = 0) {
  const geometry = surface(6, 12, (u, t) => {
    const across = u * 2 - 1;
    const edge = Math.sin(Math.PI * t) * (1 + 0.08 * Math.sin(t * Math.PI * 12));
    const x = across * width * edge;
    const z = offset + t * length;
    const height = y + Math.sin(t * Math.PI) * 0.008 - t * t * 0.009
      + (1 - Math.abs(across)) * Math.sin(Math.PI * t) * 0.003;
    return [Math.sin(angle) * z + Math.cos(angle) * x, height, Math.cos(angle) * z - Math.sin(angle) * x];
  });
  const finish = material(color, 0.74, 0);
  finish.side = THREE.DoubleSide;
  const mesh = new THREE.Mesh(geometry, finish);
  mesh.name = name;
  parent.add(mesh);
}

function flower() {
  const root = new THREE.Group();
  root.name = "Flower";
  const colors = [0xe2adb9, 0xeabbc5, 0xf0ccd3];
  // Each petal is a cupped sheet with a flared, gently rolled lip.
  // Staggering the rings creates a rose centre rather than a daisy-shaped disk.
  const rings = [
    { count: 3, base: 0.009, radius: 0.029, height: 0.151 },
    { count: 5, base: 0.015, radius: 0.059, height: 0.143 },
    { count: 7, base: 0.024, radius: 0.095, height: 0.131 },
    { count: 9, base: 0.037, radius: 0.131, height: 0.11 },
    { count: 10, base: 0.054, radius: 0.158, height: 0.084 },
  ];
  rings.forEach((ring, layer) => {
    for (let i = 0; i < ring.count; i++) {
      const angle = i / ring.count * Math.PI * 2 + layer * 0.59;
      const halfSpan = Math.PI / ring.count * 1.45;
      const geometry = surface(14, 10, (u, v) => {
        const across = u * 2 - 1;
        const theta = angle + across * halfSpan * (0.42 + 0.58 * v);
        const radius = ring.base + (ring.radius - ring.base) * Math.pow(v, 0.82)
          + 0.007 * Math.pow(v, 7);
        const height = 0.009 + ring.height * Math.sin(v * Math.PI / 2)
          * (1 - 0.23 * across * across) - 0.013 * Math.pow(v, 8)
          + Math.sin(u * Math.PI * 3 + i) * 0.0015 * v;
        return [Math.cos(theta) * radius, height, Math.sin(theta) * radius];
      });
      const finish = material(colors[Math.min(2, Math.floor(layer / 2))], 0.55, 0.08);
      finish.side = THREE.DoubleSide;
      const petal = new THREE.Mesh(geometry, finish);
      petal.name = `Petal_${layer}_${i}`;
      root.add(petal);
    }
  });
  ellipsoid(root, "RoseBud", 0xe2adb9, [0, 0.089, 0], [0.016, 0.059, 0.016], [0, 0, 0], 0.57);
  leaf(root, "ButtercreamLeaf_1", 0.85, 0.008, 0.13, 0.033, 0x81916c, 0.064);
  leaf(root, "ButtercreamLeaf_2", 3.8, 0.01, 0.1, 0.03, 0x81916c, 0.075);
  return root;
}

function strawberry() {
  const root = new THREE.Group();
  root.name = "Strawberry";
  const height = 0.226;
  const radiusAt = (t) => 0.092 * Math.pow(Math.max(0, Math.sin(Math.PI * t)), 0.72) * (0.64 + 0.5 * t);
  const seeds = [];
  for (let ring = 0; ring < 7; ring++) {
    const t = 0.16 + ring * 0.108;
    const radius = radiusAt(t);
    const count = Math.round(radius * 145);
    for (let i = 0; i < count; i++) {
      seeds.push({ t, angle: (i + (ring % 2) * 0.5) / count * Math.PI * 2, radius });
    }
  }
  const geometry = surface(56, 44, (u, t) => {
    const angle = u * Math.PI * 2;
    let radius = radiusAt(t);
    for (const seed of seeds) {
      const arc = Math.atan2(Math.sin(angle - seed.angle), Math.cos(angle - seed.angle)) * seed.radius;
      const dy = (t - seed.t) * height;
      radius -= 0.0016 * Math.exp(-(arc * arc / 0.000027 + dy * dy / 0.000045));
    }
    return [Math.cos(angle) * radius, t * height, Math.sin(angle) * radius];
  });
  // Paint subtle red variation into vertices, not a photograph wrapped around the fruit.
  const colors = [], red = new THREE.Color(0xc93646), dark = new THREE.Color(0x9f1e2e);
  const positions = geometry.attributes.position;
  for (let i = 0; i < positions.count; i++) {
    const t = positions.getY(i) / height;
    const angle = Math.atan2(positions.getZ(i), positions.getX(i));
    const color = red.clone().lerp(dark, 0.16 + 0.18 * Math.sin(angle * 3 + t * 9) ** 2);
    colors.push(color.r, color.g, color.b);
  }
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  const fleshMaterial = material(0xffffff, 0.35, 0.25);
  fleshMaterial.vertexColors = true;
  const flesh = new THREE.Mesh(geometry, fleshMaterial);
  flesh.name = "Fruit";
  root.add(flesh);
  seeds.forEach(({ t, angle, radius }, i) => {
    ellipsoid(root, `Seed_${i}`, 0xd7ac68,
      [Math.cos(angle) * (radius - 0.0008), t * height, Math.sin(angle) * (radius - 0.0008)],
      [0.0016, 0.0038, 0.0011], [0, Math.PI / 2 - angle, -0.1], 0.65, [8, 6]);
  });
  for (let i = 0; i < 6; i++) {
    leaf(root, `Calyx_${i}`, i / 6 * Math.PI * 2, height - 0.015, 0.063, 0.013, i % 2 ? 0x496e3d : 0x5e814c, 0.004);
  }
  ellipsoid(root, "Stem", 0x526c3c, [0, height + 0.002, 0], [0.005, 0.021, 0.005], [0, 0, 0.26], 0.8, [8, 6]);
  return root;
}

function macaron() {
  const root = new THREE.Group();
  root.name = "Macaron";
  const profile = [[0, 0.151], [0.04, 0.15], [0.083, 0.142], [0.108, 0.126], [0.12, 0.11], [0.119, 0.098], [0.11, 0.094], [0, 0.094]];
  const curve = new THREE.CatmullRomCurve3(profile.map(([r, y]) => new THREE.Vector3(r, y, 0)));
  const points = curve.getPoints(40).reverse().map(p => new THREE.Vector2(Math.max(0, p.x), p.y));
  for (const top of [true, false]) {
    const geometry = new THREE.LatheGeometry(points, 48);
    if (!top) { geometry.rotateX(Math.PI); geometry.translate(0, 0.156, 0); }
    const shell = new THREE.Mesh(geometry, material(0xd9abb9, 0.67, 0.035));
    shell.name = top ? "TopShell" : "BottomShell";
    root.add(shell);
  }
  ellipsoid(root, "VanillaFilling", 0xf8efdf, [0, 0.078, 0], [0.114, 0.02, 0.114], [0, 0, 0], 0.62);
  for (const [layer, y] of [["Bottom", 0.052], ["Top", 0.087]]) {
    const geometry = surface(120, 5, (u, v) => {
      const a = u * Math.PI * 2;
      const grain = Math.sin(a * 47 + v * 8) * Math.sin(a * 31 - v * 6);
      const r = 0.113 + 0.004 * Math.sin(v * Math.PI) + 0.0026 * grain;
      return [Math.cos(a) * r, y + v * 0.018 + 0.0015 * Math.sin(a * 39), Math.sin(a) * r];
    });
    const feet = new THREE.Mesh(geometry, material(0xc998a8, 0.81, 0));
    feet.name = `${layer}RuffledFeet`;
    root.add(feet);
  }
  return root;
}

function candle() {
  const root = new THREE.Group();
  root.name = "Candle";
  const wax = new THREE.Mesh(
    new THREE.CylinderGeometry(0.024, 0.024, 0.26, 20),
    material(0xf0efeb, 0.53),
  );
  wax.name = "Wax";
  wax.position.y = 0.13;
  root.add(wax);

  for (let i = 0; i < 4; i++) {
    const band = new THREE.Mesh(
      new THREE.TorusGeometry(0.0245, 0.003, 6, 24),
      material(0x8f8f8e, 0.5),
    );
    band.name = `Band_${i}`;
    band.position.y = 0.052 + i * 0.053;
    band.rotation.x = Math.PI / 2;
    root.add(band);
  }
  const wick = new THREE.Mesh(
    new THREE.CylinderGeometry(0.003, 0.003, 0.028, 8),
    material(0x2b2b2a, 0.9),
  );
  wick.name = "Wick";
  wick.position.y = 0.273;
  root.add(wick);
  ellipsoid(root, "Flame", 0xf7c77a, [0, 0.317, 0], [0.018, 0.045, 0.018], [0, 0, 0], 0.3);
  return root;
}

function mergeByMaterial(root) {
  const groups = new Map();
  for (const mesh of root.children) {
    mesh.updateMatrix();
    const material = mesh.material;
    const key = [material.color.getHex(), material.roughness, material.clearcoat, material.side, material.vertexColors].join(":");
    if (!groups.has(key)) groups.set(key, { material, geometries: [] });
    groups.get(key).geometries.push(mesh.geometry.clone().applyMatrix4(mesh.matrix));
  }

  root.clear();
  for (const [index, { material, geometries }] of [...groups.values()].entries()) {
    const geometry = mergeGeometries(geometries, false);
    if (!geometry) throw new Error(`Could not merge ${root.name} material group ${index}`);
    if (root.name === "Strawberry") geometry.rotateZ(0.72);
    const normals = geometry.attributes.normal;
    for (let i = 0; i < normals.count; i++) {
      const normal = new THREE.Vector3().fromBufferAttribute(normals, i);
      if (normal.lengthSq() < 1e-10) normal.set(0, 1, 0);
      normal.normalize();
      normals.setXYZ(i, normal.x, normal.y, normal.z);
    }
    const mesh = new THREE.Mesh(geometry, material);
    mesh.name = `${root.name}_part_${index}`;
    root.add(mesh);
  }
  // Every variant sits on the icing, including thin rose leaves and curved shells.
  const bounds = new THREE.Box3().setFromObject(root);
  const center = bounds.getCenter(new THREE.Vector3());
  for (const mesh of root.children) mesh.geometry.translate(-center.x, -bounds.min.y, -center.z);
  root.userData = { author: "Bơ Nơ Bakery", source: "Original procedural model", groundPivot: true };
  return root;
}

function exportGLB(name, object) {
  return new Promise((resolve, reject) => {
    new GLTFExporter().parse(
      mergeByMaterial(object),
      (result) => {
        const filePath = path.join(outputDir, `${name}.glb`);
        fs.writeFileSync(filePath, Buffer.from(result));
        resolve({ name, bytes: Buffer.byteLength(Buffer.from(result)) });
      },
      reject,
      { binary: true },
    );
  });
}

(async () => {
  fs.mkdirSync(outputDir, { recursive: true });
  for (const [name, build] of [
    ["flower", flower],
    ["strawberry", strawberry],
    ["macaron", macaron],
    ["candle", candle],
  ]) {
    const asset = await exportGLB(name, build());
    console.log(`${asset.name}.glb: ${asset.bytes} bytes`);
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
