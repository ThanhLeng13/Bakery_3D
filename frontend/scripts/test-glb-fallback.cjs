// Regression: a slow or failed GLB fetch must not leave a blank canvas.
//
// Cake3D wrapped <Scene> in <Suspense fallback={null}>. Scene suspends while
// the body .glb downloads, so on a slow connection the canvas rendered nothing:
// an empty white box with no cake and no explanation. The inner body already
// had a procedural fallback (<CakeMesh>), but the outer Suspense shadowed it.
//
// Same shape in CakeViewer3D: PreviewFallbackBoundary returned null, so a
// product whose model 404'd showed nothing at all.
//
// These assertions read the source because the failure is "what is absent from
// the tree", which a rendering test can only confirm by rendering WebGL.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const read = name => fs.readFileSync(path.join(__dirname, '../src/components/cake-builder', name), 'utf8');

function main() {
  const cake3d = read('Cake3D.tsx');

  // The outer Suspense must not suspend to nothing.
  assert.ok(
    !/<Suspense\s+fallback=\{null\}>/.test(cake3d),
    'Cake3D: <Suspense fallback={null}> blanks the canvas while the GLB loads',
  );

  // A visible placeholder during loading: the cake drawn procedurally, or a
  // message - anything the customer can see.
  assert.ok(
    /<Suspense\s+fallback=\{<[A-Za-z]/.test(cake3d),
    'Cake3D: Suspense needs a visible fallback while the body model loads',
  );

  // The error boundary must reset when the customer picks another model,
  // otherwise one failed asset disables the studio for the rest of the session.
  assert.ok(
    /componentDidUpdate/.test(cake3d),
    'Cake3D: the fallback boundary must retry on a newly selected model',
  );

  const viewer = read('CakeViewer3D.tsx');
  assert.ok(
    /return this\.state\.failed \? null : this\.props\.children;/.test(viewer) === false,
    'CakeViewer3D: a failed model must not render as an empty canvas',
  );
  assert.ok(
    /if \(this\.state\.failed\)[\s\S]*?return \(\s*<div/.test(viewer),
    'CakeViewer3D: the failure branch needs a visible element',
  );

  // The product page must still be usable when the 3D view cannot load, so the
  // message has to be text, not another silent null.
  assert.ok(
    /failed/.test(viewer) && /Xem mẫu 3D|không tải|Không tải/i.test(viewer),
    'CakeViewer3D: explain to the customer that 3D could not load',
  );

  console.log('PASS GLB fallback leaves no blank canvas');
}

main();