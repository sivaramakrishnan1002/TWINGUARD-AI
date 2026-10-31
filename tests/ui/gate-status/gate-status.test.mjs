import assert from 'node:assert/strict';
import path from 'node:path';
import test from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const frontendRoot = path.join(root, 'frontend');
const require = createRequire(path.join(frontendRoot, 'package.json'));
const { createServer } = require('vite');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

async function renderAppWithBuildValue(value) {
  const encoded = value === undefined ? 'undefined' : JSON.stringify(value);
  const server = await createServer({
    configFile: path.join(frontendRoot, 'vite.config.ts'),
    root: frontendRoot,
    appType: 'custom',
    server: { middlewareMode: true },
    define: { 'import.meta.env.VITE_GATE_G0_STATUS': encoded },
  });
  try {
    const { default: App } = await server.ssrLoadModule('/src/ui/App.tsx');
    return renderToStaticMarkup(React.createElement(App));
  } finally {
    await server.close();
  }
}

test('packaged UI renders authoritative ready status without a contradictory not-ready label', async () => {
  const html = await renderAppWithBuildValue('ready');
  assert.match(html, /role="status" aria-label="Gate G0: READY" data-gate-status="ready">G0 READY<\/small>/);
  assert.doesNotMatch(html, /data-gate-status="not_ready"/);
});

test('packaged UI renders not_ready as not ready', async () => {
  const html = await renderAppWithBuildValue('not_ready');
  assert.match(html, /role="status" aria-label="Gate G0: NOT READY" data-gate-status="not_ready">G0 NOT READY<\/small>/);
  assert.doesNotMatch(html, /data-gate-status="ready"/);
});

test('missing or invalid gate status renders unavailable and never defaults to ready', async (context) => {
  for (const invalid of [undefined, 'READY', null, 'pending']) {
    await context.test(`value ${String(invalid)} is unknown`, async () => {
      const html = await renderAppWithBuildValue(invalid);
      assert.match(html, /role="status" aria-label="Gate G0: STATUS UNKNOWN" data-gate-status="unknown">G0 STATUS UNKNOWN<\/small>/);
      assert.doesNotMatch(html, /data-gate-status="ready"/);
      assert.doesNotMatch(html, /data-gate-status="not_ready"/);
    });
  }
});
