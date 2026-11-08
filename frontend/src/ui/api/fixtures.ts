/**
 * Typed C4 v3 fixtures, used until B47 mounts /v3. Every value is derived from saved project
 * data at runtime; nothing is invented:
 *   runs/depth  saved A05 batch2_v1 hindcast grids (3 events × 5 rainfall scenarios × 5 leads)
 *   wards       GCC ward polygons, aggregated from the saved 600 m depth cells
 *   buildings   OSM footprints (focus areas), depth sampled from the 600 m cell at the centroid
 *   roads       OSM segments, three-state from the cell depth at the segment midpoint
 *   shelters    A10 batch2_v3 candidate facilities (assumed capacities)
 *   incidents   generated from the ward and shelter results (generated: true)
 *   resources   owner-set scenario inputs (SCENARIO_INPUT), stored in this browser
 * Requests that need the flood engine (custom rainfall, forecast) return 503 `unavailable`.
 */
import { A05_SUMMARY, A07_IMPACT, A10, EVENTS, LEADS, SCENARIOS, type EventId, type ScenarioId } from '../evidence/reports';
import { loadEventGrids, NODATA_MM, type EventGrids } from '../evidence/grids';
import { fetchChennaiWeather } from '../weather/openMeteoClient';
import { decodeBase64, haversineM, lonLatToUtm, pointInGeometry, ringAreaM2, utmToLonLat, type TerrainGrid } from './geo';
import * as T from './v3types';

const ORIGIN_X = 390000;
const ORIGIN_Y = 1471620;
const CELL = 600;
const COLS = 69;
const ROWS = 88;
const CELL_KM2 = 0.36;
export const LEVEL_HEIGHT_M = 3;

const generated = import.meta.glob('../evidence/generated/{terrain_cma,wards,shelters,waterways,boundary,gazetteer,focus_*}.json', { import: 'default' });
const cache = new Map<string, Promise<unknown>>();
function loadGenerated<R>(name: string): Promise<R | null> {
  const key = `../evidence/generated/${name}.json`;
  if (!cache.has(key)) cache.set(key, generated[key] ? generated[key]().catch(() => null) : Promise.resolve(null));
  return cache.get(key) as Promise<R | null>;
}
export const staticLayersBundled = () => Object.keys(generated).length > 0;

export interface FocusFile {
  focus_area: T.FocusArea;
  centre: T.LonLat;
  bbox_utm: [number, number, number, number];
  attribution: string;
  height_rule: string;
  /** [osmid, levels|null, centroid easting, centroid northing, flat lon/lat ring] */
  buildings: [string, number | null, number, number, number[]][];
  /** [osmid, node_a, node_b, highway, length_m, flags(1 bridge, 2 tunnel), mid easting, mid northing, flat lon/lat line] */
  roads: [string, number, number, string, number, number, number, number, number[]][];
}
interface ShelterFile { shelters: Omit<T.Shelter, 'reachable'>[] }
export const FOCUS_AREAS: { id: T.FocusArea; label: string; centre: T.LonLat }[] = [
  { id: 'VELACHERY', label: 'Velachery', centre: { lon: 80.2209, lat: 12.9815 } },
  { id: 'ADYAR', label: 'Adyar', centre: { lon: 80.257, lat: 13.0012 } },
  { id: 'T_NAGAR', label: 'T. Nagar', centre: { lon: 80.234, lat: 13.0418 } },
  { id: 'PORUR', label: 'Porur', centre: { lon: 80.157, lat: 13.035 } },
];

export const loadFocus = (area: T.FocusArea) => loadGenerated<FocusFile>(`focus_${area}`);
export const loadWaterways = () => loadGenerated<T.StaticFeatureCollection>('waterways');
export const loadBoundary = () => loadGenerated<T.StaticFeatureCollection>('boundary');
export interface GazPlace { name: string; alt: string[]; type: string; lon: number; lat: number; ward_id: number | null; zone: string | null; rank: number }
export interface GazWard { ward_id: number; name: string; zone: string | null; lon: number; lat: number; bbox: [number, number, number, number] }
export const loadGazetteer = () => loadGenerated<{ places: GazPlace[]; wards: GazWard[] }>('gazetteer');
export async function loadTerrain(): Promise<TerrainGrid | null> {
  const t = await loadGenerated<{ west: number; north: number; step_deg: number; rows: number; cols: number; heights_dm: string }>('terrain_cma');
  return t ? { west: t.west, north: t.north, step: t.step_deg, rows: t.rows, cols: t.cols, dm: new Int16Array(decodeBase64(t.heights_dm)) } : null;
}

/* ───────── run identity ───────── */

function hex8(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i += 1) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return (h >>> 0).toString(16).padStart(8, '0');
}
const stamp = (iso: string) => iso.replace(/[-:]/g, '').replace(/\.\d+/, '').slice(0, 15) + 'Z';
export function savedRunId(event: EventId, scenario: ScenarioId) {
  const start = EVENTS.find((e) => e.id === event)!.windowStartUtc;
  return `evt-${stamp(start)}-${hex8(`${event}|${scenario}`)}`;
}
const RUNS = EVENTS.flatMap((e) => SCENARIOS.map((s) => ({ id: savedRunId(e.id, s.id), event: e.id, scenario: s.id })));
export function runKey(runId: string) {
  const r = RUNS.find((x) => x.id === runId);
  if (!r) throw new T.ApiRequestError(404, { detail: `No saved run ${runId}.`, code: 'not_found' });
  return r;
}
export const DEFAULT_RUN_ID = savedRunId('2015-12-02', 'perfect_foresight_imerg');

const GRID: T.GridSpec = (() => {
  const [w, s] = utmToLonLat(ORIGIN_X, ORIGIN_Y - ROWS * CELL);
  const [e, n] = utmToLonLat(ORIGIN_X + COLS * CELL, ORIGIN_Y);
  return { crs: 'EPSG:32644', origin_x_m: ORIGIN_X, origin_y_m: ORIGIN_Y, cell_size_m: CELL, rows: ROWS, cols: COLS, bbox_wgs84: [+w.toFixed(4), +s.toFixed(4), +e.toFixed(4), +n.toFixed(4)] };
})();

/* ───────── depth helpers ───────── */

const layerBand = (layer: T.DepthLayer) => (layer === 'depth_p05' ? 'p05' : layer === 'depth_p95' ? 'p95' : 'p50');
/** Depth in mm for one frame (0..4) or the per-cell peak over frames (null). */
function depthMm(grids: EventGrids, scenario: ScenarioId, frame: number | null, layer: T.DepthLayer = 'depth_mean'): Uint16Array {
  const band = layerBand(layer);
  if (frame !== null) return grids.get(scenario, LEADS[Math.max(0, Math.min(LEADS.length - 1, frame))], band).mm;
  const peak = new Uint16Array(ROWS * COLS).fill(NODATA_MM);
  for (const l of LEADS) {
    const mm = grids.get(scenario, l, band).mm;
    for (let i = 0; i < mm.length; i += 1) if (mm[i] !== NODATA_MM && (peak[i] === NODATA_MM || mm[i] > peak[i])) peak[i] = mm[i];
  }
  return peak;
}
const cellIndex = (e: number, n: number) => {
  const c = Math.floor((e - ORIGIN_X) / CELL);
  const r = Math.floor((ORIGIN_Y - n) / CELL);
  return c < 0 || r < 0 || c >= COLS || r >= ROWS ? -1 : r * COLS + c;
};
const depthAt = (mm: Uint16Array, e: number, n: number): number | null => { const i = cellIndex(e, n); return i < 0 || mm[i] === NODATA_MM ? null : mm[i] / 1000; };
export function depthClass(d: number | null): T.DepthClass {
  if (d === null) return 'unknown';
  if (d < 0.01) return 'dry';
  if (d < 0.15) return 'lt_0_15';
  if (d < 0.5) return '0_15_to_0_5';
  if (d < 1.0) return '0_5_to_1_0';
  return 'gt_1_0';
}
const SPEED_KMH: Record<string, number> = { motorway: 70, trunk: 60, primary: 50, secondary: 40, tertiary: 35, residential: 25, unclassified: 25, service: 15, living_street: 10 };
const speedFor = (cls: string) => SPEED_KMH[cls.replace(/_link$/, '')] ?? 20;
export function edgeState(depth: number | null, flags: number, threshold: number): { state: T.EdgeState; reason: string | null } {
  if (flags & 1) return { state: 'UNKNOWN', reason: 'bridge_unassessed' };
  if (depth === null) return { state: 'UNKNOWN', reason: 'outside_model_domain' };
  const limit = flags & 2 ? Math.min(threshold, 0.15) : threshold;
  return depth >= limit ? { state: 'ASSESSED_BLOCKED', reason: null } : { state: 'ASSESSED_PASSABLE', reason: null };
}
export function estimatedLevels(ring: number[]) {
  const area = ringAreaM2(ring);
  return Math.max(1, Math.min(6, Math.round(1 + area / 220)));
}

/* ───────── fixture API ───────── */

const RESOURCE_KEY = 'twinguard.v3.scenario-resources';
const DEFAULT_RESOURCES: T.ResourceSet = {
  version: 1,
  updated_at: null,
  resources: [
    { resource_id: 'boat-guindy', type: 'boat', count: 12, base: { name: 'Guindy staging', location: { lon: 80.2206, lat: 13.0067 } }, source_mode: 'SCENARIO_INPUT' },
    { resource_id: 'team-velachery', type: 'rescue_team', count: 6, base: { name: 'Velachery staging', location: { lon: 80.2185, lat: 12.9762 } }, source_mode: 'SCENARIO_INPUT' },
    { resource_id: 'vehicle-tnagar', type: 'vehicle', count: 10, base: { name: 'T. Nagar depot', location: { lon: 80.2337, lat: 13.0405 } }, source_mode: 'SCENARIO_INPUT' },
    { resource_id: 'ambulance-adyar', type: 'ambulance', count: 8, base: { name: 'Adyar depot', location: { lon: 80.2565, lat: 13.0063 } }, source_mode: 'SCENARIO_INPUT' },
    { resource_id: 'pump-porur', type: 'pump', count: 5, base: { name: 'Porur depot', location: { lon: 80.1582, lat: 13.0366 } }, source_mode: 'SCENARIO_INPUT' },
  ],
};
const unavailable = (detail: string) => new T.ApiRequestError(503, { detail, code: 'unavailable' });
const SEVERITY_RANK: Record<T.Severity, number> = { info: 0, watch: 1, warning: 2, critical: 3 };

export async function createFixtureApi(): Promise<T.TwinGuardApi> {
  const wardFc = await loadGenerated<T.StaticFeatureCollection>('wards');
  const shelterFile = await loadGenerated<ShelterFile>('shelters');
  const wardCells = new Map<number, number[]>();
  const wardMeta = new Map<number, { name: string; zone: string | null; centroid: T.LonLat; geometry: { type: string; coordinates: unknown } }>();
  if (wardFc) {
    const cellCentres: [number, number][] = [];
    for (let r = 0; r < ROWS; r += 1) for (let c = 0; c < COLS; c += 1) cellCentres.push(utmToLonLat(ORIGIN_X + c * CELL + CELL / 2, ORIGIN_Y - r * CELL - CELL / 2));
    for (const f of wardFc.features) {
      const id = Number(f.properties.ward_id);
      const ring = ((f.geometry.type === 'Polygon' ? f.geometry.coordinates : (f.geometry.coordinates as number[][][][])[0]) as number[][][])[0];
      const cx = ring.reduce((s, p) => s + p[0], 0) / ring.length;
      const cy = ring.reduce((s, p) => s + p[1], 0) / ring.length;
      const cells: number[] = [];
      cellCentres.forEach(([x, y], i) => { if (pointInGeometry(x, y, f.geometry)) cells.push(i); });
      if (!cells.length) { const [e, n] = lonLatToUtm(cx, cy); const i = cellIndex(e, n); if (i >= 0) cells.push(i); }
      wardCells.set(id, cells);
      wardMeta.set(id, { name: String(f.properties.ward_name), zone: (f.properties.zone as string) ?? null, centroid: { lon: +cx.toFixed(5), lat: +cy.toFixed(5) }, geometry: f.geometry });
    }
  }

  const grids = async (runId: string) => {
    const k = runKey(runId);
    const g = await loadEventGrids(k.event);
    if (!g) throw unavailable('Saved depth grids are not bundled; run tools/ui/export_ui_depth_grids.py.');
    return { k, g };
  };
  const frames = (event: EventId): T.Frame[] => {
    const start = Date.parse(EVENTS.find((e) => e.id === event)!.windowStartUtc);
    return LEADS.map((l, index) => ({ index, valid_time_utc: new Date(start + l * 3600_000).toISOString().replace('.000', ''), elapsed_minutes: l * 60 }));
  };

  const wardSummaries = (mm: Uint16Array, shelterReach?: Map<number, number>): T.WardSummary[] => [...wardCells.entries()].map(([id, cells]) => {
    const vals = cells.map((i) => mm[i]).filter((v) => v !== NODATA_MM).map((v) => v / 1000);
    const meta = wardMeta.get(id)!;
    if (!vals.length) return { ward_id: id, ward_name: meta.name, zone: meta.zone, max_depth_m: null, mean_flooded_depth_m: null, flooded_area_km2: null, flooded_fraction: null, buildings_affected: null, population_exposed: null, roads_blocked_km: null, shelters_reachable: shelterReach?.get(id) ?? null, risk_level: 'low' };
    const flooded = vals.filter((v) => v >= 0.1);
    const max = Math.max(...vals);
    const fraction = flooded.length / vals.length;
    const risk: T.RiskLevel = max >= 1 || fraction >= 0.4 ? 'severe' : max >= 0.5 || fraction >= 0.2 ? 'high' : max >= 0.15 ? 'moderate' : 'low';
    return { ward_id: id, ward_name: meta.name, zone: meta.zone, max_depth_m: +max.toFixed(2), mean_flooded_depth_m: flooded.length ? +(flooded.reduce((a, b) => a + b, 0) / flooded.length).toFixed(2) : 0, flooded_area_km2: +(flooded.length * CELL_KM2).toFixed(2), flooded_fraction: +fraction.toFixed(3), buildings_affected: null, population_exposed: null, roads_blocked_km: null, shelters_reachable: shelterReach?.get(id) ?? null, risk_level: risk };
  });

  const summaryFor = (k: { event: EventId; scenario: ScenarioId }, g: EventGrids): T.SimulationSummary => {
    const peak = depthMm(g, k.scenario, null);
    let max = 0;
    let flooded = 0;
    for (const v of peak) if (v !== NODATA_MM) { max = Math.max(max, v); if (v >= 100) flooded += 1; }
    const leadIdx = LEADS.reduce((best, l, i) => (g.stats(k.scenario, l).area_ge_0_10_km2 > g.stats(k.scenario, LEADS[best]).area_ge_0_10_km2 ? i : best), 0);
    const wards = wardSummaries(peak).filter((w) => (w.max_depth_m ?? 0) >= 0.1).length;
    return { max_depth_m: +(max / 1000).toFixed(2), flooded_area_km2: +(flooded * CELL_KM2).toFixed(2), buildings_affected: null, population_exposed: null, roads_blocked_km: Math.max(...LEADS.map((l) => A07_IMPACT[k.event][k.scenario][l][1])), wards_affected: wardCells.size ? wards : null, peak_time_utc: frames(k.event)[leadIdx].valid_time_utc };
  };

  const runFor = async (runId: string): Promise<T.SimulationRun> => {
    const { k, g } = await grids(runId);
    const ev = EVENTS.find((e) => e.id === k.event)!;
    const sc = SCENARIOS.find((s) => s.id === k.scenario)!;
    return {
      run_id: runId, state: 'completed', mode: 'event', request: { mode: 'event', event_key: k.event, duration_hours: 72, resolution: 'citywide' },
      source_mode: 'SIMULATED', label: `${ev.label.replace(' window', '')} · ${sc.short} (saved)`, created_at: '2026-10-26T00:00:00Z', completed_at: '2026-10-26T00:00:00Z', progress_pct: 100, error: null,
      grid: GRID, frames: frames(k.event), summary: summaryFor(k, g),
      provenance: { engine_version: 'a06-local-inertial-numpy (saved A05 batch2_v1)', run_id: runId, forcing_sha256: null, static_assets_version: 'ui-export-v1', inputs: [{ name: 'rainfall', source: `${sc.label}: GPM IMERG daily, ERA5 hourly shape`, source_mode: 'REPLAY', fetched_at: null, sha256: null }] },
      limitations: ['600 m grid; depths sampled per cell, not per building.', 'depth_mean shows the saved 20-member median (p50).', 'No storm-drain network; hindcast forcing, not a forecast.'],
    };
  };

  const shelterList = async (runId: string, frame: number | null): Promise<T.Shelter[]> => {
    const { k, g } = await grids(runId);
    const mm = depthMm(g, k.scenario, frame);
    return (shelterFile?.shelters ?? []).map((s) => {
      const [e, n] = lonLatToUtm(s.location.lon, s.location.lat);
      const d = depthAt(mm, e, n);
      return { ...s, site_max_depth_m: d === null ? null : +d.toFixed(2), reachable: d !== null && d < 0.15, assigned_population: null, utilisation_pct: null };
    });
  };

  const incidentsFor = async (runId: string, frame: number | null): Promise<T.Incident[]> => {
    const { k, g } = await grids(runId);
    const mm = depthMm(g, k.scenario, frame);
    const t = frame === null ? (summaryFor(k, g).peak_time_utc ?? frames(k.event)[4].valid_time_utc) : frames(k.event)[frame].valid_time_utc;
    const out: T.Incident[] = [];
    for (const w of wardSummaries(mm)) {
      if (w.risk_level === 'low' || w.max_depth_m === null || w.max_depth_m === undefined) continue;
      const wMax = w.max_depth_m;
      const meta = wardMeta.get(w.ward_id)!;
      const severity: T.Severity = w.risk_level === 'severe' ? 'critical' : w.risk_level === 'high' ? 'warning' : 'watch';
      out.push({ incident_id: `inc-w${w.ward_id}`, generated: true, generated_from: 'simulation', type: 'building_flooding', severity, ward_id: w.ward_id, location: meta.centroid, valid_time_utc: t,
        title: `Simulated: max ${wMax.toFixed(2)} m, ${w.flooded_area_km2} km² ≥ 0.10 m in ${w.ward_name}`, metrics: { max_depth_m: wMax, flooded_area_km2: w.flooded_area_km2 ?? null, flooded_fraction: w.flooded_fraction ?? null } });
    }
    for (const s of await shelterList(runId, frame)) {
      const site = s.site_max_depth_m;
      if (site === null || site === undefined || site < 0.15) continue;
      out.push({ incident_id: `inc-s${hex8(s.shelter_id)}`, generated: true, generated_from: 'simulation', type: 'shelter_unreachable', severity: site >= 0.5 ? 'warning' : 'watch', ward_id: s.ward_id ?? null, location: s.location, valid_time_utc: t,
        title: `Simulated: candidate shelter site ${site.toFixed(2)} m · ${s.name}`, metrics: { site_max_depth_m: site } });
    }
    return out.sort((a, b) => SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity] || (b.metrics?.max_depth_m ?? 0) - (a.metrics?.max_depth_m ?? 0));
  };

  const readResources = (): T.ResourceSet => {
    try { const raw = localStorage.getItem(RESOURCE_KEY); if (raw) return JSON.parse(raw) as T.ResourceSet; } catch { /* storage unavailable */ }
    return structuredClone(DEFAULT_RESOURCES);
  };

  let weatherCache: { at: number; value: T.Weather } | null = null;

  const api: T.TwinGuardApi = {
    kind: 'fixture',
    async status() {
      return { engine_version: 'fixture: saved A05 batch2_v1 (B47 not mounted)', static_available: staticLayersBundled(), running: false, running_run_id: null, queue_length: 0, last_completed_run_id: DEFAULT_RUN_ID, weather_min_refresh_interval_s: 600, weather_next_fetch_allowed_at: weatherCache ? new Date(weatherCache.at + 600_000).toISOString() : null };
    },
    async overview() {
      const latest = await runFor(DEFAULT_RUN_ID).catch(() => null);
      const weather = await api.weather().catch(() => null);
      const incidents = latest ? await incidentsFor(DEFAULT_RUN_ID, null) : [];
      const counts: Record<string, number> = {};
      for (const i of incidents) counts[i.severity] = (counts[i.severity] ?? 0) + 1;
      const wards = latest ? (await api.wards(DEFAULT_RUN_ID, null)).wards : [];
      return { generated_at: new Date().toISOString(), badge: 'DEMO / SIMULATION', latest_run: latest, weather, reservoirs: null, incident_counts: counts, top_wards: [...wards].sort((a, b) => (b.max_depth_m ?? -1) - (a.max_depth_m ?? -1)).slice(0, 10) };
    },
    async events() {
      return { events: EVENTS.map((e) => ({ event_key: e.id, label: e.label.replace(' window', ' event'), start_utc: e.windowStartUtc, end_utc: new Date(Date.parse(e.windowStartUtc) + 72 * 3600_000).toISOString().replace('.000', ''), rainfall_source: 'GPM IMERG daily, ERA5 hourly shape', source_mode: 'REPLAY' as const })) };
    },
    async weather(refresh = false) {
      const now = Date.now();
      if (weatherCache && (!refresh || now - weatherCache.at < 600_000)) {
        if (refresh) throw new T.ApiRequestError(429, { detail: `Weather cache is fresh; next fetch allowed in ${Math.ceil((weatherCache.at + 600_000 - now) / 1000)} s.`, code: 'rate_limited', retry_after_s: Math.ceil((weatherCache.at + 600_000 - now) / 1000) });
        return { ...weatherCache.value, cache_age_s: Math.round((now - weatherCache.at) / 1000) };
      }
      try {
        const w = await fetchChennaiWeather();
        const utcOf = (local: string) => new Date(`${local}:00+05:30`).toISOString().replace('.000', '');
        const value: T.Weather = {
          provider: 'open-meteo', model: 'best_match', fetched_at: w.fetchedAt, cache_age_s: 0, min_refresh_interval_s: 600, location: { lon: w.requestedPoint.longitude, lat: w.requestedPoint.latitude },
          current: { temperature_c: w.current.temperatureC, precipitation_mm: w.current.precipitationMm, relative_humidity_pct: w.current.relativeHumidityPercent, wind_speed_kmh: w.current.windSpeedKmh },
          hourly: w.hourly.map((h) => ({ time_utc: utcOf(h.validTimeLocal), precipitation_mm: h.precipitationMm, precipitation_probability_pct: null })),
          source_mode: 'MODEL_FORECAST', attribution: 'Weather data by Open-Meteo.com (CC BY 4.0)',
        };
        weatherCache = { at: now, value };
        return value;
      } catch {
        throw unavailable('Open-Meteo request failed or was rate-limited.');
      }
    },
    async createSimulation(req) {
      if (req.mode === 'event') {
        const ev = EVENTS.find((e) => e.id === req.event_key) ?? EVENTS[0];
        const id = savedRunId(ev.id, 'perfect_foresight_imerg');
        return { run_id: id, state: 'cached', status_url: `/v3/simulations/${id}`, estimated_seconds: 0 };
      }
      if (req.mode === 'what_if' && req.what_if) {
        const base = runKey(req.what_if.base_run_id);
        const target = (A05_SUMMARY[base.event][base.scenario].rain72 * (req.what_if.rainfall_scale_pct ?? 100)) / 100;
        const best = SCENARIOS.reduce((a, s) => (Math.abs(A05_SUMMARY[base.event][s.id].rain72 - target) < Math.abs(A05_SUMMARY[base.event][a.id].rain72 - target) ? s : a), SCENARIOS[0]);
        const id = savedRunId(base.event, best.id);
        return { run_id: id, state: 'cached', status_url: `/v3/simulations/${id}`, estimated_seconds: 0 };
      }
      throw unavailable(req.mode === 'forecast' ? 'Forecast runs need the flood engine API (B47), which is not mounted yet.' : 'Custom-rainfall runs need the flood engine API (B47), which is not mounted yet.');
    },
    async listSimulations() { return { runs: await Promise.all(RUNS.map((r) => runFor(r.id))), next_cursor: null }; },
    getSimulation: runFor,
    async flow() { throw unavailable('Flow velocities are not saved in the A05 batch2_v1 grids; the water animation uses the surface-gradient estimate.'); },
    async depth(runId, frame, layer = 'depth_mean') {
      const { k, g } = await grids(runId);
      if (layer === 'velocity_mps') throw new T.ApiRequestError(422, { detail: 'Velocity is not saved in A05 batch2_v1.', code: 'invalid' });
      const mm = depthMm(g, k.scenario, frame, layer);
      const values: (number | null)[][] = [];
      let max = 0;
      for (let r = 0; r < ROWS; r += 1) {
        const row: (number | null)[] = [];
        for (let c = 0; c < COLS; c += 1) { const v = mm[r * COLS + c]; if (v === NODATA_MM) row.push(null); else { const m = Math.round(v / 10) / 100; max = Math.max(max, m); row.push(m); } }
        values.push(row);
      }
      return { run_id: runId, frame_index: frame, valid_time_utc: frame === null ? null : frames(k.event)[frame].valid_time_utc, unit: 'm', layer, rows: ROWS, cols: COLS, grid: GRID, values, max_value: max };
    },
    async buildings(runId, frame, bbox) {
      const { k, g } = await grids(runId);
      const mm = depthMm(g, k.scenario, frame);
      const out: T.BuildingDepth[] = [];
      let total = 0;
      for (const area of FOCUS_AREAS) {
        const f = await loadFocus(area.id);
        if (!f) continue;
        total += f.buildings.length;
        for (const [id, levels, e, n, ring] of f.buildings) {
          const [lon, lat] = utmToLonLat(e, n);
          if (lon < bbox[0] || lon > bbox[2] || lat < bbox[1] || lat > bbox[3]) continue;
          const d = depthAt(mm, e, n);
          out.push({ building_id: `way/${id}`, centroid: { lon: +lon.toFixed(5), lat: +lat.toFixed(5) }, ward_id: null, height_m: levels ? levels * LEVEL_HEIGHT_M : estimatedLevels(ring) * LEVEL_HEIGHT_M, height_source: levels ? 'osm_levels' : 'estimated', max_depth_m: d === null ? null : +d.toFixed(2), time_of_max_utc: null, depth_class: depthClass(d) });
          if (out.length >= 5000) break;
        }
      }
      return { run_id: runId, frame_index: frame, count: out.length, total, buildings: out, next_cursor: null };
    },
    async wards(runId, frame) {
      const { k, g } = await grids(runId);
      const mm = depthMm(g, k.scenario, frame);
      const reach = new Map<number, number>();
      for (const s of await shelterList(runId, frame)) if (s.reachable && s.ward_id) reach.set(s.ward_id, (reach.get(s.ward_id) ?? 0) + 1);
      return { run_id: runId, frame_index: frame, source_mode: 'SIMULATED', wards: wardSummaries(mm, reach) };
    },
    async roads(runId, frame, bbox, threshold = 0.3) {
      const { k, g } = await grids(runId);
      const mm = depthMm(g, k.scenario, frame);
      const features: T.RoadFeature[] = [];
      for (const area of FOCUS_AREAS) {
        const f = await loadFocus(area.id);
        if (!f) continue;
        for (const [id, , , cls, , flags, e, n, line] of f.roads) {
          if (line[0] < bbox[0] - 0.01 || line[0] > bbox[2] + 0.01 || line[1] < bbox[1] - 0.01 || line[1] > bbox[3] + 0.01) continue;
          const d = depthAt(mm, e, n);
          const { state, reason } = edgeState(d, flags, threshold);
          const coords: [number, number][] = [];
          for (let i = 0; i < line.length; i += 2) coords.push([line[i], line[i + 1]]);
          features.push({ type: 'Feature', geometry: { type: 'LineString', coordinates: coords }, properties: { edge_id: `e:${id}`, state, unknown_reason: reason, depth_m: d === null ? null : +d.toFixed(2), speed_factor: state === 'ASSESSED_PASSABLE' ? +Math.max(0.2, 1 - (d ?? 0) / threshold).toFixed(2) : state === 'ASSESSED_BLOCKED' ? 0 : null, road_class: cls } });
        }
      }
      return { type: 'FeatureCollection', run_id: runId, frame_index: frame, features };
    },
    async shelters(runId, frame, factor = 1) {
      const shelters = await shelterList(runId, frame);
      const k = runKey(runId);
      const a10 = A10.factors.find((f) => f.factor === factor) ?? A10.factors[1];
      const saved = k.scenario === 'perfect_foresight_imerg';
      return { run_id: runId, frame_index: frame, source_mode: 'SIMULATED', capacity_factor: factor, shelters: shelters.map((s) => ({ ...s, capacity_people: Math.round(s.capacity_people * factor) })),
        totals: { demand_people: saved ? Math.round(A10.demand) : null, served_people: saved ? Math.round(a10.served) : null, unserved_people: saved ? Math.round(a10.unserved) : null, unreachable_people: saved ? Math.round(a10.unreachable) : null, reachable_shelters: shelters.filter((s) => s.reachable).length } };
    },
    async incidents(runId, frame, min = 'watch') {
      return { run_id: runId, source_mode: 'SIMULATED', incidents: (await incidentsFor(runId, frame)).filter((i) => SEVERITY_RANK[i.severity] >= SEVERITY_RANK[min]) };
    },
    async emergencyPlan(runId, frame) {
      const set = readResources();
      const left = new Map(set.resources.map((r) => [r.resource_id, r.count]));
      const assignments: T.EmergencyPlan['assignments'] = [];
      const unassigned: string[] = [];
      for (const inc of (await incidentsFor(runId, frame)).filter((i) => i.severity === 'critical' || i.severity === 'warning')) {
        const wanted: T.ResourceType[] = inc.type === 'building_flooding' ? ['boat', 'rescue_team', 'pump'] : ['vehicle', 'ambulance'];
        const options = set.resources.filter((r) => wanted.includes(r.type) && (left.get(r.resource_id) ?? 0) > 0)
          .map((r) => ({ r, d: haversineM([r.base.location.lon, r.base.location.lat], [inc.location.lon, inc.location.lat]) })).sort((a, b) => a.d - b.d);
        if (!options.length) { unassigned.push(inc.incident_id); continue; }
        const { r, d } = options[0];
        const units = Math.min(left.get(r.resource_id)!, inc.severity === 'critical' ? 2 : 1);
        left.set(r.resource_id, left.get(r.resource_id)! - units);
        assignments.push({ incident_id: inc.incident_id, resource_id: r.resource_id, units, eta_s: Math.round((d * 1.4) / (25 / 3.6)), route_status: null });
      }
      return { run_id: runId, frame_index: frame, source_mode: 'SIMULATED', resource_set_version: set.version, assignments, unassigned_incidents: unassigned };
    },
    async comparison(runId, baseId) {
      const base = baseId ?? DEFAULT_RUN_ID;
      const [a, b] = await Promise.all([runFor(runId), runFor(base)]);
      const d = (x?: number | null, y?: number | null) => (x === null || x === undefined || y === null || y === undefined ? null : +(x - y).toFixed(2));
      const [wa, wb] = await Promise.all([api.wards(runId, null), api.wards(base, null)]);
      const before = new Map(wb.wards.map((w) => [w.ward_id, w]));
      const changes = wa.wards.map((w) => ({ ward_id: w.ward_id, max_depth_change_m: d(w.max_depth_m, before.get(w.ward_id)?.max_depth_m), risk_level_before: before.get(w.ward_id)?.risk_level ?? 'low', risk_level_after: w.risk_level }))
        .filter((c) => (c.max_depth_change_m ?? 0) !== 0 || c.risk_level_before !== c.risk_level_after).sort((x, y) => Math.abs(y.max_depth_change_m ?? 0) - Math.abs(x.max_depth_change_m ?? 0));
      const ka = runKey(runId);
      const kb = runKey(base);
      return { run_id: runId, baseline_run_id: base, modifiers: { base_run_id: base, rainfall_scale_pct: +((A05_SUMMARY[ka.event][ka.scenario].rain72 / Math.max(0.01, A05_SUMMARY[kb.event][kb.scenario].rain72)) * 100).toFixed(1) },
        delta: { max_depth_m: d(a.summary?.max_depth_m, b.summary?.max_depth_m), flooded_area_km2: d(a.summary?.flooded_area_km2, b.summary?.flooded_area_km2), buildings_affected: null, population_exposed: null, roads_blocked_km: d(a.summary?.roads_blocked_km, b.summary?.roads_blocked_km), wards_affected: a.summary?.wards_affected != null && b.summary?.wards_affected != null ? a.summary.wards_affected - b.summary.wards_affected : null, peak_time_utc: null },
        ward_changes: changes };
    },
    async route(req) {
      const k = runKey(req.run_id);
      const g = await loadEventGrids(k.event);
      if (!g) throw unavailable('Saved depth grids are not bundled.');
      const area = FOCUS_AREAS.map((a) => ({ a, d: haversineM([a.centre.lon, a.centre.lat], [req.origin.lon, req.origin.lat]) })).sort((x, y) => x.d - y.d)[0].a;
      const f = await loadFocus(area.id);
      if (!f) throw unavailable('Road layer is not bundled; run tools/ui/export_ui_twin3d.py.');
      return routeOnFocus(f, depthMm(g, k.scenario, req.frame_index ?? null), req);
    },
    async getResources() { return readResources(); },
    async putResources(set) {
      const current = readResources();
      if ((set.version ?? 0) !== (current.version ?? 0)) throw new T.ApiRequestError(409, { detail: 'Resource set changed; reload and retry.', code: 'conflict' });
      if (set.resources.length > 200 || set.resources.some((r) => r.count < 0 || r.count > 500)) throw new T.ApiRequestError(422, { detail: 'Counts must be 0–500 and at most 200 resources.', code: 'invalid' });
      const next: T.ResourceSet = { version: (current.version ?? 0) + 1, updated_at: new Date().toISOString().replace(/\.\d+/, ''), resources: set.resources.map((r) => ({ ...r, source_mode: 'SCENARIO_INPUT' })) };
      try { localStorage.setItem(RESOURCE_KEY, JSON.stringify(next)); } catch { /* storage unavailable: keep in memory only */ }
      return next;
    },
    async staticLayer(layer) {
      if (layer === 'wards' && wardFc) return wardFc;
      if (layer === 'shelters') return { type: 'FeatureCollection', layer, source: 'A10 candidate facilities (OSM)', source_mode: 'STATIC_REFERENCE', attribution: '© OpenStreetMap contributors (ODbL)', features: (shelterFile?.shelters ?? []).map((s) => ({ type: 'Feature', geometry: { type: 'Point', coordinates: [s.location.lon, s.location.lat] }, properties: { shelter_id: s.shelter_id, name: s.name, category: s.category, capacity_people: s.capacity_people, capacity_source: s.capacity_source } })), next_cursor: null };
      if (layer === 'focus_areas') return { type: 'FeatureCollection', layer, source: 'UI display boxes (approximate, 5 km)', source_mode: 'STATIC_REFERENCE', features: FOCUS_AREAS.map((a) => ({ type: 'Feature', geometry: { type: 'Point', coordinates: [a.centre.lon, a.centre.lat] }, properties: { focus_area: a.id, label: a.label } })), next_cursor: null };
      throw new T.ApiRequestError(404, { detail: `Static layer ${layer} not bundled in fixtures.`, code: 'not_found' });
    },
  };
  return api;
}

/* ───────── fixture routing (Dijkstra on the focus-area OSM segments) ───────── */

function routeOnFocus(f: FocusFile, mm: Uint16Array, req: T.RouteRequest): T.RouteResponse {
  const threshold = req.blocked_depth_threshold_m ?? 0.3;
  const policy = req.policy ?? 'avoid_blocked';
  const profileSpeed = req.profile === 'walk' ? () => 4.5 : req.profile === 'emergency_vehicle' ? (c: string) => speedFor(c) * 1.2 : speedFor;
  type Edge = { to: number; seg: number; len: number; cls: string; state: T.EdgeState; depth: number | null; forward: boolean };
  const adj = new Map<number, Edge[]>();
  const nodePos = new Map<number, [number, number]>();
  f.roads.forEach(([, a, b, cls, len, flags, e, n, line], seg) => {
    const depth = depthAt(mm, e, n);
    const { state } = edgeState(depth, flags, threshold);
    nodePos.set(a, [line[0], line[1]]);
    nodePos.set(b, [line[line.length - 2], line[line.length - 1]]);
    (adj.get(a) ?? adj.set(a, []).get(a)!).push({ to: b, seg, len, cls, state, depth, forward: true });
    (adj.get(b) ?? adj.set(b, []).get(b)!).push({ to: a, seg, len, cls, state, depth, forward: false });
  });
  const nearest = (p: T.LonLat) => {
    let best = -1;
    let bd = Infinity;
    for (const [id, pos] of nodePos) { const d = haversineM(pos, [p.lon, p.lat]); if (d < bd) { bd = d; best = id; } }
    return { id: best, d: bd };
  };
  const o = nearest(req.origin);
  const t = nearest(req.destination);
  const base = { run_id: req.run_id, frame_index: req.frame_index ?? null, source_mode: 'SIMULATED' as const };
  if (o.d > 800) return { ...base, status: 'origin_unreachable', routes: [], dry_baseline: null };
  if (t.d > 800) return { ...base, status: 'destination_unreachable', routes: [], dry_baseline: null };

  const search = (pol: T.RoutePolicy): T.RouteOption => {
    const allowed = (e: Edge) => pol === 'shortest_dry' || (e.state !== 'ASSESSED_BLOCKED' && (pol !== 'avoid_blocked_and_unknown' || e.state !== 'UNKNOWN'));
    const cost = (e: Edge) => e.len / ((profileSpeed(e.cls) / 3.6) * (pol === 'shortest_dry' || e.state !== 'ASSESSED_PASSABLE' || e.depth === null ? 1 : Math.max(0.2, 1 - e.depth / threshold))) * (e.state === 'UNKNOWN' && pol !== 'shortest_dry' ? 1.5 : 1);
    const dist = new Map<number, number>([[o.id, 0]]);
    const prev = new Map<number, { from: number; edge: Edge }>();
    const heap = new MinHeap();
    heap.push(0, o.id);
    const done = new Set<number>();
    while (heap.size) {
      const [dCur, u] = heap.pop();
      if (done.has(u)) continue;
      done.add(u);
      if (u === t.id) break;
      for (const e of adj.get(u) ?? []) {
        if (!allowed(e)) continue;
        const nd = dCur + cost(e);
        if (nd < (dist.get(e.to) ?? Infinity)) { dist.set(e.to, nd); prev.set(e.to, { from: u, edge: e }); heap.push(nd, e.to); }
      }
    }
    if (!dist.has(t.id)) return { policy: pol, route_status: 'NO_ROUTE', distance_m: null, travel_time_s: null, geometry: null, length_by_state_m: {}, max_depth_on_route_m: null };
    const edges: Edge[] = [];
    for (let v = t.id; v !== o.id; v = prev.get(v)!.from) edges.unshift(prev.get(v)!.edge);
    const coords: [number, number][] = [];
    const byState: Record<T.EdgeState, number> = { ASSESSED_PASSABLE: 0, ASSESSED_BLOCKED: 0, UNKNOWN: 0 };
    let maxDepth: number | null = 0;
    for (const e of edges) {
      const line = f.roads[e.seg][8];
      const pts: [number, number][] = [];
      for (let i = 0; i < line.length; i += 2) pts.push([line[i], line[i + 1]]);
      if (!e.forward) pts.reverse();
      coords.push(...(coords.length ? pts.slice(1) : pts));
      byState[e.state] += e.len;
      maxDepth = e.depth === null || maxDepth === null ? maxDepth : Math.max(maxDepth, e.depth);
    }
    const length = edges.reduce((s, e) => s + e.len, 0);
    const time = edges.reduce((s, e) => s + e.len / (profileSpeed(e.cls) / 3.6), 0);
    const status = pol === 'shortest_dry' ? 'ASSESSED_PASSABLE' : byState.UNKNOWN > 0 ? 'CONDITIONAL' : 'ASSESSED_PASSABLE';
    return { policy: pol, route_status: status, distance_m: Math.round(length), travel_time_s: Math.round(time), geometry: { type: 'LineString', coordinates: coords },
      length_by_state_m: { ASSESSED_PASSABLE: Math.round(byState.ASSESSED_PASSABLE), ASSESSED_BLOCKED: Math.round(byState.ASSESSED_BLOCKED), UNKNOWN: Math.round(byState.UNKNOWN) }, max_depth_on_route_m: pol === 'shortest_dry' ? 0 : maxDepth };
  };
  const main = search(policy);
  const alt = policy === 'avoid_blocked' ? search('avoid_blocked_and_unknown') : null;
  const dry = search('shortest_dry');
  const routes = [main, ...(alt && alt.route_status !== 'NO_ROUTE' && alt.distance_m !== main.distance_m ? [alt] : [])];
  return { ...base, status: main.route_status === 'NO_ROUTE' ? 'no_route' : 'found', routes, dry_baseline: dry };
}

class MinHeap {
  private k: number[] = [];
  private v: number[] = [];
  get size() { return this.k.length; }
  push(key: number, value: number) {
    this.k.push(key); this.v.push(value);
    let i = this.k.length - 1;
    while (i > 0) { const p = (i - 1) >> 1; if (this.k[p] <= this.k[i]) break; this.swap(i, p); i = p; }
  }
  pop(): [number, number] {
    const top: [number, number] = [this.k[0], this.v[0]];
    const lk = this.k.pop()!; const lv = this.v.pop()!;
    if (this.k.length) {
      this.k[0] = lk; this.v[0] = lv;
      let i = 0;
      for (;;) { const l = 2 * i + 1; const r = l + 1; let m = i; if (l < this.k.length && this.k[l] < this.k[m]) m = l; if (r < this.k.length && this.k[r] < this.k[m]) m = r; if (m === i) break; this.swap(i, m); i = m; }
    }
    return top;
  }
  private swap(a: number, b: number) { [this.k[a], this.k[b]] = [this.k[b], this.k[a]]; [this.v[a], this.v[b]] = [this.v[b], this.v[a]]; }
}
