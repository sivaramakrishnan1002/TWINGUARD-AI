import assert from 'node:assert/strict';
import path from 'node:path';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const frontendRoot = path.join(root, 'frontend');
const require = createRequire(path.join(frontendRoot, 'package.json'));
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { createServer } = require('vite');

const server = (gate = 'ready') => createServer({ configFile: path.join(frontendRoot, 'vite.config.ts'), root: frontendRoot, appType: 'custom', logLevel: 'silent', server: { middlewareMode: true, hmr: false, watch: { ignored: () => true } }, envDir: path.join(frontendRoot, 'node_modules/.tg-test-env'), define: { 'import.meta.env.VITE_GATE_G0_STATUS': JSON.stringify(gate) } });
const TABS = [
  ['overview', 'Situation Overview', 'City Risk Snapshot'],
  ['simulation', 'Flood Simulation', 'Simulation Setup'],
  ['emergency', 'Emergency Support', 'Incident Priority Queue'],
  ['routing', 'Road Routing', 'Route Request'],
  ['what-if', 'What-if Simulation', 'Scenario Builder'],
  ['reservoirs', 'Reservoir Monitoring', 'Historical Alert Replay (2015)'],
  ['twin', 'Digital Twin (3D City)', 'Digital Twin Layers'],
];

test('all seven reference-design tabs render with reachable semantic navigation', async (context) => {
  const vite = await server();
  try {
    const ui = await vite.ssrLoadModule('/src/ui/product/ProductExperience.tsx');
    for (const [id, label, panel] of TABS) {
      await context.test(`${id} tab`, () => {
        const markup = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: id }));
        assert.match(markup, /aria-label="Product sections"/);
        for (const [, l] of TABS) assert.ok(markup.includes(`aria-label="${l.replace('&', '&amp;')}"`), `${l} nav item`);
        assert.equal((markup.match(/aria-current="page"/g) ?? []).length, 1);
        assert.ok(markup.includes(`<h1 class="tg-visually-hidden">${label}</h1>`), `${id} heading`);
        assert.ok(markup.includes(panel), `${id} panel`);
        assert.match(markup, /DEMO \/ SIMULATION/);
        assert.match(markup, /TwinGuard AI/);
        assert.doesNotMatch(markup, /LIVE · current/);
      });
    }
  } finally {
    await vite.close();
  }
});

test('generated incidents and scenario resources stay labelled; reservoir snapshots are on request only', async () => {
  const vite = await server();
  try {
    const ui = await vite.ssrLoadModule('/src/ui/product/ProductExperience.tsx');
    const render = (id) => renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: id }));
    assert.match(render('overview'), /Alerts are generated from the simulation, not issued warnings/);
    assert.match(render('overview'), /SCENARIO_INPUT/);
    assert.match(render('emergency'), /Generated from the simulation \(generated: true\)/);
    const reservoirs = render('reservoirs');
    assert.match(reservoirs, /Fetch published snapshot/);
    assert.match(reservoirs, /PUBLISHED_SNAPSHOT/);
    assert.match(reservoirs, /REPLAY of past data, not a live feed/);
    const routing = render('routing');
    assert.match(routing, /Conditional routes use unknown roads and need on-ground verification/);
  } finally {
    await vite.close();
  }
});

test('gate badge remains an exact build-time snapshot and fails closed', async () => {
  const vite = await server('not_ready');
  try {
    const { default: App } = await vite.ssrLoadModule('/src/ui/App.tsx');
    const markup = renderToStaticMarkup(React.createElement(App));
    assert.match(markup, /role="status" aria-label="Gate G0: NOT READY" data-gate-status="not_ready">G0 NOT READY<\/small>/);
    assert.doesNotMatch(markup, /data-gate-status="ready"/);
  } finally {
    await vite.close();
  }
});

test('C4 v3 fixtures follow the contract shapes and keep NoData as null', async () => {
  const vite = await server();
  try {
    const fx = await vite.ssrLoadModule('/src/ui/api/fixtures.ts');
    const grids = await vite.ssrLoadModule('/src/ui/evidence/grids.ts');
    const api = await fx.createFixtureApi();
    assert.equal(api.kind, 'fixture');
    const events = await api.events();
    assert.equal(events.events.length, 3);
    for (const e of events.events) assert.equal(e.source_mode, 'REPLAY');
    const res = await api.getResources();
    for (const r of res.resources) assert.equal(r.source_mode, 'SCENARIO_INPUT');
    await assert.rejects(api.createSimulation({ mode: 'custom', custom_rainfall: { start_time_utc: '2026-11-07T00:00:00Z', interval_minutes: 60, values_mm: [10] } }), (e) => e.status === 503 && e.body.code === 'unavailable');
    assert.match(fx.DEFAULT_RUN_ID, /^(sim|evt|whatif)-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}$/);
    assert.equal(fx.depthClass(null), 'unknown');
    assert.equal(fx.depthClass(0), 'dry');
    assert.equal(fx.depthClass(1.2), 'gt_1_0');
    assert.deepEqual(fx.edgeState(null, 0, 0.3), { state: 'UNKNOWN', reason: 'outside_model_domain' });
    assert.deepEqual(fx.edgeState(0.1, 1, 0.3), { state: 'UNKNOWN', reason: 'bridge_unassessed' });
    assert.equal(fx.edgeState(0.4, 0, 0.3).state, 'ASSESSED_BLOCKED');
    if (grids.gridsBundled()) {
      const run = await api.getSimulation(fx.DEFAULT_RUN_ID);
      assert.equal(run.source_mode, 'SIMULATED');
      assert.equal(run.frames.length, 5);
      const depth = await api.depth(fx.DEFAULT_RUN_ID, 3);
      assert.equal(depth.unit, 'm');
      assert.equal(depth.values.length, depth.rows);
      assert.ok(depth.values.flat().some((v) => v === null), 'NoData cells stay null');
      const inc = await api.incidents(fx.DEFAULT_RUN_ID, 3);
      for (const i of inc.incidents) { assert.equal(i.generated, true); assert.equal(i.generated_from, 'simulation'); }
    }
  } finally {
    await vite.close();
  }
});

test('product shell retains responsive, keyboard and reduced-motion styling with AA token contrast', async () => {
  const css = await readFile(path.join(frontendRoot, 'src/ui/product/product.css'), 'utf8');
  assert.match(css, /\.tg-app :focus-visible/);
  assert.match(css, /max-width:\s*1280px/);
  assert.match(css, /max-width:\s*980px/);
  assert.match(css, /max-width:\s*640px/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
  assert.match(css, /\.tg-reservoir-live\s*\{/, 'B45 panel styles are retained');
  const token = (name) => {
    const match = css.match(new RegExp(`${name}:\\s*(#[0-9a-fA-F]{6})`));
    assert.ok(match, `${name} design token should exist`);
    return match[1];
  };
  const luminance = (hex) => {
    const channels = hex.slice(1).match(/.{2}/g).map((part) => parseInt(part, 16) / 255).map((value) => (value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4));
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
  };
  const contrast = (a, b) => { const v = [luminance(a), luminance(b)].sort((x, y) => y - x); return (v[0] + 0.05) / (v[1] + 0.05); };
  for (const [fg, bg] of [['--tg-ink', '--tg-canvas'], ['--tg-muted', '--tg-panel'], ['--tg-soft', '--tg-panel'], ['--tg-primary', '--tg-panel']]) {
    assert.ok(contrast(token(fg), token(bg)) >= 4.5, `${fg} on ${bg} should meet 4.5:1; got ${contrast(token(fg), token(bg)).toFixed(2)}`);
  }
});
