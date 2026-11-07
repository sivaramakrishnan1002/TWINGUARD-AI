import assert from 'node:assert/strict';
import test from 'node:test';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const frontendRoot = path.join(root, 'frontend');
const require = createRequire(path.join(frontendRoot, 'package.json'));
const { createServer } = require('vite');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

async function withModules(callback) {
  const server = await createServer({ configFile: path.join(frontendRoot, 'vite.config.ts'), root: frontendRoot, appType: 'custom', logLevel: 'silent', server: { middlewareMode: true, hmr: false } });
  try {
    const client = await server.ssrLoadModule('/src/ui/reservoir-live/reservoirClient.ts');
    const panel = await server.ssrLoadModule('/src/ui/reservoir-live/ReservoirLivePanel.tsx');
    const product = await server.ssrLoadModule('/src/ui/product/ProductExperience.tsx');
    await callback({ client, panel, product });
  } finally { await server.close(); }
}

const SHA = 'a'.repeat(64);
function record(id, name, date, level, storage) {
  return {
    reservoir_id: id, reservoir_name: name, source_date: date, time_precision: 'date', observed_at: null,
    observation_timezone: 'unknown', water_level_m: level, average_storage_mcm: storage,
    received_at: '2026-11-07T06:24:59Z', source_mode: 'LIVE', availability: 'available', freshness: 'unknown',
    freshness_note: 'Cadence unknown.', provenance: { source_id: 'tn_cfm_dss_public_lakes_dashboard', endpoint: '/Master/GetLast15daysWaterLevel', response_sha256: SHA },
  };
}
function payload(overrides = {}) {
  return {
    history_kind: 'daily', source_id: 'tn_cfm_dss_public_lakes_dashboard', source_mode: 'LIVE', received_at: '2026-11-07T06:24:59Z',
    availability: 'available', freshness: 'unknown',
    records: [record('Po001', 'Poondi', '2026-11-06', 38.5, 16.2), record('Po001', 'Poondi', '2026-11-07', 38.69, 16.51), record('Ch001', 'Chembarambakkam', '2026-11-07', 23.03, 39.05)],
    limitations: ['Latest published CFM-DSS dashboard history.'],
    ...overrides,
  };
}

test('reservoir client calls only the same-origin AI proxy with GET and no credentials', async () => {
  await withModules(async ({ client }) => {
    let request;
    const snapshot = await client.fetchReservoirHistory('daily', async (url, options) => {
      request = { url: String(url), options };
      return new Response(JSON.stringify(payload()), { status: 200, headers: { 'content-type': 'application/json' } });
    });
    assert.equal(request.url, '/api/ai/reservoirs/history?period=daily');
    assert.equal(request.options.method, 'GET');
    assert.equal(request.options.credentials, 'omit');
    assert.equal(request.options.cache, 'no-store');
    assert.equal(snapshot.sourceMode, 'LIVE');
    assert.equal(snapshot.freshness, 'unknown');
    assert.deepEqual(snapshot.series.map((item) => item.reservoirName), ['Chembarambakkam', 'Poondi']);
    const poondi = snapshot.series.find((item) => item.reservoirName === 'Poondi');
    assert.equal(poondi.latest.sourceDate, '2026-11-07');
    assert.equal(poondi.records.length, 2);
  });
});

test('reservoir client fails closed on fabricated instants, duplicates, bad periods and upstream errors', async () => {
  await withModules(async ({ client }) => {
    assert.throws(() => client.parseReservoirHistory(payload({ history_kind: 'monthly' }), 'daily'), /period/);
    const instant = payload();
    instant.records[0] = { ...instant.records[0], observed_at: '2026-11-06T00:00:00Z' };
    assert.throws(() => client.parseReservoirHistory(instant, 'daily'), /date-only/);
    const dup = payload();
    dup.records.push(dup.records[0]);
    assert.throws(() => client.parseReservoirHistory(dup, 'daily'), /duplicate/);
    const negative = payload();
    negative.records[0] = { ...negative.records[0], water_level_m: -1 };
    assert.throws(() => client.parseReservoirHistory(negative, 'daily'), /incomplete/);
    await assert.rejects(client.fetchReservoirHistory('daily', async () => new Response('{}', { status: 503 })), /unavailable/);
  });
});

test('panel renders idle, live and failure states without demo substitution', async () => {
  await withModules(async ({ client, panel, product }) => {
    const idle = renderToStaticMarkup(React.createElement(panel.ReservoirLivePanel));
    assert.match(idle, /NOT YET FETCHED/);
    assert.match(idle, /Fetch latest snapshot/);
    assert.match(idle, /Freshness is <strong>unknown<\/strong>/);
    const snapshot = client.parseReservoirHistory(payload(), 'daily');
    const live = renderToStaticMarkup(React.createElement(panel.ReservoirLivePanel, { initialState: { status: 'available', snapshot, message: null } }));
    assert.match(live, /LIVE · SNAPSHOT RECEIVED/);
    assert.match(live, /Latest published dashboard snapshot/);
    assert.match(live, /Poondi/);
    assert.match(live, /38\.69/);
    assert.match(live, /Unknown · date-only source/);
    assert.match(live, /2026-11-07T06:24:59Z/);
    assert.doesNotMatch(live, /mcft/);
    const failed = renderToStaticMarkup(React.createElement(panel.ReservoirLivePanel, { initialState: panel.reservoirRequestFailed(null, 'request timed out.') }));
    assert.match(failed, /UNAVAILABLE/);
    assert.match(failed, /role="alert"/);
    assert.doesNotMatch(failed, /Poondi/);
    const kept = panel.reservoirRequestFailed(snapshot, 'HTTP 503.');
    assert.equal(kept.status, 'refresh-failed');
    assert.match(kept.message, /not presented as current/);
    const section = renderToStaticMarkup(React.createElement(product.ProductExperience, { initialSection: 'reservoirs' }));
    assert.match(section, /PUBLIC CFM-DSS DASHBOARD · LIVE FETCH/);
    // The live panel sits beside saved REPLAY evidence, which stays labelled as replay, not live.
    assert.match(section, /2015 REPLAY alert sequence/);
    assert.match(section, /REPLAY of past data, not a live feed/);
  });
});
