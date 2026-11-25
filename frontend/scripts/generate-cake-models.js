/**
 * Sinh "kho mẫu 3D" cho Bơ Nơ Bakery — KHÔNG cần tải model từ mạng.
 *
 * Chạy:  node scripts/generate-cake-models.js
 * Ra:    public/models/*.glb
 *
 * QUY ƯỚC ĐẶT TÊN (frontend dựa vào tên này để tô màu theo vùng):
 *   Body        - thân bánh
 *   Top         - mặt trên
 *   Border      - viền kem sò xoắn (mép trên & chân đế)
 *   Stand       - đĩa sứ cao cấp
 *   GoldRim     - viền vàng kim quanh đĩa
 *   Body_tier2  - thân tầng 2  (tầng 1 không có hậu tố)
 */

if (typeof globalThis.FileReader === "undefined") {
  globalThis.FileReader = class FileReader {
    readAsArrayBuffer(blob) {
      blob.arrayBuffer().then((buf) => {
        this.result = buf;
        if (typeof this.onloadend === "function") this.onloadend();
        if (typeof this.onload === "function") this.onload();
      });
    }
  };
}

const THREE = require("three");
const { GLTFExporter } = require("three/examples/jsm/exporters/GLTFExporter.js");
const { mergeGeometries } = require("three/examples/jsm/utils/BufferGeometryUtils.js");
const fs = require("fs");
const path = require("path");

// Bảng màu mặc định — tông kem bơ vani ấm + đĩa sứ viền vàng kim
const COLOR = {
  body: 0xfaf3e6,
  top: 0xfffdf8,
  border: 0xf5e6cc,
  stand: 0xf3ece0,
  gold: 0xd4a64e,
};

function mat(color, roughness = 0.4, clearcoat = 0.4, metalness = 0.0) {
  return new THREE.MeshPhysicalMaterial({
    color,
    roughness,
    metalness,
    clearcoat,
    clearcoatRoughness: 0.25,
  });
}

/** Tạo 1 múi kem bắt bông đui sao 8 khía (star-nozzle buttercream shell) */
function createPipedShellGeo(sx = 0.030, sy = 0.024, sz = 0.036, twist = 1.8) {
  const g = new THREE.SphereGeometry(1, 14, 10);
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z = pos.getZ(i);
    const angle = Math.atan2(z, x);
    const ridge = 1 + 0.17 * Math.cos(angle * 8 + (y + 1) * twist);
    const taper = 1 - Math.max(y, 0) * 0.38;
    const flattenBottom = y < -0.4 ? -0.4 + (y + 0.4) * 0.3 : y;
    pos.setXYZ(i, x * ridge * taper * sx, flattenBottom * sy, z * ridge * taper * sz);
  }
  g.computeVertexNormals();
  return g;
}

/** Viền kem sò xoắn chạy quanh hình tròn */
function pipedCircleRing(radius, y, scale = 1.0, count = 36, tilt = 0.24) {
  const parts = [];
  const baseShell = createPipedShellGeo(0.029 * scale, 0.024 * scale, 0.035 * scale, 2.0);
  const dummy = new THREE.Object3D();
  for (let i = 0; i < count; i++) {
    const a = (i / count) * Math.PI * 2;
    const g = baseShell.clone();
    dummy.position.set(Math.cos(a) * radius, y, Math.sin(a) * radius);
    dummy.rotation.set(tilt, -a, 0);
    dummy.updateMatrix();
    g.applyMatrix4(dummy.matrix);
    parts.push(g);
  }
  return mergeGeometries(parts, false);
}

/** Viền kem sò xoắn chạy dọc theo THREE.Shape 2D (bánh vuông bo góc & bánh trái tim) */
function pipedShapeRing(shape2D, y, scale = 1.0, count = 42, radialOffset = 1.0, tilt = 0.22) {
  const parts = [];
  const baseShell = createPipedShellGeo(0.028 * scale, 0.023 * scale, 0.034 * scale, 2.0);
  const pts = shape2D.getSpacedPoints(count);
  const dummy = new THREE.Object3D();
  for (let i = 0; i < count; i++) {
    const p = pts[i];
    const next = pts[(i + 1) % count];
    const x = p.x * radialOffset;
    const z = -p.y * radialOffset;
    const nx = next.x * radialOffset;
    const nz = -next.y * radialOffset;
    const tangentAngle = Math.atan2(nx - x, nz - z);

    const g = baseShell.clone();
    dummy.position.set(x, y, z);
    dummy.rotation.set(tilt, tangentAngle, 0);
    dummy.updateMatrix();
    g.applyMatrix4(dummy.matrix);
    parts.push(g);
  }
  return mergeGeometries(parts, false);
}

/** Mặt cắt dọc của lớp kem phủ: hơi vồng ở giữa rồi chảy nhẹ qua mép bánh. */
function frostingProfile(r, h) {
  return [
    new THREE.Vector2(0.0001, h + 0.052),
    new THREE.Vector2(r * 0.30, h + 0.046),
    new THREE.Vector2(r * 0.58, h + 0.034),
    new THREE.Vector2(r * 0.80, h + 0.020),
    new THREE.Vector2(r * 0.94, h + 0.008),
    new THREE.Vector2(r * 0.995, h - 0.002),
    new THREE.Vector2(r * 1.012, h - 0.016),
    new THREE.Vector2(r * 1.016, h - 0.038),
    new THREE.Vector2(r * 1.012, h - 0.058),
  ];
}

/** Đế bánh sứ cao cấp kèm chân đế thấp */
function luxuryPlateGeo(radius, y) {
  const topR = radius * 1.24;
  const botR = radius * 1.19;
  const mainPlate = new THREE.CylinderGeometry(topR, botR, 0.026, 64, 1);
  mainPlate.translate(0, y, 0);

  const foot = new THREE.CylinderGeometry(radius * 0.78, radius * 0.84, 0.016, 56, 1);
  foot.translate(0, y - 0.020, 0);

  return mergeGeometries([mainPlate, foot], false);
}

/** Viền vàng kim quanh đĩa bánh */
function plateGoldRimGeo(radius, y) {
  const rimR = radius * 1.235;
  const rim = new THREE.TorusGeometry(rimR, 0.007, 12, 80);
  rim.rotateX(Math.PI / 2);
  rim.translate(0, y + 0.007, 0);
  return rim;
}

/** Hình trái tim (mặt cắt ngang) để dựng bánh hình tim. */
function heartShape(scale) {
  const s = new THREE.Shape();
  const k = scale;
  s.moveTo(0, 0.30 * k);
  s.bezierCurveTo(0, 0.30 * k, -0.28 * k, 0.62 * k, -0.55 * k, 0.34 * k);
  s.bezierCurveTo(-0.86 * k, 0.02 * k, -0.38 * k, -0.42 * k, 0, -0.80 * k);
  s.bezierCurveTo(0.38 * k, -0.42 * k, 0.86 * k, 0.02 * k, 0.55 * k, 0.34 * k);
  s.bezierCurveTo(0.28 * k, 0.62 * k, 0, 0.30 * k, 0, 0.30 * k);
  return s;
}

/** Hình chữ nhật bo góc để dựng bánh vuông. */
function roundedRectShape(w, h, radius) {
  const s = new THREE.Shape();
  const x = -w / 2, y = -h / 2;
  s.moveTo(x + radius, y);
  s.lineTo(x + w - radius, y);
  s.quadraticCurveTo(x + w, y, x + w, y + radius);
  s.lineTo(x + w, y + h - radius);
  s.quadraticCurveTo(x + w, y + h, x + w - radius, y + h);
  s.lineTo(x + radius, y + h);
  s.quadraticCurveTo(x, y + h, x, y + h - radius);
  s.lineTo(x, y + radius);
  s.quadraticCurveTo(x, y, x + radius, y);
  return s;
}

/**
 * Dựng một chiếc bánh.
 * shape: "round" | "square" | "heart"
 * tiers: 1..3
 */
function buildCake({ shape = "round", tiers = 1, radius = 0.5, height = 0.30 }) {
  const root = new THREE.Group();
  root.name = "Cake";

  const bodyMat = mat(COLOR.body, 0.42, 0.28);
  const topMat = mat(COLOR.top, 0.32, 0.48);
  const borderMat = mat(COLOR.border, 0.36, 0.35);
  const standMat = mat(COLOR.stand, 0.25, 0.55);
  const goldMat = mat(COLOR.gold, 0.2, 0.7, 0.86);

  let y = 0;

  const standMesh = new THREE.Mesh(luxuryPlateGeo(radius, y - 0.012), standMat);
  standMesh.name = "Stand";
  root.add(standMesh);

  const goldRimMesh = new THREE.Mesh(plateGoldRimGeo(radius, y - 0.012), goldMat);
  goldRimMesh.name = "GoldRim";
  root.add(goldRimMesh);

  for (let t = 0; t < tiers; t++) {
    const r = radius * Math.pow(0.78, t);
    const h = height * (t === 0 ? 1 : 0.86);
    const suffix = t === 0 ? "" : `_tier${t + 1}`;
    const shellScale = Math.pow(0.88, t);

    // --- THÂN ---
    let bodyGeo;
    let baseShape2D = null;
    if (shape === "round") {
      bodyGeo = new THREE.CylinderGeometry(r, r * 0.996, h, 64, 1);
    } else if (shape === "square") {
      baseShape2D = roundedRectShape(r * 2, r * 2, r * 0.18);
      bodyGeo = new THREE.ExtrudeGeometry(baseShape2D, {
        depth: h, bevelEnabled: true, bevelSize: 0.01, bevelThickness: 0.01, bevelSegments: 4, curveSegments: 24,
      });
      bodyGeo.rotateX(-Math.PI / 2);
    } else {
      baseShape2D = heartShape(r * 1.35);
      bodyGeo = new THREE.ExtrudeGeometry(baseShape2D, {
        depth: h, bevelEnabled: true, bevelSize: 0.01, bevelThickness: 0.01, bevelSegments: 4, curveSegments: 24,
      });
      bodyGeo.rotateX(-Math.PI / 2);
    }
    bodyGeo.translate(0, y + (shape === "round" ? h / 2 : 0), 0);
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.name = `Body${suffix}`;
    root.add(body);

    // --- MẶT TRÊN (kem phủ ôm khít thân bánh, không phình như nắp hộp) ---
    let topGeo;
    if (shape === "round") {
      topGeo = new THREE.LatheGeometry(frostingProfile(r, h), 64);
      topGeo.translate(0, y, 0);
    } else {
      const shp = shape === "square"
        ? roundedRectShape(r * 2.01, r * 2.01, r * 0.18)
        : heartShape(r * 1.36);
      topGeo = new THREE.ExtrudeGeometry(shp, {
        depth: 0.022, bevelEnabled: true, bevelSize: 0.012, bevelThickness: 0.012, bevelSegments: 4, curveSegments: 24,
      });
      topGeo.rotateX(-Math.PI / 2);
      topGeo.translate(0, y + h - 0.002, 0);
    }
    const top = new THREE.Mesh(topGeo, topMat);
    top.name = `Top${suffix}`;
    root.add(top);

    // --- VIỀN KEM SÒ ĐUI SAO (cả viền mặt trên & viền chân đế bánh) ---
    let borderGeo;
    if (shape === "round") {
      const topRing = pipedCircleRing(r * 0.95, y + h + 0.020, shellScale * 0.92, Math.round(36 * shellScale), 0.22);
      const bottomRing = pipedCircleRing(r * 1.012, y + 0.018, shellScale * 0.85, Math.round(40 * shellScale), 0.30);
      borderGeo = mergeGeometries([topRing, bottomRing], false);
    } else if (shape === "square") {
      const topRing = pipedShapeRing(baseShape2D, y + h + 0.028, shellScale * 0.9, 40, 0.96, 0.2);
      const bottomRing = pipedShapeRing(baseShape2D, y + 0.018, shellScale * 0.84, 44, 1.015, 0.28);
      borderGeo = mergeGeometries([topRing, bottomRing], false);
    } else {
      const topRing = pipedShapeRing(baseShape2D, y + h + 0.028, shellScale * 0.88, 40, 0.95, 0.2);
      const bottomRing = pipedShapeRing(baseShape2D, y + 0.018, shellScale * 0.82, 44, 1.015, 0.28);
      borderGeo = mergeGeometries([topRing, bottomRing], false);
    }
    const border = new THREE.Mesh(borderGeo, borderMat);
    border.name = `Border${suffix}`;
    root.add(border);

    y += h + (t === 0 ? 0.012 : 0.01);
  }

  return root;
}

function exportGLB(object, outPath) {
  return new Promise((resolve, reject) => {
    new GLTFExporter().parse(
      object,
      (result) => {
        fs.mkdirSync(path.dirname(outPath), { recursive: true });
        fs.writeFileSync(outPath, Buffer.from(result));
        resolve(Buffer.from(result).length);
      },
      reject,
      { binary: true }
    );
  });
}

const DESIGNS = [
  { file: "cake-tron-1-tang.glb",  shape: "round",  tiers: 1, radius: 0.50, height: 0.34, label: "Tròn 1 tầng" },
  { file: "cake-tron-2-tang.glb",  shape: "round",  tiers: 2, radius: 0.52, height: 0.33, label: "Tròn 2 tầng" },
  { file: "cake-tron-3-tang.glb",  shape: "round",  tiers: 3, radius: 0.54, height: 0.32, label: "Tròn 3 tầng" },
  { file: "cake-vuong-1-tang.glb", shape: "square", tiers: 1, radius: 0.46, height: 0.32, label: "Vuông 1 tầng" },
  { file: "cake-trai-tim.glb",     shape: "heart",  tiers: 1, radius: 0.48, height: 0.32, label: "Trái tim" },
  { file: "cake-cao-1-tang.glb",   shape: "round",  tiers: 1, radius: 0.42, height: 0.50, label: "Tròn cao" },
];

(async () => {
  const outDir = path.join("public", "models");
  console.log("Sinh kho mau 3D ->", outDir, "\n");

  for (const d of DESIGNS) {
    const cake = buildCake(d);
    const fresh = path.join("public", "models", d.file);
    const size = await exportGLB(cake, fresh);

    const buf = fs.readFileSync(fresh);
    const jsonLen = buf.readUInt32LE(12);
    const json = JSON.parse(buf.subarray(20, 20 + jsonLen).toString("utf8"));
    const names = (json.nodes || []).map((n) => n.name).filter(Boolean);
    const tris = (json.meshes || []).reduce((s, m) =>
      s + (m.primitives || []).reduce((t, pr) => {
        const a = json.accessors[pr.indices];
        return t + (a ? a.count / 3 : 0);
      }, 0), 0);

    const zones = ["Body", "Top", "Border", "Stand", "GoldRim"].filter((z) =>
      names.some((n) => n === z || n.startsWith(z + "_"))
    );
    console.log(
      `  ${d.label.padEnd(14)} ${d.file.padEnd(24)} ${(size / 1024).toFixed(0).padStart(4)} KB  ` +
      `${Math.round(tris).toString().padStart(5)} tam giac  vung: ${zones.join("+")}`
    );
  }
  console.log("\nXong. Kiem tra: magic header phai la \"glTF\".");
})().catch((e) => { console.error("LOI:", e.message); process.exit(1); });
