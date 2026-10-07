/** Validate the shipped GLBs as the browser loader sees them. Run from frontend/. */
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const THREE = require("three");
const { GLTFLoader } = require("three/examples/jsm/loaders/GLTFLoader.js");

(async () => {
  for (const name of ["flower", "strawberry", "macaron", "candle"]) {
    const bytes = fs.readFileSync(path.join(__dirname, "..", "public", "models", "decorations", `${name}.glb`));
    assert.equal(bytes.toString("ascii", 0, 4), "glTF", `${name}: GLB header`);
    assert.equal(bytes.readUInt32LE(4), 2, `${name}: GLB version`);
    assert.equal(bytes.readUInt32LE(8), bytes.length, `${name}: file length`);
    assert.ok(bytes.length < 2_000_000, `${name}: mobile download budget`);
    const json = JSON.parse(bytes.toString("utf8", 20, 20 + bytes.readUInt32LE(12)));
    assert.ok(!(json.extensionsRequired ?? []).some(x => /draco|meshopt/i.test(x)), `${name}: unexpected decoder`);
    const arrayBuffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
    const gltf = await new Promise((resolve, reject) => new GLTFLoader().parse(arrayBuffer, "", resolve, reject));
    let triangles = 0, meshes = 0;
    gltf.scene.traverse(object => {
      if (!object.isMesh) return;
      meshes++;
      const geometry = object.geometry;
      for (const attribute of Object.values(geometry.attributes)) {
        assert.ok(Array.from(attribute.array).every(Number.isFinite), `${name}: non-finite geometry`);
      }
      const positions = geometry.attributes.position;
      if (geometry.index) assert.ok(Array.from(geometry.index.array).every(i => i < positions.count), `${name}: invalid index`);
      triangles += (geometry.index?.count ?? positions.count) / 3;
      const normal = geometry.attributes.normal;
      for (let i = 0; i < normal.count; i++) {
        assert.ok(Math.abs(Math.hypot(normal.getX(i), normal.getY(i), normal.getZ(i)) - 1) < 0.001, `${name}: invalid normal`);
      }
    });
    const bounds = new THREE.Box3().setFromObject(gltf.scene);
    const size = bounds.getSize(new THREE.Vector3());
    assert.ok(Math.abs(bounds.min.y) < 0.00001, `${name}: pivot must touch icing`);
    assert.ok(size.x > 0.01 && size.y > 0.01 && size.z > 0.01, `${name}: collapsed geometry`);
    assert.ok(triangles < 25_000 && meshes <= 10, `${name}: rendering budget exceeded`);
    console.log(`${name}: ${meshes} meshes, ${triangles} triangles, ${Math.round(bytes.length / 1024)} KiB, ground pivot OK`);
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
