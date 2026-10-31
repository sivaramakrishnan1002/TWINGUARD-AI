import type { A20Raster } from './geotiff.js';

export type ScenarioBand = {
  sha256: string;
  size_bytes: number;
  units: string;
  units_basis: string;
  valid_cell_count: number;
  nodata_cell_count: number;
  source_status_tag: string;
  band_units_metadata?: string | null;
};
export type ScenarioSeries = {
  event_id: string;
  scenario_id: string;
  source_mode: string;
  member_count: number;
  band_semantics: string;
  rainfall_semantics: string;
  slices: Array<{ valid_time_utc: string; lead_hours: number; valid_time_rule: string; bands: Record<string, ScenarioBand> }>;
};
export type ScenarioDetail = {
  schema_version: string;
  artifact_version: string;
  status: string;
  grid: { width: number; height: number; crs: string; affine_transform: number[]; pixel_size_m: number[] };
  depth_units: { value: string; metadata_note: string };
  nodata: { value: number; meaning: string };
  provenance: { source_hash_status?: string; forecast_summary?: { path: string; sha256: string; seed?: number; status: string }; simulation_summary?: { path: string; sha256: string; seed?: number; status: string } };
  limitations: string[];
  presentation_policy?: string;
  series: ScenarioSeries;
};
export type ScenarioCatalog = { schema_version?: string; artifact_version?: string; scenario_series: ScenarioSeries[] };
export type DecodedScenarioRaster = { raster: A20Raster; reference: ScenarioBand; sha256: string; validTimeUtc: string; band: string };
export class ScenarioRequestError extends Error { status: number | null; }
export const AI_SCENARIO_ORIGIN: string;
export const FRONTEND_ORIGIN: string;
export const ALLOWED_BANDS: readonly string[];
export function fetchScenarioCatalog(signal?: AbortSignal): Promise<ScenarioCatalog>;
export function fetchScenarioDetail(eventId: string, scenarioId: string, signal?: AbortSignal): Promise<ScenarioDetail>;
export function makeScenarioKey(series: ScenarioSeries): string;
export function findScenario(catalog: ScenarioCatalog | null, key: string): ScenarioSeries | null;
export function fetchScenarioRaster(detail: ScenarioDetail, validTimeUtc: string, band: string, expectedHash: string, signal?: AbortSignal): Promise<DecodedScenarioRaster>;
