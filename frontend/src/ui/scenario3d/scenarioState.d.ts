import type { ScenarioCatalog, ScenarioDetail, DecodedScenarioRaster } from './scenarioApi.js';

export type ScenarioState = {
  phase: 'loading_catalog' | 'catalog_ready' | 'loading_detail' | 'loading_raster' | 'ready' | 'error' | 'empty';
  catalog: ScenarioCatalog | null;
  selectedKey: string;
  detail: ScenarioDetail | null;
  validTimeUtc: string;
  band: string;
  raster: DecodedScenarioRaster | null;
  view: '3D' | '2D';
  playing: boolean;
  message: string;
};
export const initialScenarioState: ScenarioState;
export function scenarioReducer(state: ScenarioState, action: { type: string; [key: string]: any }): ScenarioState;
export function adjacentSavedTime(slices: Array<{ valid_time_utc: string }>, current: string, direction: number): string;
