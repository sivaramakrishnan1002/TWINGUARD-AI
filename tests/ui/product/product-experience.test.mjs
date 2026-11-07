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

const server = (gate = 'ready') => createServer({ configFile: path.join(frontendRoot, 'vite.config.ts'), root: frontendRoot, appType: 'custom', server: { middlewareMode: true }, define: { 'import.meta.env.VITE_GATE_G0_STATUS': JSON.stringify(gate) } });

test('all seven report-backed sections render with reachable semantic navigation', async (context) => {
  const vite = await server();
  try {
    const ui = await vite.ssrLoadModule('/src/ui/product/ProductExperience.tsx');
    const expectations = [
      ['overview', 'Situation overview', 'Scenario snapshot'],
      ['twin', 'Flood simulation', 'Simulation setup'],
      ['impacts', 'Impacts &amp; shelters', 'Facility access cascade at +72 h'],
      ['response', 'Road routing', 'Three-state road evidence'],
      ['what-if', 'What-if comparison', 'Compare saved scenarios'],
      ['reservoirs', 'Reservoirs (Track B)', '2015 REPLAY alert sequence'],
      ['system', 'Data &amp; evidence', 'Coverage states'],
    ];
    for (const [section, heading, card] of expectations) {
      await context.test(`${section} section`, () => {
        const markup = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: section }));
        assert.match(markup, /aria-label="Product sections"/);
        for (const label of ['Situation Overview', 'Flood Simulation', 'Impacts &amp; Shelters', 'Road Routing', 'What-if Comparison', 'Reservoirs (Track B)', 'Data &amp; Evidence']) assert.ok(markup.includes(`aria-label="${label}"`), `${label} nav item`);
        assert.equal((markup.match(/aria-current="page"/g) ?? []).length, 1);
        assert.ok(markup.includes(`<h1>${heading}</h1>`), `${section} heading should render`);
        assert.ok(markup.includes(card), `${section} content should render`);
        assert.match(markup, /NOT AN OPERATIONAL SERVICE/);
        assert.match(markup, /Research prototype · not an official warning/);
        assert.match(markup, /SIMULATED · HINDCAST/);
        assert.match(markup, /aria-label="Select event window"/);
        assert.match(markup, /aria-label="Select rainfall scenario"/);
      });
    }
  } finally {
    await vite.close();
  }
});

test('figures shown come from the cited reports and keep their caveats', async () => {
  const vite = await server();
  try {
    const ui = await vite.ssrLoadModule('/src/ui/product/ProductExperience.tsx');
    const render = (section) => renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: section }));
    const overview = render('overview');
    assert.match(overview, /2,21,131/, 'A07 Dec 2015 perfect-foresight +48 h people in screened cells');
    assert.match(overview, /WorldPop model estimate · PARTIAL/);
    assert.match(overview, /docs\/PHASE13_IMPACT_BATCH2_V4\.md/);
    const twin = render('twin');
    assert.match(twin, /aria-label="Map display mode"/);
    assert.match(twin, /aria-label="Depth band"/);
    assert.match(twin, /351\.54 mm \/ 72 h/, 'A05 report rainfall total');
    assert.match(twin, /Nothing is interpolated between them/);
    const routing = render('response');
    assert.match(routing, /Unknown · verify/);
    assert.match(routing, /Never treated as passable/);
    assert.match(routing, /Uncertainty-aware/);
    const whatIf = render('what-if');
    assert.match(whatIf, /aria-label="Scenario A"/);
    assert.match(whatIf, /aria-label="Scenario B"/);
    assert.match(whatIf, /not predictions or validated counterfactual outcomes/);
    assert.match(whatIf, /H2–H5 are not confirmed/);
    const reservoirs = render('reservoirs');
    assert.match(reservoirs, /Storage % uses current published capacity/);
    assert.match(reservoirs, /not a live feed or flood warning/);
    const system = render('system');
    for (const state of ['Known value', 'Known zero (0)', 'NoData', 'Unknown', 'Unavailable']) assert.ok(system.includes(state), `${state} remains distinct`);
    assert.match(system, /Unknown, not dry/);
    assert.match(system, /B40 is blocked pending authorization/);
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

test('report evidence keeps NoData, unknown and assumption semantics', async () => {
  const vite = await server();
  try {
    const reports = await vite.ssrLoadModule('/src/ui/evidence/reports.ts');
    const grids = await vite.ssrLoadModule('/src/ui/evidence/grids.ts');
    assert.equal(reports.EVENTS.length, 3);
    assert.equal(reports.SCENARIOS.length, 5);
    assert.deepEqual(reports.LEADS, [6, 12, 24, 48, 72]);
    for (const e of reports.EVENTS) for (const s of reports.SCENARIOS) for (const l of reports.LEADS) assert.equal(reports.A07_IMPACT[e.id][s.id][l].length, 3);
    assert.equal(reports.A21.failClosed + reports.A21.conditional + reports.A21.noPath, reports.A21.primaryCases);
    assert.equal(reports.TRACKB_REPLAY.length, 50);
    assert.equal(grids.NODATA_MM, 65535);
    assert.equal(reports.A09_METHODS.find((m) => m.method === 'Static free-flow').failure, null, 'unassessed stays null, not zero');
  } finally {
    await vite.close();
  }
});

test('product shell retains responsive, keyboard, and reduced-motion styling with AA token contrast', async () => {
  const css = await readFile(path.join(frontendRoot, 'src/ui/product/product.css'), 'utf8');
  assert.match(css, /\.tg-app :focus-visible/);
  assert.match(css, /max-width:\s*940px/);
  assert.match(css, /max-width:\s*700px/);
  assert.match(css, /max-width:\s*520px/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
  assert.match(css, /\.tg-reservoir-live\s*\{/, 'B45 panel styles are retained');
  assert.match(css, /\.tg-weather-card\s*\{/, 'CR-014 weather card styles are retained');
  const token = (name) => {
    const match = css.match(new RegExp(`${name}:\\s*(#[0-9a-fA-F]{6})`));
    assert.ok(match, `${name} design token should exist`);
    return match[1];
  };
  const luminance = (hex) => {
    const channels = hex.slice(1).match(/.{2}/g).map((part) => parseInt(part, 16) / 255).map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
  };
  const contrast = (foreground, background) => {
    const values = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
    return (values[0] + 0.05) / (values[1] + 0.05);
  };
  for (const [fg, bg] of [['--tg-ink', '--tg-canvas'], ['--tg-muted', '--tg-panel'], ['--tg-soft', '--tg-panel'], ['--tg-primary', '--tg-panel']]) {
    assert.ok(contrast(token(fg), token(bg)) >= 4.5, `${fg} on ${bg} should meet 4.5:1; got ${contrast(token(fg), token(bg)).toFixed(2)}`);
  }
});

test('demo adapter remains deterministic for any consumer still importing it', async () => {
  const vite = await server();
  try {
    const adapter = await vite.ssrLoadModule('/src/ui/demo/adapter.ts');
    assert.equal(adapter.advanceDemoFrame(0, -1, 4), 0);
    assert.equal(adapter.advanceDemoFrame(3, 1, 4, true), 0);
  } finally {
    await vite.close();
  }
});
