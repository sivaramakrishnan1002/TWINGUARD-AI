import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { colorForDepth, parseA20Float32GeoTiff, rasterToFeatures, summarizeValidValues, utm44ToWgs84 } from '../../../frontend/src/ui/scenario3d/geotiff.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const manifest = JSON.parse(await readFile(path.join(root, 'data/features/visualization3d/batch2_v1/manifest.json'), 'utf8'));
const series = manifest.scenario_series.find((item) => item.event_id === '2015-12-02' && item.scenario_id === 'perfect_foresight_imerg');
const slice = series.slices.find((item) => item.valid_time_utc === '2015-11-30T06:00:00Z');
const band = slice.bands.p50;
const rasterBytes = new Uint8Array(await readFile(path.join(root, band.path)));
const expectedGrid = {
  width: band.grid.width,
  height: band.grid.height,
  epsg: 32644,
  transform: band.grid.affine_transform,
  nodata: band.nodata_value,
};

test('decodes the exact saved Float32 grid, CRS, extent and mask', async () => {
  const raster = await parseA20Float32GeoTiff(rasterBytes, expectedGrid);
  assert.equal(raster.width, 69);
  assert.equal(raster.height, 88);
  assert.equal(raster.crs, 'EPSG:32644');
  assert.deepEqual(raster.bounds, [390000, 1418820, 431400, 1471620]);
  assert.equal(raster.validCount, 2430);
  assert.equal(raster.nodataCount, 3642);
  assert.equal(raster.values[69 * 30 + 5], 0.000968976819422096);
  assert.equal(raster.values[0], -9999);
  assert.equal(raster.validMask[0], 0);
  assert.equal(raster.validMask[69 * 30 + 5], 1);
});

test('keeps NoData out of mapped features and outside the value range', async () => {
  const raster = await parseA20Float32GeoTiff(rasterBytes, expectedGrid);
  const features = rasterToFeatures(raster);
  const range = summarizeValidValues(raster);
  assert.equal(features.features.length, raster.validCount);
  assert.ok(features.features.every((feature) => feature.properties.depth_m !== -9999));
  assert.ok(range.min > -9999);
  assert.ok(range.max < Infinity);
  assert.match(colorForDepth(range.min, range.min, range.max), /^#[0-9a-f]{6}$/);
});

test('fails closed when manifest grid differs from source bytes', async () => {
  await assert.rejects(parseA20Float32GeoTiff(rasterBytes, { ...expectedGrid, epsg: 4326 }), /CRS does not match/);
});

test('projects the declared UTM grid to geographic display coordinates', () => {
  const [longitude, latitude] = utm44ToWgs84(410700, 1445220);
  assert.ok(Math.abs(longitude - 80.1763017117) < 1e-8);
  assert.ok(Math.abs(latitude - 13.0717907529) < 1e-7);
});
