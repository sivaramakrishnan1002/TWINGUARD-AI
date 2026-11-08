import assert from 'node:assert/strict';
import path from 'node:path';
import test from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const frontendRoot = path.join(root, 'frontend');
const require = createRequire(path.join(frontendRoot, 'package.json'));
const React = require('react');
const { createServer } = require('vite');
const { renderToStaticMarkup } = require('react-dom/server');

async function loadModules() {
  const server = await createServer({ configFile: path.join(frontendRoot, 'vite.config.ts'), root: frontendRoot, appType: 'custom', server: { middlewareMode: true, hmr: false, watch: { ignored: () => true } }, envDir: path.join(frontendRoot, 'node_modules/.tg-test-env') });
  try {
    return {
      model: await server.ssrLoadModule('/src/ui/live-readiness/model.ts'),
      panel: await server.ssrLoadModule('/src/ui/live-readiness/SourceReadinessPanel.tsx'),
    };
  } finally {
    await server.close();
  }
}

function replayStaleFixture() {
  return {
    sourceMode: 'REPLAY', availability: 'STALE', sourceIdentity: 'Local recorded replay fixture',
    sourceTime: { precision: 'instant', value: '2015-12-01T09:00:00+05:30', timezone: 'Asia/Kolkata', semantics: 'Example fixture source timestamp; original offset retained.' },
    receivedAt: '2015-12-01T09:02:00+05:30', refreshedAt: null, ageSeconds: 900,
    freshnessBasis: 'Example-only caller-supplied threshold; not a source cadence.',
    provenance: { reference: 'local-test-fixture', sha256: 'c'.repeat(64) },
    unavailableReason: null, demoLabel: null, liveEvidence: null,
  };
}

test('valid source modes and availability remain separate, including date-only unknown time', async () => {
  const { model } = await loadModules();
  const demo = model.demoScenarioMetadata({ sourceIdentity: 'Local UI fixture', runId: 'demo-7', version: 'v1', timeSemantics: 'Synthetic steps; no observed timestamp.' });
  assert.equal(demo.sourceMode, 'SIMULATED');
  assert.equal(demo.demoLabel, 'DEMO');
  assert.equal(demo.availability, 'current');
  assert.equal(demo.sourceTime.value, null);
  const replay = model.validateSourceFreshness(replayStaleFixture());
  assert.equal(replay.sourceMode, 'REPLAY');
  assert.equal(replay.availability, 'STALE');
  assert.equal(replay.sourceTime.value, '2015-12-01T09:00:00+05:30');
  const liveUnavailable = model.unavailableLiveMetadata('No authorized and verified source is connected.');
  assert.equal(liveUnavailable.sourceMode, 'LIVE');
  assert.equal(liveUnavailable.availability, 'UNAVAILABLE');
  assert.equal(liveUnavailable.liveEvidence, null);

  const dateOnly = model.validateSourceFreshness({
    ...replayStaleFixture(), availability: 'current', ageSeconds: null,
    sourceTime: { precision: 'date', value: '2015-12-01', timezone: 'unknown', semantics: 'Date-only source row; measurement time is unknown.' },
    receivedAt: '2026-11-04T11:00:00+05:30', freshnessBasis: 'Replay fixture available; source age cannot be measured from date-only input.',
    provenance: { reference: 'archive member hash', sha256: 'd'.repeat(64) },
  });
  assert.equal(dateOnly.sourceTime.value, '2015-12-01');
  assert.equal(dateOnly.sourceTime.timezone, 'unknown');
  assert.notEqual(dateOnly.receivedAt, dateOnly.sourceTime.value);
});

test('invalid mode, freshness, and incomplete metadata fail closed', async () => {
  const { model } = await loadModules();
  const base = replayStaleFixture();
  assert.throws(() => model.validateSourceFreshness({ ...base, sourceMode: 'DEMO' }), /Source mode/);
  assert.throws(() => model.validateSourceFreshness({ ...base, availability: 'fresh' }), /Availability/);
  assert.throws(() => model.validateSourceFreshness({ ...base, sourceMode: 'LIVE', liveEvidence: null }), /LIVE data requires/);
  assert.throws(() => model.validateSourceFreshness({ ...base, sourceMode: 'LIVE', availability: 'current', ageSeconds: null, liveEvidence: { ownerAuthorization: 'fixture-only', runtimeEvidence: 'fixture-only', verifiedAt: '2026-11-04T11:00:00+05:30', observationHash: 'c'.repeat(64) }, provenance: { reference: 'fixture', sha256: 'c'.repeat(64) } }), /Available LIVE data requires/);
  assert.throws(() => model.validateSourceFreshness({ ...base, availability: 'STALE', ageSeconds: null }), /measured age/);
  assert.throws(() => model.validateSourceFreshness({ ...base, sourceTime: { precision: 'date', value: '2015-12-01', timezone: 'Asia/Kolkata', semantics: 'wrongly assigned zone' } }), /timezone must remain unknown/);
  assert.throws(() => model.validateSourceFreshness({ ...base, freshnessBasis: null }), /freshness basis/);
  assert.throws(() => model.validateSourceFreshness({ ...base, sourceIdentity: null }), /source identity/);
  const unavailable = model.unavailableLiveMetadata('No verified source.');
  assert.throws(() => model.validateSourceFreshness({ ...unavailable, unavailableReason: null }), /requires an explicit reason/);
});

test('unknown, unavailable, zero, dry, and NoData remain distinct', async () => {
  const { model } = await loadModules();
  assert.equal(model.observationValueLabel('value', null), 'Unknown');
  assert.equal(model.observationValueLabel('unknown'), 'Unknown');
  assert.equal(model.observationValueLabel('unavailable'), 'Unavailable');
  assert.equal(model.observationValueLabel('zero', 0), 'Known zero');
  assert.equal(model.observationValueLabel('dry'), 'Explicit dry observation');
  assert.equal(model.observationValueLabel('nodata'), 'NoData');
  assert.equal(new Set(['unknown', 'unavailable', 'zero', 'dry', 'nodata'].map((state) => model.observationValueLabel(state))).size, 5);
});

test('stale and unavailable cards expose evidence without asserting a live connection', async () => {
  const { model, panel } = await loadModules();
  const stale = model.validateSourceFreshness(replayStaleFixture());
  const staleMarkup = renderToStaticMarkup(React.createElement(panel.SourceFreshnessCard, { metadata: stale, exampleLabel: 'EXAMPLE · REPLAY' }));
  assert.match(staleMarkup, /data-availability="STALE"/);
  assert.match(staleMarkup, /EXAMPLE · REPLAY/);
  assert.match(staleMarkup, /2015-12-01T09:00:00\+05:30/);
  assert.match(staleMarkup, /2015-12-01T09:02:00\+05:30/);
  const live = model.unavailableLiveMetadata('No verified feed is connected.');
  const liveMarkup = renderToStaticMarkup(React.createElement(panel.SourceFreshnessCard, { metadata: live }));
  assert.match(liveMarkup, /data-availability="UNAVAILABLE"/);
  assert.match(liveMarkup, /No verified live source/);
  assert.match(liveMarkup, /No verified feed is connected/);
  assert.doesNotMatch(liveMarkup, />LIVE<\/strong>/);
});

test('current product shows data freshness and never presents unfetched or saved data as live', async () => {
  const server = await createServer({ configFile: path.join(frontendRoot, 'vite.config.ts'), root: frontendRoot, appType: 'custom', server: { middlewareMode: true, hmr: false, watch: { ignored: () => true } }, envDir: path.join(frontendRoot, 'node_modules/.tg-test-env') });
  try {
    const ui = await server.ssrLoadModule('/src/ui/product/ProductExperience.tsx');
    const markup = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: 'overview' }));
    assert.match(markup, /Confidence &amp; Data Freshness/);
    assert.match(markup, /DATA: CONNECTING|DATA: SAVED RESULTS|DATA: C4 v3 API/);
    assert.match(markup, /Not fetched\. Snapshots are read only when you ask\./);
    assert.doesNotMatch(markup, /LIVE · current/);
  } finally {
    await server.close();
  }
});
