export const initialScenarioState = Object.freeze({
  phase: 'loading_catalog',
  catalog: null,
  selectedKey: '',
  detail: null,
  validTimeUtc: '',
  band: 'p50',
  raster: null,
  view: '3D',
  playing: false,
  message: '',
});

export function scenarioReducer(state, action) {
  switch (action.type) {
    case 'CATALOG_READY':
      return {
        ...state,
        phase: action.catalog.scenario_series.length ? 'catalog_ready' : 'empty',
        catalog: action.catalog,
        message: action.catalog.scenario_series.length ? '' : 'No saved A20 scenarios are available.',
      };
    case 'RETRY_CATALOG':
      return { ...initialScenarioState };
    case 'SELECT_SCENARIO':
      return {
        ...state,
        phase: 'loading_detail',
        selectedKey: action.key,
        detail: null,
        validTimeUtc: '',
        raster: null,
        playing: false,
        message: '',
      };
    case 'DETAIL_READY': {
      const series = action.detail.series;
      const firstSlice = series.slices[0];
      if (!firstSlice) return { ...state, phase: 'empty', detail: action.detail, message: 'This saved scenario has no available timestamps.' };
      const band = ['p50', 'p05', 'p95'].find((name) => firstSlice.bands?.[name]) ?? '';
      if (!band) return { ...state, phase: 'empty', detail: action.detail, message: 'This saved scenario has no supported raster bands.' };
      return {
        ...state,
        phase: 'loading_raster',
        detail: action.detail,
        validTimeUtc: firstSlice.valid_time_utc,
        band,
        raster: null,
        message: '',
      };
    }
    case 'SELECT_SLICE':
      return { ...state, phase: 'loading_raster', validTimeUtc: action.validTimeUtc, band: action.band, raster: null, playing: false, message: '' };
    case 'RASTER_READY':
      if (action.validTimeUtc !== state.validTimeUtc || action.band !== state.band) return state;
      return { ...state, phase: 'ready', raster: action.raster, message: '' };
    case 'FAILED':
      return { ...state, phase: 'error', raster: null, playing: false, message: action.message };
    case 'SET_VIEW':
      return { ...state, view: action.view };
    case 'SET_PLAYING':
      return { ...state, playing: action.playing };
    default:
      return state;
  }
}

export function adjacentSavedTime(slices, current, direction) {
  if (!Array.isArray(slices) || slices.length === 0) return '';
  const index = slices.findIndex((slice) => slice.valid_time_utc === current);
  const start = index < 0 ? 0 : index;
  const next = (start + direction + slices.length) % slices.length;
  return slices[next].valid_time_utc;
}
