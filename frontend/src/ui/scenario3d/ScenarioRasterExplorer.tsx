import { useCallback, useEffect, useId, useMemo, useReducer, useRef, useState } from 'react';
import { Map as MapLibreMap, NavigationControl } from 'maplibre-gl';
import type { MapMouseEvent, StyleSpecification } from 'maplibre-gl';
import {
  fetchScenarioCatalog,
  fetchScenarioDetail,
  fetchScenarioRaster,
  findScenario,
  makeScenarioKey,
} from './scenarioApi.js';
import { colorForDepth, rasterToFeatures, summarizeValidValues, utm44ToWgs84 } from './geotiff.js';
import { adjacentSavedTime, initialScenarioState, scenarioReducer } from './scenarioState.js';
import './scenario.css';

import type { ScenarioSeries } from './scenarioApi.js';

import type { DecodedScenarioRaster } from './scenarioApi.js';

const scenarioStyle: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: 'saved-evidence-background', type: 'background', paint: { 'background-color': '#eef2ef' } }],
};

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Saved scenario data could not be loaded.';
}

function formatMeters(value: number): string {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value);
}

export function ScenarioRasterExplorer() {
  const [state, dispatch] = useReducer(scenarioReducer, initialScenarioState);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [hoveredDepth, setHoveredDepth] = useState<number | null>(null);
  const [mapError, setMapError] = useState('');

  const onMapError = useCallback((message: string) => setMapError(message), []);
  const onCellHover = useCallback((value: number | null) => setHoveredDepth(value), []);

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReducedMotion(query.matches);
    update();
    query.addEventListener?.('change', update);
    return () => query.removeEventListener?.('change', update);
  }, []);

  useEffect(() => {
    if (state.phase !== 'loading_catalog') return undefined;
    const controller = new AbortController();
    fetchScenarioCatalog(controller.signal)
      .then((catalog) => dispatch({ type: 'CATALOG_READY', catalog }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) dispatch({ type: 'FAILED', message: errorMessage(error) });
      });
    return () => controller.abort();
  }, [state.phase]);

  useEffect(() => {
    if (state.phase !== 'loading_detail' || !state.catalog) return undefined;
    const option = findScenario(state.catalog, state.selectedKey);
    if (!option) {
      dispatch({ type: 'FAILED', message: 'The selected event/scenario identity is missing or ambiguous.' });
      return undefined;
    }
    const controller = new AbortController();
    fetchScenarioDetail(option.event_id, option.scenario_id, controller.signal)
      .then((detail) => dispatch({ type: 'DETAIL_READY', detail }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) dispatch({ type: 'FAILED', message: errorMessage(error) });
      });
    return () => controller.abort();
  }, [state.phase, state.catalog, state.selectedKey]);

  useEffect(() => {
    if (state.phase !== 'loading_raster' || !state.detail || !state.validTimeUtc || !state.band) return undefined;
    const controller = new AbortController();
    const slice = state.detail.series.slices.filter((item) => item.valid_time_utc === state.validTimeUtc);
    if (slice.length !== 1) {
      dispatch({ type: 'FAILED', message: 'The selected UTC timestamp is not unique in this saved scenario.' });
      return undefined;
    }
    const bandReference = slice[0].bands[state.band];
    if (!bandReference) {
      dispatch({ type: 'FAILED', message: 'The selected band is unavailable for this saved timestamp.' });
      return undefined;
    }
    fetchScenarioRaster(state.detail, state.validTimeUtc, state.band, bandReference.sha256, controller.signal)
      .then((raster) => dispatch({ type: 'RASTER_READY', raster, validTimeUtc: state.validTimeUtc, band: state.band }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) dispatch({ type: 'FAILED', message: errorMessage(error) });
      });
    return () => controller.abort();
  }, [state.phase, state.detail, state.validTimeUtc, state.band]);

  useEffect(() => {
    if (reducedMotion && state.playing) dispatch({ type: 'SET_PLAYING', playing: false });
  }, [reducedMotion, state.playing]);

  useEffect(() => {
    if (!state.playing || state.phase !== 'ready' || !state.detail) return undefined;
    const timer = window.setTimeout(() => {
      const next = adjacentSavedTime(state.detail!.series.slices, state.validTimeUtc, 1);
      if (next) dispatch({ type: 'SELECT_SLICE', validTimeUtc: next, band: state.band });
    }, 2400);
    return () => window.clearTimeout(timer);
  }, [state.playing, state.phase, state.detail, state.validTimeUtc, state.band]);

  const series = state.detail?.series ?? null;
  const selectedSlice = series?.slices.find((slice) => slice.valid_time_utc === state.validTimeUtc) ?? null;
  const range = useMemo(() => state.raster ? summarizeValidValues(state.raster.raster) : { min: null, max: null }, [state.raster]);
  const selectionKey = state.selectedKey;
  const viewModel = state.raster as DecodedScenarioRaster | null;

  function selectScenario(key: string) {
    if (key) dispatch({ type: 'SELECT_SCENARIO', key });
  }

  function selectTime(validTimeUtc: string) {
    if (state.band) dispatch({ type: 'SELECT_SLICE', validTimeUtc, band: state.band });
  }

  function selectBand(band: string) {
    if (state.validTimeUtc) dispatch({ type: 'SELECT_SLICE', validTimeUtc: state.validTimeUtc, band });
  }

  function retry() {
    if (state.detail && state.validTimeUtc && state.band) {
      dispatch({ type: 'SELECT_SLICE', validTimeUtc: state.validTimeUtc, band: state.band });
    } else if (selectionKey) {
      dispatch({ type: 'SELECT_SCENARIO', key: selectionKey });
    } else dispatch({ type: 'RETRY_CATALOG' });
  }

  const slices = series?.slices ?? [];
  const currentIndex = slices.findIndex((slice) => slice.valid_time_utc === state.validTimeUtc);

  return (
    <section className="scenario-raster" aria-labelledby="scenario-raster-title">
      <header className="scenario-raster__header">
        <div>
          <span className="overline">A20 · SAVED SCENARIO ASSETS</span>
          <h2 id="scenario-raster-title">Scenario depth explorer</h2>
          <p>Exact saved raster slices only. No live feed, interpolation, or operational guidance.</p>
        </div>
        <span className="scenario-raster__evidence-tag">RESEARCH / SIMULATION EVIDENCE</span>
      </header>

      <div className="scenario-raster__notice" role="note">
        <strong>Assumption-based historical evidence</strong>
        <span>This display is not an observed flood, validated hydraulic result, live warning, or safe-route tool.</span>
      </div>

      <div className="scenario-raster__controls" aria-label="Saved scenario controls">
        <label>
          <span>Saved event and scenario</span>
          <select
            aria-label="Saved event and scenario"
            value={state.selectedKey}
            disabled={!state.catalog || !state.catalog.scenario_series.length}
            onChange={(event) => selectScenario(event.target.value)}
          >
            <option value="">Choose a saved scenario</option>
            {state.catalog?.scenario_series.map((option: ScenarioSeries) => {
              const key = makeScenarioKey(option);
              return <option key={key} value={key}>{option.event_id} · {option.scenario_id} · {option.source_mode}</option>;
            })}
          </select>
        </label>
        <label>
          <span>Exact saved valid time (UTC)</span>
          <select aria-label="Exact saved valid time (UTC)" value={state.validTimeUtc} disabled={!series} onChange={(event) => selectTime(event.target.value)}>
            {series?.slices.map((slice) => <option key={slice.valid_time_utc} value={slice.valid_time_utc}>{slice.valid_time_utc}</option>)}
          </select>
        </label>
        <label>
          <span>Saved member band</span>
          <select aria-label="Saved member band" value={state.band} disabled={!selectedSlice} onChange={(event) => selectBand(event.target.value)}>
            {(['p05', 'p50', 'p95'] as const).filter((band) => selectedSlice?.bands[band]).map((band) => <option key={band} value={band}>{band}</option>)}
          </select>
        </label>
      </div>

      {state.phase === 'loading_catalog' && <div className="scenario-raster__state" role="status" aria-live="polite">Loading the saved A20 catalog…</div>}
      {state.phase === 'catalog_ready' && <div className="scenario-raster__state" role="status">Choose one exact saved event/scenario to load its detail and raster.</div>}
      {state.phase === 'loading_detail' && <div className="scenario-raster__state" role="status" aria-live="polite">Loading exact scenario metadata…</div>}
      {state.phase === 'loading_raster' && <div className="scenario-raster__state" role="status" aria-live="polite">Verifying and decoding the original saved GeoTIFF…</div>}
      {state.phase === 'empty' && <div className="scenario-raster__state" role="status">{state.message}</div>}
      {state.phase === 'error' && (
        <div className="scenario-raster__error" role="alert">
          <div><strong>Saved evidence unavailable</strong><span>{state.message}</span></div>
          <button type="button" className="scenario-raster__secondary" onClick={retry}>Retry this selection</button>
        </div>
      )}

      {state.detail && series && selectedSlice && (
        <>
          <div className="scenario-raster__time-controls" aria-label="Saved timestamp stepping">
            <button type="button" className="scenario-raster__secondary" disabled={currentIndex <= 0 || state.phase === 'loading_raster'} onClick={() => selectTime(adjacentSavedTime(slices, state.validTimeUtc, -1))}>Previous saved time</button>
            <span>Saved slice {Math.max(0, currentIndex + 1)} of {slices.length} · no intermediate times</span>
            <button type="button" className="scenario-raster__secondary" disabled={currentIndex < 0 || currentIndex >= slices.length - 1 || state.phase === 'loading_raster'} onClick={() => selectTime(adjacentSavedTime(slices, state.validTimeUtc, 1))}>Next saved time</button>
            <button
              type="button"
              className="scenario-raster__secondary"
              disabled={reducedMotion || state.phase !== 'ready' || slices.length < 2}
              aria-pressed={state.playing}
              onClick={() => dispatch({ type: 'SET_PLAYING', playing: !state.playing })}
            >{state.playing ? 'Pause saved-time steps' : 'Auto-step saved times'}</button>
          </div>
          {reducedMotion && <p className="scenario-raster__reduced-motion" role="note">Automatic stepping is disabled by your reduced-motion setting; manual saved-time controls remain available.</p>}

          {state.phase === 'ready' && viewModel && (
            <>
              <div className="scenario-raster__view-toggle" role="group" aria-label="Raster display mode">
                <button type="button" aria-pressed={state.view === '3D'} onClick={() => dispatch({ type: 'SET_VIEW', view: '3D' })}>3D depth view</button>
                <button type="button" aria-pressed={state.view === '2D'} onClick={() => dispatch({ type: 'SET_VIEW', view: '2D' })}>2D fallback</button>
              </div>
              {state.view === '3D'
                ? <ScenarioMap3D key={`${state.validTimeUtc}-${state.band}`} raster={viewModel.raster} onError={onMapError} onCellHover={onCellHover} />
                : <Raster2DFallback key={`${state.validTimeUtc}-${state.band}`} raster={viewModel.raster} />}
              {mapError && state.view === '3D' && <div className="scenario-raster__map-error" role="alert"><span>{mapError}</span><button type="button" className="scenario-raster__secondary" onClick={() => dispatch({ type: 'SET_VIEW', view: '2D' })}>Open 2D fallback</button></div>}
              <div className="scenario-raster__legend" aria-label="Depth display legend">
                <strong>Display-only color ramp · metres</strong>
                <span className="scenario-raster__gradient" aria-hidden="true" />
                <div><span>{range.min === null ? 'Unavailable' : `${formatMeters(range.min)} m`}</span><span>{range.max === null ? 'Unavailable' : `${formatMeters(range.max)} m`}</span></div>
                <small>Ramp rescales to this saved slice; Float32 values and source bytes are unchanged. 3D cell height equals the saved depth in metres.</small>
                <small>Hatched / transparent NoData is unknown coverage, not dry or zero.</small>
              </div>
              <p className="scenario-raster__cell-readout" role="status" aria-live="polite">
                {hoveredDepth === null ? 'Move over a valid 600 m cell in the 3D view to inspect its saved Float32 depth.' : `Saved cell depth: ${hoveredDepth} m`}
              </p>
            </>
          )}

          <dl className="scenario-raster__metadata">
            <div><dt>Event / scenario</dt><dd>{series.event_id} · {series.scenario_id}</dd></div>
            <div><dt>Exact saved valid time</dt><dd>{selectedSlice.valid_time_utc} · lead {selectedSlice.lead_hours} h</dd></div>
            <div><dt>Mode / status</dt><dd>{series.source_mode} · {state.detail.status}</dd></div>
            <div><dt>Grid / extent</dt><dd>{state.detail.grid.crs} · {state.detail.grid.pixel_size_m.join(' × ')} m cells · X {formatMeters(viewModel?.raster.bounds[0] ?? state.detail.grid.affine_transform[2])}–{formatMeters(viewModel?.raster.bounds[2] ?? state.detail.grid.affine_transform[2] + state.detail.grid.width * state.detail.grid.pixel_size_m[0])} m; Y {formatMeters(viewModel?.raster.bounds[1] ?? state.detail.grid.affine_transform[5] - state.detail.grid.height * state.detail.grid.pixel_size_m[1])}–{formatMeters(viewModel?.raster.bounds[3] ?? state.detail.grid.affine_transform[5])} m</dd></div>
            <div><dt>Raster / band</dt><dd>{state.band} · {viewModel?.raster.validCount ?? selectedSlice.bands[state.band]?.valid_cell_count} valid cells · {viewModel?.raster.nodataCount ?? selectedSlice.bands[state.band]?.nodata_cell_count} unknown NoData cells</dd></div>
            <div><dt>Units / source metadata</dt><dd>{state.detail.depth_units.value} · {viewModel?.reference.units_basis ?? selectedSlice.bands[state.band]?.units_basis} · TIFF band-unit tag {viewModel?.reference.band_units_metadata ?? 'unset'}</dd></div>
            <div><dt>Parameter spread</dt><dd>{series.member_count} members · {series.band_semantics}</dd></div>
            <div><dt>Rainfall / source</dt><dd>{series.rainfall_semantics}</dd></div>
            <div><dt>Original raster SHA-256</dt><dd className="scenario-raster__hash">{viewModel?.sha256 ?? selectedSlice.bands[state.band]?.sha256 ?? 'Unavailable until verified'}</dd></div>
            <div><dt>Run / source provenance</dt><dd>{state.detail.provenance.forecast_summary && <span>Forecast: {state.detail.provenance.forecast_summary.path} · seed {state.detail.provenance.forecast_summary.seed ?? 'unavailable'} · SHA-256 {state.detail.provenance.forecast_summary.sha256}. </span>}{state.detail.provenance.simulation_summary && <span>Simulation: {state.detail.provenance.simulation_summary.path} · seed {state.detail.provenance.simulation_summary.seed ?? 'unavailable'} · SHA-256 {state.detail.provenance.simulation_summary.sha256}. </span>}{state.detail.provenance.source_hash_status ?? 'Source hash status unavailable.'}</dd></div>
            <div><dt>Mask semantics</dt><dd>{state.detail.nodata.meaning}. Missing cells are never converted to zero.</dd></div>
          </dl>
          <details className="scenario-raster__limitations">
            <summary>Research limitations and provenance notes</summary>
            <p>{state.detail.provenance.forecast_summary?.status ?? state.detail.provenance.simulation_summary?.status ?? 'Saved derived scenario'} · {state.detail.provenance.source_hash_status ?? 'Manifest-backed A20 saved output'}.</p>
            <ul>{state.detail.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
            <p>{state.detail.presentation_policy ?? 'Only exact saved times and original source cells are displayed.'}</p>
          </details>
        </>
      )}
    </section>
  );
}

function ScenarioMap3D({ raster, onError, onCellHover }: { raster: DecodedScenarioRaster['raster']; onError: (message: string) => void; onCellHover: (value: number | null) => void }) {
  const hostRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!hostRef.current) return undefined;
    const webglCanvas = document.createElement('canvas');
    if (!webglCanvas.getContext('webgl2') && !webglCanvas.getContext('webgl')) {
      onError('WebGL is unavailable in this browser. Use the functional 2D raster fallback.');
      return undefined;
    }
    onError('');
    const features = rasterToFeatures(raster);
    const [minX, minY, maxX, maxY] = raster.bounds;
    const corners = [utm44ToWgs84(minX, minY), utm44ToWgs84(maxX, maxY)];
    const map = new MapLibreMap({
      container: hostRef.current,
      style: scenarioStyle,
      center: [(corners[0][0] + corners[1][0]) / 2, (corners[0][1] + corners[1][1]) / 2],
      zoom: 9,
      pitch: 52,
      maxPitch: 60,
      attributionControl: false,
      cooperativeGestures: true,
    });
    map.addControl(new NavigationControl({ showCompass: true, visualizePitch: true }), 'top-right');
    map.getCanvas().setAttribute('aria-label', '3D perspective of original saved Float32 depth cells; each cell is 600 metres and cell height equals its saved depth.');
    map.once('load', () => {
      map.addSource('a20-saved-depth', { type: 'geojson', data: features });
      map.addSource('a20-grid-envelope', {
        type: 'geojson',
        data: {
          type: 'Feature',
          properties: {},
          geometry: { type: 'Polygon', coordinates: [[
            utm44ToWgs84(minX, minY), utm44ToWgs84(maxX, minY), utm44ToWgs84(maxX, maxY),
            utm44ToWgs84(minX, maxY), utm44ToWgs84(minX, minY),
          ]] },
        },
      });
      map.addLayer({
        id: 'a20-grid-envelope-line', type: 'line', source: 'a20-grid-envelope',
        paint: { 'line-color': '#334a4c', 'line-width': 1.4, 'line-dasharray': [3, 2] },
      });
      const min = summarizeValidValues(raster).min ?? 0;
      const max = summarizeValidValues(raster).max ?? min + 0.001;
      map.addLayer({
        id: 'a20-saved-depth-extrusion',
        type: 'fill-extrusion',
        source: 'a20-saved-depth',
        paint: {
          'fill-extrusion-color': ['interpolate', ['linear'], ['get', 'depth_m'], min, '#e2f0e7', min + (max - min) / 2, '#4da8b6', max, '#14538b'],
          'fill-extrusion-height': ['max', 0, ['get', 'depth_m']],
          'fill-extrusion-base': 0,
          'fill-extrusion-opacity': 0.94,
          'fill-extrusion-vertical-gradient': false,
        },
      });
      map.fitBounds(corners as [[number, number], [number, number]], { padding: 44, duration: 0, maxZoom: 10.5 });
      map.setPitch(52);
      map.on('mousemove', 'a20-saved-depth-extrusion', (event: MapMouseEvent) => {
        const feature = map.queryRenderedFeatures(event.point, { layers: ['a20-saved-depth-extrusion'] })[0];
        onCellHover(typeof feature?.properties?.depth_m === 'number' ? feature.properties.depth_m : null);
      });
      map.on('mouseleave', 'a20-saved-depth-extrusion', () => onCellHover(null));
      map.on('error', () => onError('The 3D map could not render this saved raster. Use the 2D fallback.'));
    });
    return () => {
      map.remove();
      onCellHover(null);
    };
  }, [raster, onError, onCellHover]);

  return <div className="scenario-raster__map3d" ref={hostRef} aria-label="MapLibre 3D view of saved A20 raster values" />;
}

function Raster2DFallback({ raster }: { raster: DecodedScenarioRaster['raster'] }) {
  const reactId = useId();
  const patternId = `unknown-${reactId.replace(/:/g, '')}`;
  const { min, max } = summarizeValidValues(raster);
  return (
    <div className="scenario-raster__fallback" aria-label={`2D fallback raster, ${raster.width} columns by ${raster.height} rows, EPSG:32644`}>
      <svg viewBox={`0 0 ${raster.width} ${raster.height}`} role="img" aria-label={`Original ${raster.width} by ${raster.height} saved grid in ${raster.crs}. Hatched cells are unknown NoData coverage.`} shapeRendering="crispEdges">
        <defs><pattern id={patternId} width="1" height="1" patternUnits="userSpaceOnUse"><rect width="1" height="1" fill="#e9e8de" /><path d="M0 0L1 1M-0.25 0.25L0.25 -0.25M0.75 1.25L1.25 0.75" stroke="#9e9c8f" strokeWidth="0.09" /></pattern></defs>
        <rect width={raster.width} height={raster.height} fill={`url(#${patternId})`} />
        {Array.from(raster.validMask, (valid, index) => valid ? (
          <rect
            key={index}
            x={index % raster.width}
            y={Math.floor(index / raster.width)}
            width="1"
            height="1"
            fill={colorForDepth(raster.values[index], min ?? 0, max ?? 0)}
          ><title>{`Row ${Math.floor(index / raster.width) + 1}, column ${index % raster.width + 1}: ${raster.values[index]} m`}</title></rect>
        ) : null)}
        <rect x="0" y="0" width={raster.width} height={raster.height} fill="none" stroke="#334a4c" strokeWidth="0.2" strokeDasharray="1 0.6" />
      </svg>
      <p>North is up · one displayed square per saved 600 m source cell · no raster resampling.</p>
    </div>
  );
}

export { Raster2DFallback };
