import type { EventId, Lead, ScenarioId } from './reports';

/**
 * Saved A05 depth grids, exported by tools/ui/export_ui_depth_grids.py from the
 * git-ignored rasters under data/features/forecast/batch2_v1/. When the export has
 * not been run (e.g. a fresh clone) no grid is available and the UI says so.
 */

export const NODATA_MM = 65535;
export type Band = 'p05' | 'p50' | 'p95';

export interface GridStats { valid_cells: number; nodata_cells: number; max_m: number; mean_m: number; area_ge_0_10_km2: number; area_ge_0_30_km2: number }
interface LeadEntry { valid_time_utc: string; p05: string; p50: string; p95: string; p50_sha256: string; stats_p50: GridStats }
interface EventFile {
  schema: string;
  event_id: EventId;
  window_start_utc: string;
  grid: { width: number; height: number; cell_size_m: number; crs: string; transform: number[] };
  scenarios: Record<ScenarioId, { leads: Record<string, LeadEntry> }>;
}

export interface DepthGrid {
  width: number;
  height: number;
  cellSizeM: number;
  crs: string;
  /** Depth in millimetres, row-major from the north-west cell; NODATA_MM = outside assessed CMA, not dry. */
  mm: Uint16Array;
  validTimeUtc: string;
  sha256: string;
  stats: GridStats;
}

export interface EventGrids {
  get(scenario: ScenarioId, lead: Lead, band: Band): DepthGrid;
  stats(scenario: ScenarioId, lead: Lead): GridStats;
  validTime(scenario: ScenarioId, lead: Lead): string;
}

const loaders = import.meta.glob<EventFile>('./generated/a05_*.json', { import: 'default' });
const cache = new Map<EventId, Promise<EventGrids | null>>();

export const gridsBundled = () => Object.keys(loaders).length > 0;

function decode(b64: string): Uint16Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return new Uint16Array(bytes.buffer);
}

function wrap(file: EventFile): EventGrids {
  const decoded = new Map<string, Uint16Array>();
  const entry = (scenario: ScenarioId, lead: Lead) => file.scenarios[scenario].leads[String(lead)];
  return {
    get(scenario, lead, band) {
      const key = `${scenario}|${lead}|${band}`;
      const e = entry(scenario, lead);
      if (!decoded.has(key)) decoded.set(key, decode(e[band]));
      return { width: file.grid.width, height: file.grid.height, cellSizeM: file.grid.cell_size_m, crs: file.grid.crs, mm: decoded.get(key)!, validTimeUtc: e.valid_time_utc, sha256: e.p50_sha256, stats: e.stats_p50 };
    },
    stats: (scenario, lead) => entry(scenario, lead).stats_p50,
    validTime: (scenario, lead) => entry(scenario, lead).valid_time_utc,
  };
}

export function loadEventGrids(event: EventId): Promise<EventGrids | null> {
  if (!cache.has(event)) {
    const loader = loaders[`./generated/a05_${event}.json`];
    cache.set(event, loader ? loader().then(wrap).catch(() => null) : Promise.resolve(null));
  }
  return cache.get(event)!;
}
