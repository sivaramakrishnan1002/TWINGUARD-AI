import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { fetchScenarioCatalog, fetchScenarioDetail, fetchScenarioRaster } from '../../../frontend/src/ui/scenario3d/scenarioApi.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const manifest = JSON.parse(await readFile(path.join(root, 'data/features/visualization3d/batch2_v1/manifest.json'), 'utf8'));
const series = manifest.scenario_series.find((item) => item.event_id === '2015-12-02' && item.scenario_id === 'perfect_foresight_imerg');
const slice = series.slices.find((item) => item.valid_time_utc === '2015-11-30T06:00:00Z');
const band = slice.bands.p50;
const raster = await readFile(path.join(root, band.path));
const detail = { ...manifest, series };

test('catalog/detail/raster use only bounded GETs to approved exact routes', async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (input, init) => {
    const url = new URL(String(input));
    calls.push({ url, init });
    if (url.pathname === '/scenario-visualization-assets') {
      return new Response(JSON.stringify({ scenario_series: [series] }), { headers: { 'Content-Type': 'application/json' } });
    }
    if (url.pathname === `/scenario-visualization-assets/${series.event_id}/${series.scenario_id}`) {
      return new Response(JSON.stringify(detail), { headers: { 'Content-Type': 'application/json' } });
    }
    if (url.pathname === `/scenario-visualization-assets/${series.event_id}/${series.scenario_id}/raster`) {
      return new Response(raster, { headers: { 'Content-Type': 'image/tiff', 'Content-Length': String(raster.byteLength) } });
    }
    throw new Error('Unexpected route in B18 test');
  };

  try {
    const catalog = await fetchScenarioCatalog();
    const fetchedDetail = await fetchScenarioDetail(series.event_id, series.scenario_id);
    const result = await fetchScenarioRaster(fetchedDetail, slice.valid_time_utc, 'p50', band.sha256);
    assert.equal(catalog.scenario_series.length, 1);
    assert.equal(fetchedDetail.provenance.forecast_summary.sha256, manifest.provenance.forecast_summary.sha256);
    assert.equal(fetchedDetail.provenance.simulation_summary.sha256, manifest.provenance.simulation_summary.sha256);
    assert.equal(fetchedDetail.provenance.source_hash_status, 'all_declared_A05_A06_input_hashes_match_current_files');
    assert.equal(fetchedDetail.nodata.meaning, 'outside assessed CMA or otherwise unmodelled; it is unknown coverage, not dry');
    assert.equal(result.sha256, band.sha256);
    assert.equal(result.raster.validCount, band.valid_cell_count);
    assert.equal(result.raster.nodataCount, band.nodata_cell_count);
    assert.equal(calls.length, 3);
    assert.deepEqual(calls.map(({ url }) => url.pathname), [
      '/scenario-visualization-assets',
      `/scenario-visualization-assets/${series.event_id}/${series.scenario_id}`,
      `/scenario-visualization-assets/${series.event_id}/${series.scenario_id}/raster`,
    ]);
    assert.equal(calls[2].url.searchParams.get('valid_time_utc'), slice.valid_time_utc);
    assert.equal(calls[2].url.searchParams.get('band'), 'p50');
    for (const { url, init } of calls) {
      assert.equal(url.origin, 'http://127.0.0.1:8000');
      assert.equal(init.method, 'GET');
      assert.equal(init.credentials, 'omit');
      assert.deepEqual(init.headers, { Accept: url.pathname.endsWith('/raster') ? 'image/tiff' : 'application/json' });
    }
  } finally {
    globalThis.fetch = originalFetch;
  }
});
