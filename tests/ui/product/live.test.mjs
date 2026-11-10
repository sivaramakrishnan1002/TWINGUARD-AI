import assert from 'node:assert/strict';
import path from 'node:path';
import test from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const frontendRoot = path.join(root, 'frontend');
const require = createRequire(path.join(frontendRoot, 'package.json'));
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { createServer } = require('vite');
const server = () => createServer({ configFile: path.join(frontendRoot, 'vite.config.ts'), root: frontendRoot, appType: 'custom', logLevel: 'silent', server: { middlewareMode: true, hmr: false, watch: { ignored: () => true } }, envDir: path.join(frontendRoot, 'node_modules/.tg-test-env') });

test('B52 live client: same-origin GET status/latest, POST refresh, 429 surfaces retry_after_s', async () => {
  const vite = await server();
  try {
    const { createHttpApi } = await vite.ssrLoadModule('/src/ui/api/client.ts');
    const calls = [];
    const api = createHttpApi(async (url, init = {}) => {
      calls.push(`${init.method ?? 'GET'} ${url}`);
      if (String(url).endsWith('/live/refresh')) return new Response(JSON.stringify({ detail: 'Manual refresh allowed every 600 s.', code: 'rate_limited', retry_after_s: 420 }), { status: 429 });
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    });
    await api.liveStatus();
    await api.liveLatest();
    await assert.rejects(api.liveRefresh(), (e) => e.status === 429 && e.body.retry_after_s === 420);
    assert.deepEqual(calls, ['GET /api/ai/v3/live/status', 'GET /api/ai/v3/live/latest', 'POST /api/ai/v3/live/refresh']);
  } finally {
    await vite.close();
  }
});

test('B52 run-kind badges, assumption inputs and the disclaimer on every tab', async () => {
  const vite = await server();
  try {
    const R = await vite.ssrLoadModule('/src/ui/product/runs.ts');
    const ui = await vite.ssrLoadModule('/src/ui/product/ProductExperience.tsx');
    const fx = await vite.ssrLoadModule('/src/ui/api/fixtures.ts');
    assert.equal(R.badgeFor('LIVE_FORECAST'), 'LIVE FORECAST');
    assert.equal(R.badgeFor('REPLAY'), 'REPLAY');
    assert.equal(R.badgeFor('WHAT_IF'), 'WHAT-IF');
    assert.equal(R.badgeFor('CUSTOM'), 'CUSTOM');
    assert.equal(R.badgeFor('FORECAST'), 'FORECAST');
    assert.equal(R.badgeFor(null), 'DEMO / SIMULATION');
    const mk = (id, kind, res = 'citywide', created = '2026-11-10T00:00:00Z') => ({ run_id: id, state: 'completed', run_kind: kind, mode: 'event', request: { mode: 'event', resolution: res }, created_at: created, frames: [] });
    assert.equal(R.defaultRun([mk('c1', 'CUSTOM'), mk('f1', 'REPLAY', 'focus'), mk('r1', 'REPLAY'), mk('r2', 'REPLAY')]).run_id, 'r1', 'newest citywide event replay, not a custom or focus run');
    assert.equal(R.runKindOf({ mode: 'event', request: { mode: 'event' } }), 'REPLAY', 'older runs derive their kind from the request');
    assert.equal(R.runKindOf({ mode: 'forecast', run_kind: 'LIVE_FORECAST' }), 'LIVE_FORECAST');
    assert.equal(R.isAssumptionInput({ name: 'reservoir_outlet_inflow', source: 'A28-RES-STORAGE-v1 (ASSUMPTION; not an observed release)', source_mode: 'SCENARIO_INPUT' }), true);
    assert.equal(R.isAssumptionInput({ name: 'rainfall', source: 'open-meteo:ecmwf_ifs', source_mode: 'MODEL_FORECAST' }), false);
    assert.equal(R.LIVE_DISCLAIMER, 'Model forecast — not an official warning');
    for (const id of ['overview', 'simulation', 'emergency', 'routing', 'what-if', 'reservoirs', 'twin']) {
      const markup = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: id }));
      assert.ok(markup.includes('Model forecast — not an official warning'), `${id}: disclaimer`);
    }
    const res = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: 'reservoirs' }));
    assert.match(res, /ASSUMPTION<\/b> Live forecast runs derive reservoir outlet inflows/);
    const api = await fx.createFixtureApi();
    const st = await api.liveStatus();
    assert.equal(st.enabled, false, 'saved-results mode has no live cycle');
    await assert.rejects(api.liveRefresh(), (e) => e.status === 503);
  } finally {
    await vite.close();
  }
});
