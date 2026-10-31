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
// Lần sửa sau đó phải đổi KIẾN TRÚC, không chỉ đổi chữ: boundary cũ nằm TRONG
// <Canvas>. R3F render children bằng reconciler Three.js, nên khi fallback trả
// về <div>/<svg>/<p> thì reconciler coi tên thẻ là phần tử THREE không tồn tại
// và ném lỗi lần hai — khách vẫn thấy canvas chết. R3F 8.18 ném lỗi con ra
// ngoài <Canvas> (`if (error) throw error`), nên boundary DOM phải bọc NGOÀI.
//
// Các kiểm tra dưới đây đọc source vì bất biến là "cấu trúc cây", thứ mà test
// render chỉ xác nhận được khi có WebGL thật. Hành vi thực tế (GLB 404 và mất
// WebGL context) được kiểm riêng ở `e2e/cake-3d-fallback.spec.ts`.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const read = name => fs.readFileSync(path.join(__dirname, '../src/components/cake-builder', name), 'utf8');

/** Bỏ chú thích để chữ trong ghi chú (`<Canvas>`...) không bị tính là JSX thật. */
function stripComments(source) {
  return source
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '');
}

/** Boundary phải mở TRƯỚC <Canvas và đóng SAU </Canvas>. */
function assertBoundaryWrapsCanvas(rawSource, file) {
  const source = stripComments(rawSource);
  // `<Canvas` là tiền tố của `<CanvasErrorBoundary`, nên phải khớp đúng thẻ
  // (theo sau là khoảng trắng hoặc `>`); nếu không, chỉ số hai bên trùng nhau
  // và phép so sánh vô nghĩa.
  const boundary = source.search(/<CanvasErrorBoundary[\s>]/);
  const canvas = source.search(/<Canvas[\s>]/);
  const canvasClose = source.indexOf('</Canvas>');
  const boundaryClose = source.indexOf('</CanvasErrorBoundary>');
  assert.ok(boundary !== -1, `${file}: needs a DOM-level CanvasErrorBoundary`);
  assert.ok(
    boundary < canvas && canvasClose !== -1 && canvasClose < boundaryClose,
    `${file}: the fallback boundary must wrap <Canvas> from OUTSIDE; inside the ` +
      'reconciler a DOM fallback throws a second error',
  );
}

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

  assertBoundaryWrapsCanvas(cake3d, 'Cake3D.tsx');

  const viewer = read('CakeViewer3D.tsx');
  assert.ok(
    /return this\.state\.failed \? null : this\.props\.children;/.test(viewer) === false,
    'CakeViewer3D: a failed model must not render as an empty canvas',
  );
  assertBoundaryWrapsCanvas(viewer, 'CakeViewer3D.tsx');

  // Chính boundary dùng chung phải render phần tử DOM nhìn thấy được và đọc
  // được bởi trình đọc màn hình.
  const boundary = read('CanvasErrorBoundary.tsx');
  assert.ok(
    /role="status"/.test(boundary) && /<div/.test(boundary),
    'CanvasErrorBoundary: the failure branch needs a visible, announced element',
  );

  // The product page must still be usable when the 3D view cannot load, so the
  // message has to be text, not another silent null.
  assert.ok(
    /Không tải được mô hình 3D/.test(viewer),
    'CakeViewer3D: explain to the customer that 3D could not load',
  );

  console.log('PASS GLB fallback leaves no blank canvas');
}

main();