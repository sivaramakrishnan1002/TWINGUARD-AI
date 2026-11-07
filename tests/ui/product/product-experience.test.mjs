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

test('all seven product sections render with reachable semantic navigation', async (context) => {
  const server = await createServer({ configFile: path.join(frontendRoot, 'vite.config.ts'), root: frontendRoot, appType: 'custom', server: { middlewareMode: true }, define: { 'import.meta.env.VITE_GATE_G0_STATUS': JSON.stringify('ready') } });
  try {
    const ui = await server.ssrLoadModule('/src/ui/product/ProductExperience.tsx');
    const expectations = [
      ['overview', 'Situation overview', 'Flood city twin'],
      ['twin', '3D Flood Twin', 'Illustrative flood scene'],
      ['reservoirs', 'Reservoirs & alerts', 'FIXTURE INVENTORY'],
      ['impacts', 'Impacts', 'Illustrative layer view'],
      ['response', 'Emergency response', 'Candidate route comparison'],
      ['what-if', 'What-if lab', 'Adjust demo assumptions'],
      ['system', 'Data & system', 'Source and run context'],
    ];
    for (const [section, heading, card] of expectations) {
      await context.test(`${heading} section`, () => {
        const markup = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: section }));
        assert.match(markup, new RegExp(`aria-label="Product sections"`));
        assert.match(markup, /aria-label="Situation Overview"/);
        assert.match(markup, /aria-label="3D Flood Twin"/);
        assert.equal((markup.match(/aria-current="page"/g) ?? []).length, 1);
        assert.ok(markup.includes(`<h1>${heading.replaceAll('&', '&amp;')}</h1>`), `${section} heading should render`);
        assert.ok(markup.includes(card), `${section} content should render`);
        assert.match(markup, /DEMO \/ SIMULATED/);
        assert.match(markup, /NOT AN OPERATIONAL SERVICE/);
      });
    }
    const twin = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: 'twin' }));
    const overview = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: 'overview' }));
    assert.match(overview, /aria-label="Overview display mode"/);
    assert.match(overview, /aria-label="Select illustrative demo time step"/);
    assert.match(twin, /hand-authored interface illustration and has no Chennai coordinates/);
    assert.match(overview, /aria-label="Select demo scenario"/);
    assert.match(twin, /Play demo/);
    assert.match(twin, /Previous step/);
    assert.match(twin, /Next step/);
    assert.match(twin, /Reset/);
    assert.match(twin, /Select illustrative demo time step/);
    assert.match(twin, /aria-label="Map display mode"/);
    assert.match(twin, /aria-pressed="true">3D view/);
    assert.match(twin, /Map display mode/);
    assert.match(twin, /Demo water shape/);
    assert.match(twin, /Illustrative roads/);
    assert.match(twin, /NoData is a missing-coverage state, never a dry classification/);
    assert.match(twin, /SCHEMATIC CITY BLOCKS/);
    assert.match(twin, /Visual level is unitless/);
    const fallback = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: 'twin', initialViewMode: '2d' }));
    assert.match(fallback, /aria-pressed="true">2D fallback/);
    assert.match(fallback, /Top-down illustrative city grid/);
    assert.doesNotMatch(fallback, /Water surface depth|metres of flood depth/i);
    const whatIf = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: 'what-if' }));
    assert.match(whatIf, /Choose what-if demo scenario/);
    assert.match(whatIf, /Choose demo reservoir assumption/);
    assert.match(whatIf, /Choose demo unavailable shelter/);
    assert.match(whatIf, /Illustrative rainfall input/);
    assert.match(whatIf, /Illustrative reservoir release/);
  } finally {
    await server.close();
  }
});

test('existing gate badge remains an exact build-time snapshot and fails closed', async () => {
  const server = await createServer({ configFile: path.join(frontendRoot, 'vite.config.ts'), root: frontendRoot, appType: 'custom', server: { middlewareMode: true }, define: { 'import.meta.env.VITE_GATE_G0_STATUS': JSON.stringify('not_ready') } });
  try {
    const { default: App } = await server.ssrLoadModule('/src/ui/App.tsx');
    const markup = renderToStaticMarkup(React.createElement(App));
    assert.match(markup, /role="status" aria-label="Gate G0: NOT READY" data-gate-status="not_ready">G0 NOT READY<\/small>/);
    assert.doesNotMatch(markup, /data-gate-status="ready"/);
  } finally {
    await server.close();
  }
});

test('demo adapter steps frames and updates what-if values deterministically', async () => {
  const server = await createServer({ configFile: path.join(frontendRoot, 'vite.config.ts'), root: frontendRoot, appType: 'custom', server: { middlewareMode: true } });
  try {
    const adapter = await server.ssrLoadModule('/src/ui/demo/adapter.ts');
    const fixtures = await server.ssrLoadModule('/src/ui/demo/fixtures.ts');
    const initial = adapter.demoAdapter.getWorkspace('demo-monsoon', 0, adapter.defaultWhatIfInputs);
    const later = adapter.demoAdapter.getWorkspace('demo-monsoon', 1, adapter.defaultWhatIfInputs);
    assert.notEqual(initial.frame.waterPath2d, later.frame.waterPath2d);
    assert.equal(initial.adjustedFrame.waterPath2d, initial.frame.waterPath2d);
    assert.equal(initial.adjustedFrame.waterPath3d, initial.frame.waterPath3d);
    assert.equal(adapter.advanceDemoFrame(0, -1, 4), 0);
    assert.equal(adapter.advanceDemoFrame(3, 1, 4), 3);
    assert.equal(adapter.advanceDemoFrame(3, 1, 4, true), 0);
    const changed = adapter.demoAdapter.getWorkspace('demo-monsoon', 1, { rainfallMm: 100, reservoirReleaseCusecs: 600, unavailableShelterId: 'shelter-a' });
    assert.ok(changed.adjustedImpact.populationExposure > changed.baseline.populationExposure);
    assert.notEqual(changed.adjustedRoutes[0].minutes, initial.adjustedRoutes[0].minutes);
    assert.equal(changed.inputs.unavailableShelterId, 'shelter-a');
    assert.equal(changed.inputs.reservoirId, 'demo-north');
    assert.notEqual(changed.adjustedFrame.waterPath2d, changed.frame.waterPath2d);
    const unavailableShelter = adapter.setDemoShelterAvailability(adapter.defaultWhatIfInputs, 'shelter-a', true);
    assert.equal(unavailableShelter.unavailableShelterId, 'shelter-a');
    assert.equal(adapter.setDemoShelterAvailability(unavailableShelter, 'shelter-a', false).unavailableShelterId, null);
    assert.equal(changed.scenario.reservoirs.find((item) => item.id === 'demo-unknown').storageMcft, null);
    assert.equal(fixtures.DEMO_STATE_EXAMPLES.zero.value, 0);
    for (const kind of ['unknown', 'unavailable', 'zero', 'dry', 'nodata']) assert.equal(fixtures.DEMO_STATE_EXAMPLES[kind].kind, kind);
  } finally {
    await server.close();
  }
});

test('Demo and scenario state stays clearly named as synthetic, not historical or operational', async () => {
  const server = await createServer({ configFile: path.join(frontendRoot, 'vite.config.ts'), root: frontendRoot, appType: 'custom', server: { middlewareMode: true } });
  try {
    const ui = await server.ssrLoadModule('/src/ui/product/ProductExperience.tsx');
    const dataPage = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: 'system' }));
    assert.match(dataPage, /Local static fixture · no refresh/);
    assert.match(dataPage, /Synthetic elapsed steps; no calendar date or observation time/);
    for (const state of ['Unknown', 'Unavailable', 'Known zero \\(0\\)', 'Explicit dry fixture', 'NoData']) assert.match(dataPage, new RegExp(state));
    const response = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: 'response' }));
    assert.match(response, /Reachability does not establish flood access or safety/);
    assert.match(response, /scope="col">Hazard assessment<\/th>/);
    assert.match(response, /<td>Unknown<\/td>/);
    assert.match(response, /No shelter is represented as open or operational/);
    assert.match(response, /Explicit zero-length test case; does not mean a usable route exists/);
  } finally {
    await server.close();
  }
});

test('product shell retains responsive, keyboard, and reduced-motion styling with AA token contrast', async () => {
  const css = await readFile(path.join(frontendRoot, 'src/ui/product/product.css'), 'utf8');
  assert.match(css, /:focus-visible/);
    assert.match(css, /max-width:\s*940px/);
    assert.match(css, /max-width:\s*700px/);
    assert.match(css, /max-width:\s*520px/);
    assert.match(css, /grid-template-columns:\s*repeat\(3,minmax\(0,1fr\)\)/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
    assert.match(css, /\.tg-product__nav-text small\s*\{[^}]*font-size:\s*11px/s);
    assert.match(css, /\.tg-product__metric > span\s*\{[^}]*font-size:\s*12px/s);
    assert.match(css, /\.tg-product__overview-layout\s*\{[^}]*minmax\(0, 1fr\)[^}]*300px/s);
    assert.match(css, /\.tg-product__reservoir-workspace\s*\{[^}]*265px/s);

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
  for (const [fg, bg] of [['--tg-ink', '--tg-canvas'], ['--tg-muted', '--tg-panel'], ['--tg-primary', '--tg-panel']]) {
    assert.ok(contrast(token(fg), token(bg)) >= 4.5, `${fg} on ${bg} should meet 4.5:1; got ${contrast(token(fg), token(bg)).toFixed(2)}`);
  }
});
