import assert from 'node:assert/strict';
import path from 'node:path';
import test from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const frontendRoot = path.join(root, 'frontend');
const require = createRequire(path.join(frontendRoot, 'package.json'));
const { createServer } = require('vite');

const frames = (n, start = '2015-11-30T00:00:00Z') => Array.from({ length: n }, (_, i) => ({ index: i, valid_time_utc: new Date(Date.parse(start) + i * 1800000).toISOString(), elapsed_minutes: i * 30 }));
const run = (id, state, request, created, n = 49) => ({ run_id: id, state, mode: request.mode, request, source_mode: 'SIMULATED', label: 'Chennai floods, Dec 2015', created_at: created, frames: frames(n), frame_interval_minutes: 30, provenance: { engine_version: 'x', run_id: id, inputs: [] } });

test('runs are labelled by resolution, sorted citywide first, and focus runs get a citywide context run', async () => {
  const vite = await createServer({ configFile: path.join(frontendRoot, 'vite.config.ts'), root: frontendRoot, appType: 'custom', logLevel: 'silent', server: { middlewareMode: true, hmr: false, watch: { ignored: () => true } }, envDir: path.join(frontendRoot, 'node_modules/.tg-test-env') });
  try {
    const R = await vite.ssrLoadModule('/src/ui/product/runs.ts');
    const focus = run('evt-20261110T042654Z-52149f5f', 'completed', { mode: 'event', event_key: '2015-12-01', duration_hours: 24, resolution: 'focus', focus_area: 'VELACHERY' }, '2026-11-10T04:26:54Z');
    const city48 = run('evt-20261108T152128Z-59eba744', 'completed', { mode: 'event', event_key: '2015-12-01', duration_hours: 48, resolution: 'citywide' }, '2026-11-08T15:21:28Z', 97);
    const city6 = run('evt-20261108T092757Z-95df136d', 'completed', { mode: 'event', event_key: '2015-12-01', duration_hours: 6, resolution: 'citywide' }, '2026-11-08T09:27:57Z', 13);
    const other = run('evt-20261108T150215Z-4f19092b', 'completed', { mode: 'event', event_key: '2023-12-03', duration_hours: 48, resolution: 'citywide' }, '2026-11-08T15:02:15Z', 97);
    const failed = run('sim-20261108T152438Z-54e95bb8', 'failed', { mode: 'custom', duration_hours: 6, resolution: 'citywide' }, '2026-11-11T00:00:00Z', 0);

    assert.equal(R.runTitle(city48), 'Chennai floods, Dec 2015 · citywide 120 m · 48 h');
    assert.equal(R.runTitle(focus), 'Velachery focus 30 m · Chennai floods, Dec 2015 · 24 h');
    assert.equal(R.isFocusRun(focus), true);
    assert.equal(R.isFocusRun(city48), false);

    const sorted = R.sortRuns([failed, focus, city6, city48, other]).map((r) => r.run_id);
    assert.deepEqual(sorted, [city48.run_id, other.run_id, city6.run_id, focus.run_id, failed.run_id], 'completed citywide (newest first), then focus, then failed');

    assert.equal(R.contextRunFor(focus, [focus, city6, city48, other])?.run_id, city48.run_id, 'same event, covers the focus duration');
    assert.equal(R.contextRunFor(city48, [focus, city48]), null, 'citywide runs need no context');
    assert.equal(R.nearestFrameByTime(city48, '2015-12-01T00:00:00Z'), 48);
  } finally {
    await vite.close();
  }
});
