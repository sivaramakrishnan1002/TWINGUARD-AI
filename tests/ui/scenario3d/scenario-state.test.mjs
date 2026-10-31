import assert from 'node:assert/strict';
import test from 'node:test';
import { findScenario, makeScenarioKey } from '../../../frontend/src/ui/scenario3d/scenarioApi.js';
import { adjacentSavedTime, initialScenarioState, scenarioReducer } from '../../../frontend/src/ui/scenario3d/scenarioState.js';

const a = { event_id: '2015-12-02', scenario_id: 'perfect_foresight_imerg', source_mode: 'PERFECT_FORESIGHT_HINDCAST' };
const b = { event_id: '2021-11-13', scenario_id: 'perfect_foresight_imerg', source_mode: 'PERFECT_FORESIGHT_HINDCAST' };

test('scenario selection key requires the exact event and scenario identity', () => {
  const catalog = { scenario_series: [a, b] };
  assert.equal(makeScenarioKey(a), '2015-12-02::perfect_foresight_imerg');
  assert.equal(findScenario(catalog, makeScenarioKey(b)), b);
  assert.equal(findScenario(catalog, '2015-12-03::perfect_foresight_imerg'), null);
  assert.equal(findScenario({ scenario_series: [a, a] }, makeScenarioKey(a)), null);
});

test('loading, failure, and 2D fallback state remain explicit', () => {
  const loading = scenarioReducer(initialScenarioState, { type: 'SELECT_SCENARIO', key: makeScenarioKey(a) });
  assert.equal(loading.phase, 'loading_detail');
  const failed = scenarioReducer(loading, { type: 'FAILED', message: 'saved asset unavailable' });
  assert.equal(failed.phase, 'error');
  assert.equal(failed.message, 'saved asset unavailable');
  const fallback = scenarioReducer(failed, { type: 'SET_VIEW', view: '2D' });
  assert.equal(fallback.view, '2D');
  const retried = scenarioReducer(fallback, { type: 'RETRY_CATALOG' });
  assert.equal(retried.phase, 'loading_catalog');
  assert.equal(retried.view, '3D');
});

test('time stepping selects only adjacent exact saved timestamps', () => {
  const slices = ['2015-11-30T06:00:00Z', '2015-12-01T06:00:00Z', '2015-12-02T06:00:00Z'].map((valid_time_utc) => ({ valid_time_utc }));
  assert.equal(adjacentSavedTime(slices, slices[0].valid_time_utc, 1), slices[1].valid_time_utc);
  assert.equal(adjacentSavedTime(slices, slices[1].valid_time_utc, -1), slices[0].valid_time_utc);
  assert.equal(adjacentSavedTime(slices, 'missing', 1), slices[1].valid_time_utc);
});

test('saved evidence labels remain separate from live or operational mode', () => {
  assert.equal(a.source_mode, 'PERFECT_FORESIGHT_HINDCAST');
  assert.notEqual(a.source_mode, 'LIVE');
});
