import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { resolveApi } from '../api/client';
import { createFixtureApi, DEFAULT_RUN_ID, FOCUS_AREAS, loadFocus, loadTerrain, type FocusFile } from '../api/fixtures';
import { lonLatToUtm, utmToLonLat, type TerrainGrid } from '../api/geo';
import type * as T from '../api/v3types';

export interface TwinData {
  api: T.TwinGuardApi | null;
  apiKind: 'api' | 'fixture' | 'connecting';
  runs: T.SimulationRun[];
  run: T.SimulationRun | null;
  runId: string;
  setRunId: (id: string) => void;
  frameIndex: number;
  setFrameIndex: (i: number) => void;
  playing: boolean;
  setPlaying: (p: boolean) => void;
  depth: T.DepthFrame | null;
  wards: T.WardSummary[];
  wardShapes: T.StaticFeatureCollection | null;
  incidents: T.Incident[];
  shelters: T.ShelterReport | null;
  focusArea: T.FocusArea;
  setFocusArea: (a: T.FocusArea) => void;
  focus: FocusFile | null;
  roads: T.RoadFeatureCollection | null;
  terrain: TerrainGrid | null;
  weather: T.Weather | null;
  weatherError: string | null;
  refreshWeather: () => void;
  error: string | null;
  reload: () => void;
  refreshRuns: () => Promise<T.SimulationRun[]>;
}

export function focusBbox(f: FocusFile | null, area: T.FocusArea): [number, number, number, number] {
  if (f) {
    const [w, s] = utmToLonLat(f.bbox_utm[0], f.bbox_utm[1]);
    const [e, n] = utmToLonLat(f.bbox_utm[2], f.bbox_utm[3]);
    return [w, s, e, n];
  }
  const c = FOCUS_AREAS.find((a) => a.id === area)!.centre;
  const [x, y] = lonLatToUtm(c.lon, c.lat);
  const [w, s] = utmToLonLat(x - 2500, y - 2500);
  const [e, n] = utmToLonLat(x + 2500, y + 2500);
  return [w, s, e, n];
}

export function useTwinData(): TwinData {
  const [api, setApi] = useState<T.TwinGuardApi | null>(null);
  const [nonce, setNonce] = useState(0);
  const [runs, setRuns] = useState<T.SimulationRun[]>([]);
  const [runId, setRunId] = useState(DEFAULT_RUN_ID);
  const [frameIndex, setFrameIndex] = useState(3);
  const [playing, setPlaying] = useState(false);
  const [depth, setDepth] = useState<T.DepthFrame | null>(null);
  const [wards, setWards] = useState<T.WardSummary[]>([]);
  const [wardShapes, setWardShapes] = useState<T.StaticFeatureCollection | null>(null);
  const [incidents, setIncidents] = useState<T.Incident[]>([]);
  const [shelters, setShelters] = useState<T.ShelterReport | null>(null);
  const [focusArea, setFocusArea] = useState<T.FocusArea>('VELACHERY');
  const [focus, setFocus] = useState<FocusFile | null>(null);
  const [roads, setRoads] = useState<T.RoadFeatureCollection | null>(null);
  const [terrain, setTerrain] = useState<TerrainGrid | null>(null);
  const [weather, setWeather] = useState<T.Weather | null>(null);
  const [weatherError, setWeatherError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const depthCache = useRef(new Map<string, T.DepthFrame>());

  useEffect(() => {
    let live = true;
    setApi(null);
    resolveApi(createFixtureApi).then((a) => { if (live) setApi(a); }).catch((e) => setError(String(e)));
    loadTerrain().then((t) => { if (live) setTerrain(t); });
    return () => { live = false; };
  }, [nonce]);

  const refreshRuns = useCallback(async () => {
    if (!api) return [];
    const list = (await api.listSimulations()).runs;
    setRuns(list);
    return list;
  }, [api]);

  useEffect(() => {
    if (!api) return;
    refreshRuns().then((list) => {
      if (api.kind === 'api' && list.length && !list.some((r) => r.run_id === runId)) setRunId(list[0].run_id);
    }).catch((e) => setError(e instanceof Error ? e.message : String(e)));
    api.staticLayer('wards').then(setWardShapes).catch(() => setWardShapes(null));
    api.weather().then((w) => { setWeather(w); setWeatherError(null); }).catch((e) => setWeatherError(e instanceof Error ? e.message : 'Weather unavailable'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

  const run = useMemo(() => runs.find((r) => r.run_id === runId) ?? null, [runs, runId]);

  useEffect(() => {
    if (run && frameIndex >= run.frames.length) setFrameIndex(Math.max(0, run.frames.length - 1));
  }, [run, frameIndex]);

  useEffect(() => {
    if (!api) return;
    let live = true;
    const key = `${runId}|${frameIndex}`;
    const cached = depthCache.current.get(key);
    if (cached) setDepth(cached);
    else api.depth(runId, frameIndex).then((d) => { depthCache.current.set(key, d); if (live) setDepth(d); }).catch((e) => { if (live) { setDepth(null); setError(e instanceof Error ? e.message : String(e)); } });
    api.wards(runId, frameIndex).then((w) => live && setWards(w.wards)).catch(() => live && setWards([]));
    api.incidents(runId, frameIndex, 'watch').then((i) => live && setIncidents(i.incidents)).catch(() => live && setIncidents([]));
    api.shelters(runId, frameIndex, 1).then((s) => live && setShelters(s)).catch(() => live && setShelters(null));
    return () => { live = false; };
  }, [api, runId, frameIndex]);

  useEffect(() => {
    let live = true;
    loadFocus(focusArea).then((f) => live && setFocus(f));
    return () => { live = false; };
  }, [focusArea]);

  useEffect(() => {
    if (!api) return;
    let live = true;
    api.roads(runId, frameIndex, focusBbox(focus, focusArea), 0.3).then((r) => live && setRoads(r)).catch(() => live && setRoads(null));
    return () => { live = false; };
  }, [api, runId, frameIndex, focus, focusArea]);

  useEffect(() => {
    const reduce = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (!playing || !run || reduce) return;
    const t = window.setInterval(() => setFrameIndex((i) => (i + 1) % Math.max(1, run.frames.length)), 1800);
    return () => window.clearInterval(t);
  }, [playing, run]);

  const refreshWeather = useCallback(() => {
    if (!api) return;
    api.weather(true).then((w) => { setWeather(w); setWeatherError(null); }).catch((e) => setWeatherError(e instanceof Error ? e.message : 'Weather unavailable'));
  }, [api]);

  return {
    api, apiKind: api ? api.kind : 'connecting', runs, run, runId, setRunId, frameIndex, setFrameIndex, playing, setPlaying,
    depth, wards, wardShapes, incidents, shelters, focusArea, setFocusArea, focus, roads, terrain, weather, weatherError, refreshWeather,
    error, reload: () => setNonce((n) => n + 1), refreshRuns,
  };
}

/** Area (km²) of cells at or above a depth threshold in a depth frame. */
export function frameArea(d: T.DepthFrame | null, threshold = 0.1): number | null {
  if (!d) return null;
  let n = 0;
  for (const row of d.values) for (const v of row) if (v !== null && v >= threshold) n += 1;
  return +((n * d.grid.cell_size_m * d.grid.cell_size_m) / 1e6).toFixed(2);
}

export function depthHistogram(d: T.DepthFrame | null) {
  const bins = [0, 0, 0, 0, 0];
  let nodata = 0;
  if (d) for (const row of d.values) for (const v of row) {
    if (v === null) { nodata += 1; continue; }
    bins[v < 0.15 ? 0 : v < 0.3 ? 1 : v < 0.5 ? 2 : v < 1 ? 3 : 4] += 1;
  }
  return { bins, nodata };
}
