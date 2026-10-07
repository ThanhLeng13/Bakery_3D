// Regression: selected GLB bodies must compose decorations, not just change price.
// Uses real GLB geometry; only the browser asset-loading hook is substituted.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

async function main() {
  const three = await import('three');
  const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js');
  let loaded;
  const originalLoad = Module._load;
  Module._load = function (id, parent, isMain) {
    if (id === 'three') return three;
    if (id === '@react-three/drei') return { useGLTF: () => loaded };
    if (id.startsWith('@/')) id = path.join(__dirname, '../src', id.slice(2));
    return originalLoad.call(this, id, parent, isMain);
  };
  for (const extension of ['.ts', '.tsx']) {
    require.extensions[extension] = (module, filename) => module._compile(
      ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
        compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS, esModuleInterop: true },
      }).outputText, filename);
  }
  const Body = require('../src/components/cake-builder/GlbCakeBody.tsx').default;
  const cases = [
    ['round-1-tier', 'cake-tron-1-tang.glb', '16cm', 1],
    ['round-1-tier', 'cake-tron-1-tang.glb', '24cm', 1],
    ['round-2-tier', 'cake-tron-2-tang.glb', '2-tier', 2],
    ['round-3-tier', 'cake-tron-3-tang.glb', '20cm', 3],
    ['tall-1-tier', 'cake-cao-1-tang.glb', '20cm', 1],
    ['square-1-tier', 'cake-vuong-1-tang.glb', '20cm', 1],
    ['heart-1-tier', 'cake-trai-tim.glb', '20cm', 1],
  ];
  for (const [slug, file, size, count] of cases) {
    const bytes = fs.readFileSync(path.join(__dirname, '../public/models', file));
    loaded = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
    let layout;
    const stop = new Error('Stop before rendering WebGL elements into HTML');
    try {
      renderToStaticMarkup(React.createElement(Body, {
        design: { model_slug: slug, size, zones: { top: { toppings: ['flowers'] }, border: { decoration: 'pearls' } } },
        activeZone: null, hoveredZone: null, onZoneClick() {}, onZoneHover() {},
        renderDecorations(tiers) { layout = tiers; throw stop; },
      }));
    } catch (error) { if (error !== stop) throw error; }
    assert.ok(layout, `${slug}: decorations were not rendered with the GLB`);
    assert.equal(layout.length, count);
    for (const tier of layout) {
      assert.ok(tier.radius > 0 && tier.height > 0);
      assert.ok(tier.surfaceY > tier.bodyY);
      assert.ok(tier.surfaceAt(tier.radius * 0.64, 0) > tier.bodyY, 'toppings must sit above the body');
      assert.equal(typeof tier.edgeAt, 'function', 'decorations need the actual outline, not a circular radius');
      if (slug.startsWith('round') || slug === 'tall-1-tier') {
        assert.ok(tier.surfaceAt(0.01, 0) - tier.surfaceAt(tier.radius * 0.92, 0) > 0.02,
          'raycast must hit the domed frosting, not return its maximum height for every point');
      }
      const { createGanacheGeometry } = require('../src/components/cake-builder/cake-decoration-surface.ts');
      const glaze = createGanacheGeometry(tier);
      const vertices = glaze.getAttribute('position');
      // All eight top rows must follow the icing, including the rounded shoulder.
      for (let i = 0; i < vertices.count; i++) {
        if (i % 10 >= 8) continue;
        const gap = vertices.getY(i) - tier.surfaceAt(vertices.getX(i), vertices.getZ(i));
        assert.ok(gap >= 0 && gap < 0.012, `${slug}: floating ganache gap ${gap}`);
      }
      if (slug === 'square-1-tier' || slug === 'heart-1-tier') {
        const distances = Array.from({ length: 40 }, (_, i) => tier.edgeAt(i / 40).length());
        assert.ok(Math.max(...distances) - Math.min(...distances) > 0.12, 'non-round outline must not become a circle');
        assert.ok(tier.icingBottom <= tier.bodyY + tier.height / 2 + 0.001, 'icing must not float above the body');
      }
      glaze.dispose();
    }
    assert.ok(layout.every((tier, i) => i === 0 || tier.surfaceY > layout[i - 1].surfaceY));
    // Loading/customizing must not hide borders in Drei's shared source asset.
    assert.equal(loaded.scene.getObjectByName('Border').visible, true);
    console.log(`PASS ${slug} ${size}: ${count} decoration surfaces`);
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
