/**
 * Sinh "kho mẫu 3D" cho Bơ Nơ Bakery — KHÔNG cần tải model từ mạng.
 *
 * Chạy:  node scripts/generate-cake-models.js
 * Ra:    public/models/*.glb
 *
 * Vì sao tự sinh thay vì tải model CC0?
 *   1. Model tải về là MỘT KHỐI LIỀN -> không tô màu theo vùng được -> phá tính năng
 *      "thiết kế bánh trực quan theo vùng" của đề tài.
 *   2. Model tự sinh có các phần ĐẶT TÊN TÁCH RỜI: Body / Top / Border.
 *      Nhờ vậy trình cấu hình hiện có vẫn đổi màu từng vùng như cũ.
 *   3. Không vướng giấy phép, dung lượng nhỏ (mỗi file vài chục KB).
 *
 * QUY ƯỚC ĐẶT TÊN (frontend dựa vào tên này để tô màu theo vùng):
 *   Body        - thân bánh
 *   Top         - mặt trên
 *   Border      - viền kem
 *   Body_tier2  - thân tầng 2  (tầng 1 không có hậu tố)
 */

// GLTFExporter viết cho trình duyệt: nó dùng FileReader để đọc Blob.
// Node không có FileReader nên ta tự cấp một bản tối thiểu.
// Thứ tự trong three.js: readAsArrayBuffer() gọi TRƯỚC khi gán onloadend,
// nên phải trả kết quả bất đồng bộ.
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

// Bảng màu mặc định — tông kem/trắng ấm, KHÔNG dùng màu cam san hô.
const COLOR = {
  body: 0xf3ece1,
  top: 0xfdfbf7,
  border: 0xf8f3ea,
  stand: 0xe8e5e0,
};

function mat(color, roughness = 0.42, clearcoat = 0.5) {
  return new THREE.MeshPhysicalMaterial({
    color,
    roughness,
    metalness: 0.0,
    clearcoat,
    clearcoatRoughness: 0.28,
  });
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
    new THREE.Vector2(r * 1.018, h - 0.016),
    new THREE.Vector2(r * 1.024, h - 0.042),
    new THREE.Vector2(r * 1.020, h - 0.068),
  ];
}

/** Viền kem: một vòng búi kem nhỏ, gộp thành 1 mesh để file gọn. */
function rosetteRing(radius, y, bead = 0.042, count = 18) {
  const parts = [];
  for (let i = 0; i < count; i++) {
    const a = (i / count) * Math.PI * 2;
    const g = new THREE.SphereGeometry(bead, 10, 8);
    g.scale(1, 0.82, 1);
    g.translate(Math.cos(a) * radius, y, Math.sin(a) * radius);
    parts.push(g);
  }
  return mergeGeometries(parts, false);
}

/** Đế bánh tròn, dẹt. */
function plate(radius, y) {
  const g = new THREE.CylinderGeometry(radius * 1.22, radius * 1.16, 0.022, 56, 1);
  g.translate(0, y, 0);
  return g;
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

  const bodyMat = mat(COLOR.body, 0.46, 0.45);
  const topMat = mat(COLOR.top, 0.30, 0.75);
  const borderMat = mat(COLOR.border, 0.34, 0.6);

  let y = 0;

  root.add(new THREE.Mesh(plate(radius, y - 0.012), mat(COLOR.stand, 0.35, 0.3)));
  y += 0.0;

  for (let t = 0; t < tiers; t++) {
    const r = radius * Math.pow(0.78, t);
    const h = height * (t === 0 ? 1 : 0.86);
    const suffix = t === 0 ? "" : `_tier${t + 1}`;

    // --- THÂN ---
    let bodyGeo;
    if (shape === "round") {
      bodyGeo = new THREE.CylinderGeometry(r, r * 0.995, h, 56, 1);
    } else if (shape === "square") {
      bodyGeo = new THREE.ExtrudeGeometry(roundedRectShape(r * 2, r * 2, r * 0.16), {
        depth: h, bevelEnabled: true, bevelSize: 0.008, bevelThickness: 0.008, bevelSegments: 2, curveSegments: 16,
      });
      bodyGeo.rotateX(-Math.PI / 2);
    } else {
      bodyGeo = new THREE.ExtrudeGeometry(heartShape(r * 1.35), {
        depth: h, bevelEnabled: true, bevelSize: 0.008, bevelThickness: 0.008, bevelSegments: 2, curveSegments: 10,
      });
      bodyGeo.rotateX(-Math.PI / 2);
    }
    bodyGeo.translate(0, y + (shape === "round" ? h / 2 : 0), 0);
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.name = `Body${suffix}`;
    root.add(body);

    // --- MẶT TRÊN (kem phủ) ---
    let topGeo;
    if (shape === "round") {
      topGeo = new THREE.LatheGeometry(frostingProfile(r, h), 56);
      topGeo.translate(0, y, 0);
    } else {
      const shp = shape === "square"
        ? roundedRectShape(r * 2.08, r * 2.08, r * 0.17)
        : heartShape(r * 1.42);
      topGeo = new THREE.ExtrudeGeometry(shp, {
        depth: 0.035, bevelEnabled: true, bevelSize: 0.012, bevelThickness: 0.012, bevelSegments: 3, curveSegments: 16,
      });
      topGeo.rotateX(-Math.PI / 2);
      topGeo.translate(0, y + h + 0.035, 0);
    }
    const top = new THREE.Mesh(topGeo, topMat);
    top.name = `Top${suffix}`;
    root.add(top);

    // --- VIỀN KEM ---
    let borderGeo;
    if (shape === "round") {
      borderGeo = rosetteRing(r * 1.0, y + h - 0.03, 0.040 * Math.pow(0.88, t), 18);
    } else if (shape === "square") {
      const parts = [];
      const half = r * 0.99;
      const per = 6;
      for (let i = 0; i < per; i++) {
        const p = -half + (i / (per - 1)) * half * 2;
        for (const [dx, dz] of [[p, -half], [p, half], [-half, p], [half, p]]) {
          const g = new THREE.SphereGeometry(0.036, 10, 8);
          g.scale(1, 0.82, 1);
          g.translate(dx, y + h - 0.028, dz);
          parts.push(g);
        }
      }
      borderGeo = mergeGeometries(parts, false);
    } else {
      const parts = [];
      const shp = heartShape(r * 1.30);
      const pts = shp.getPoints(26);
      for (const p of pts) {
        const g = new THREE.SphereGeometry(0.034, 10, 8);
        g.scale(1, 0.82, 1);
        g.translate(p.x, y + h - 0.026, -p.y);
        parts.push(g);
      }
      borderGeo = mergeGeometries(parts, false);
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

    // Đọc lại để đếm tam giác + liệt kê tên vùng
    const buf = fs.readFileSync(fresh);
    const jsonLen = buf.readUInt32LE(12);
    const json = JSON.parse(buf.subarray(20, 20 + jsonLen).toString("utf8"));
    const names = (json.nodes || []).map((n) => n.name).filter(Boolean);
    const tris = (json.meshes || []).reduce((s, m) =>
      s + (m.primitives || []).reduce((t, pr) => {
        const a = json.accessors[pr.indices];
        return t + (a ? a.count / 3 : 0);
      }, 0), 0);

    const zones = ["Body", "Top", "Border"].filter((z) => names.some((n) => n === z || n.startsWith(z + "_")));
    console.log(
      `  ${d.label.padEnd(14)} ${d.file.padEnd(24)} ${(size / 1024).toFixed(0).padStart(4)} KB  ` +
      `${Math.round(tris).toString().padStart(5)} tam giac  vung: ${zones.join("+")}`
    );
  }
  console.log("\nXong. Kiem tra: magic header phai la \"glTF\".");
})().catch((e) => { console.error("LOI:", e.message); process.exit(1); });
