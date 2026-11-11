import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { resolveApi } from '../api/client';
import { createFixtureApi, DEFAULT_RUN_ID, FOCUS_AREAS, loadFocus, loadTerrain, type FocusFile } from '../api/fixtures';
import { lonLatToUtm, utmToLonLat, type TerrainGrid } from '../api/geo';
import type * as T from '../api/v3types';
import { ApiRequestError } from '../api/v3types';
import { contextRunFor, defaultRun, isFocusRun, istTime, nearestFrameByTime, runKindOf, sortRuns } from './runs';

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
  /** Real flow velocities for the shown frame (null: not available for this run, fall back to the estimate). */
  flow: T.FlowFrame | null;
  wards: T.WardSummary[];
  wardShapes: T.StaticFeatureCollection | null;
  incidents: T.Incident[];
  shelters: T.ShelterReport | null;
  focusArea: T.FocusArea;
  setFocusArea: (a: T.FocusArea) => void;
  focus: FocusFile | null;
  roads: T.RoadFeatureCollection | null;
  /** Ask for three-state road colours in this WGS84 view (null = the default focus/run box). */
  setRoadView: (bbox: [number, number, number, number] | null) => void;
  /** For a 30 m focus run: the citywide run used as faded context outside the focus box, and its nearest frame. */
  contextRun: T.SimulationRun | null;
  contextDepth: T.DepthFrame | null;
  terrain: TerrainGrid | null;
  weather: T.Weather | null;
  weatherError: string | null;
  refreshWeather: () => void;
  error: string | null;
  reload: () => void;
  refreshRuns: () => Promise<T.SimulationRun[]>;
  /** Live forecast cycle (GET /v3/live/status, polled every 60 s); null in saved-results mode or before the first poll. */
  live: T.LiveStatus | null;
  /** The run the live cycle currently serves: the latest live run, or the last good one after a failed cycle. */
  liveRunId: string | null;
  /** True once the user picked a non-live run (replay, what-if, ...): new live runs then do not take over the view. */
  pinned: boolean;
  /** Go back to following the live forecast. */
  followLive: () => void;
  /** POST /v3/live/refresh; resolves to a short status message (202 / 429 / 503 handled). */
  refreshLive: () => Promise<string>;
}

/** Playback: minimum time per saved frame (the water cross-fades over ~1.2 s between frames). */
const PLAY_STEP_MS = 1300;
/** Live polling cadence: 60 s normally, 10 s while a cycle runs or right after a manual refresh. */
export const LIVE_POLL_MS = 60_000;
const LIVE_FAST_POLL_MS = 10_000;

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

/** OSM shelters without a usable name arrive as null/'nan'; label them rather than printing 'nan'. */
function cleanShelters(r: T.ShelterReport): T.ShelterReport {
  return { ...r, shelters: r.shelters.map((s) => (!s.name || /^(nan|none|null)$/i.test(String(s.name).trim()) ? { ...s, name: `Unnamed ${s.category ?? 'shelter'} (${s.shelter_id})` } : s)) };
}

/** UNKNOWN reasons meaning "this run has no model cell here", i.e. not assessed by the run (neutral citywide layer instead). */
const NOT_IN_RUN = /^(no_model_cell|outside_model_domain)$/i;

export function useTwinData(): TwinData {
  const [api, setApi] = useState<T.TwinGuardApi | null>(null);
  const [nonce, setNonce] = useState(0);
  const [runs, setRuns] = useState<T.SimulationRun[]>([]);
  const deepLinkRun = useMemo(() => {
    // ?run=<run_id> deep link (demos, screenshots); unknown ids fall back to the first completed run
    try { const r = typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('run') : null; if (r && /^[a-z]+-[0-9TZ]+-[a-f0-9]+$/.test(r)) return r; } catch { /* non-browser */ }
    return null;
  }, []);
  const [runId, setRunIdRaw] = useState(() => deepLinkRun ?? DEFAULT_RUN_ID);
  const setRunId = setRunIdRaw;
  const [live, setLive] = useState<T.LiveStatus | null>(null);
  const [fastPoll, setFastPoll] = useState(false);
  // a deep-linked run is the user's explicit choice
  const [pinned, setPinned] = useState(() => deepLinkRun != null);
  const [frameIndex, setFrameIndex] = useState(() => {
    try { const f = typeof window !== 'undefined' ? Number(new URLSearchParams(window.location.search).get('frame')) : NaN; if (Number.isInteger(f) && f >= 0) return f; } catch { /* non-browser */ }
    return 3;
  });
  const [playing, setPlaying] = useState(false);
  const [depth, setDepth] = useState<T.DepthFrame | null>(null);
  const [flow, setFlow] = useState<T.FlowFrame | null>(null);
  const flowCache = useRef(new Map<string, T.FlowFrame | null>());
  const [wards, setWards] = useState<T.WardSummary[]>([]);
  const [wardShapes, setWardShapes] = useState<T.StaticFeatureCollection | null>(null);
  const [incidents, setIncidents] = useState<T.Incident[]>([]);
  const [shelters, setShelters] = useState<T.ShelterReport | null>(null);
  const [focusArea, setFocusArea] = useState<T.FocusArea>('VELACHERY');
  const [focus, setFocus] = useState<FocusFile | null>(null);
  const [roads, setRoads] = useState<T.RoadFeatureCollection | null>(null);
  const [roadView, setRoadViewRaw] = useState<[number, number, number, number] | null>(null);
  const setRoadView = useCallback((b: [number, number, number, number] | null) => {
    // round to ~1 km so small camera moves do not refetch
    const r = b ? (b.map((v, i) => (i < 2 ? Math.floor(v * 100) / 100 : Math.ceil(v * 100) / 100)) as [number, number, number, number]) : null;
    setRoadViewRaw((cur) => (cur && r && cur.every((v, i) => v === r[i])) || (!cur && !r) ? cur : r);
  }, []);
  const [contextDepth, setContextDepth] = useState<T.DepthFrame | null>(null);
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
    const list = sortRuns((await api.listSimulations()).runs);
    setRuns(list);
    return list;
  }, [api]);

  useEffect(() => {
    if (!api) return;
    Promise.all([refreshRuns(), api.kind === 'api' ? api.liveStatus().catch(() => null) : Promise.resolve(null)]).then(([list, st]) => {
      const done = list.filter((r) => r.state === 'completed');
      if (st) setLive(st);
      // live-first: open on the latest live run (or the last good one after a failed cycle) unless the user deep-linked a run
      const liveTarget = st?.latest?.run_id ?? st?.last_good_run_id ?? null;
      if (api.kind === 'api' && !pinned && liveTarget && done.some((r) => r.run_id === liveTarget)) setRunId(liveTarget);
      else if (api.kind === 'api') { const d = defaultRun(list); if (d && !done.some((r) => r.run_id === runId)) setRunId(d.run_id); }
      // saved-results mode: a deep-linked API run id is not in the bundle, so show the default saved run instead of an error
      else if (!list.some((r) => r.run_id === runId)) setRunId(list.some((r) => r.run_id === DEFAULT_RUN_ID) ? DEFAULT_RUN_ID : (done[0] ?? list[0])?.run_id ?? DEFAULT_RUN_ID);
    }).catch((e) => setError(e instanceof Error ? e.message : String(e)));
    api.staticLayer('wards').then(setWardShapes).catch(() => setWardShapes(null));
    api.weather().then((w) => { setWeather(w); setWeatherError(null); }).catch((e) => setWeatherError(e instanceof Error ? e.message : 'Weather unavailable'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

  const run = useMemo(() => runs.find((r) => r.run_id === runId) ?? null, [runs, runId]);
  const liveRunId = live?.latest?.run_id ?? live?.last_good_run_id ?? null;

  /* live polling: follow new live runs unless the user pinned another run */
  const liveSeen = useRef<string | null>(null);
  useEffect(() => {
    if (!api || api.kind !== 'api') return;
    let stop = false;
    const tick = async () => {
      const st = await api.liveStatus().catch(() => null);
      if (stop || !st) return;
      setLive(st);
      const target = st.latest?.run_id ?? st.last_good_run_id ?? null;
      if (st.state !== 'running' && target && target !== liveSeen.current) {
        const isNew = liveSeen.current !== null;
        liveSeen.current = target;
        if (isNew) {
          const list = await refreshRuns().catch(() => [] as T.SimulationRun[]);
          if (!pinnedRef.current && list.some((r) => r.run_id === target)) setRunId(target);
          // only now drop back to the slow cadence: changing it re-runs this effect (and stops this closure)
          setFastPoll(false);
        }
      }
    };
    tick();
    const t = window.setInterval(tick, fastPoll ? LIVE_FAST_POLL_MS : LIVE_POLL_MS);
    return () => { stop = true; window.clearInterval(t); };
  }, [api, fastPoll, refreshRuns]);
  const pinnedRef = useRef(pinned);
  pinnedRef.current = pinned;

  /** User selection: picking a non-live run pins it; picking the live run follows live again. */
  const selectRun = useCallback((id: string) => {
    const r = runs.find((x) => x.run_id === id);
    setPinned(runKindOf(r) !== 'LIVE_FORECAST');
    setRunId(id);
  }, [runs]);
  const followLive = useCallback(() => { setPinned(false); if (liveRunId) setRunId(liveRunId); }, [liveRunId]);
  const refreshLive = useCallback(async (): Promise<string> => {
    if (!api) return 'Not connected.';
    try {
      const r = await api.liveRefresh();
      setFastPoll(true);
      return r.state === 'already_running' ? 'A live cycle is already running; the view switches when it lands.' : 'Live cycle started; the view switches to the new forecast when it lands.';
    } catch (e) {
      if (e instanceof ApiRequestError && e.status === 429) {
        const wait = e.body?.retry_after_s ?? null;
        const next = live?.manual_refresh?.next_allowed_at ?? (wait != null ? new Date(Date.now() + wait * 1000).toISOString() : null);
        return `Refreshed recently. Next manual refresh allowed at ${istTime(next)} IST${wait != null ? ` (in ${Math.ceil(wait / 60)} min)` : ''}.`;
      }
      if (e instanceof ApiRequestError && e.status === 503) return `Live refresh unavailable: ${e.body?.detail ?? 'live mode disabled or engine busy'}.`;
      return `Live refresh failed: ${e instanceof Error ? e.message : String(e)}.`;
    }
  }, [api, live]);
  // on the live API, only ask for per-run data once the selected id is a listed run (the saved-results default id
  // or a stale deep link would otherwise 404 on depth/flow/wards/incidents/shelters/roads)
  const runKnown = !!api && (api.kind === 'fixture' || !!run);
  const fallBackToCitywide = useCallback(() => {
    const pick = defaultRun(runs);
    if (pick && pick.run_id !== runId) setRunId(pick.run_id);
  }, [runs, runId]);
  const contextRun = useMemo(() => contextRunFor(run, runs), [run, runs]);

  // focus runs: load the full run (listings omit the grid) and switch the focus area to the run's own box
  useEffect(() => {
    if (!api || !run || !isFocusRun(run)) return;
    const area = run.request?.focus_area;
    if (area && area !== focusArea) setFocusArea(area);
    if (run.grid) return;
    let live = true;
    api.getSimulation(run.run_id).then((full) => { if (live) setRuns((list) => list.map((r) => (r.run_id === full.run_id ? { ...r, ...full } : r))); }).catch(() => undefined);
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, run?.run_id, run?.grid]);

  // focus runs: the matching citywide run's depth at the nearest valid time, drawn faded outside the box
  useEffect(() => {
    if (!api || !contextRun || !run) { setContextDepth(null); return; }
    const idx = nearestFrameByTime(contextRun, run.frames.find((f) => f.index === frameIndex)?.valid_time_utc);
    if (idx == null) { setContextDepth(null); return; }
    let live = true;
    const key = `${contextRun.run_id}|${idx}`;
    const cached = depthCache.current.get(key);
    if (cached) setContextDepth(cached);
    else api.depth(contextRun.run_id, idx).then((d) => { depthCache.current.set(key, d); if (live) setContextDepth(d); }).catch(() => live && setContextDepth(null));
    return () => { live = false; };
  }, [api, contextRun, run, frameIndex]);

  useEffect(() => {
    if (run && frameIndex >= run.frames.length) setFrameIndex(Math.max(0, run.frames.length - 1));
  }, [run, frameIndex]);

  /** Depth + flow for one frame, cached; flow failures (503 = run saved without flow output, fixtures) resolve to null. */
  const frameLoads = useRef(new Map<string, Promise<[T.DepthFrame, T.FlowFrame | null]>>());
  const loadFrame = useCallback((id: string, i: number): Promise<[T.DepthFrame, T.FlowFrame | null]> => {
    const key = `${id}|${i}`;
    const d0 = depthCache.current.get(key);
    if (d0 && flowCache.current.has(key)) return Promise.resolve([d0, flowCache.current.get(key) ?? null]);
    const hit = frameLoads.current.get(key);
    if (hit) return hit;
    if (!api) return Promise.reject(new Error('Not connected'));
    const p = Promise.all([
      d0 ? Promise.resolve(d0) : api.depth(id, i),
      flowCache.current.has(key) ? Promise.resolve(flowCache.current.get(key) ?? null) : api.flow(id, i, 4).catch(() => null),
    ]).then(([d, f]) => {
      depthCache.current.set(key, d); flowCache.current.set(key, f);
      // keep the caches bounded (a 97-frame citywide run is ~1 MB per frame of JSON)
      for (const m of [depthCache.current, flowCache.current] as Map<string, unknown>[]) while (m.size > 48) m.delete(m.keys().next().value as string);
      return [d, f] as [T.DepthFrame, T.FlowFrame | null];
    }).finally(() => frameLoads.current.delete(key));
    frameLoads.current.set(key, p);
    return p;
  }, [api]);

  useEffect(() => {
    if (!api || !runKnown) return;
    let live = true;
    // depth and flow land together, so the water texture is built once per frame (not once without and once with flow)
    loadFrame(runId, frameIndex).then(([d, f]) => { if (!live) return; setDepth(d); setFlow(f); }).catch((e) => {
      if (!live) return;
      setDepth(null);
      // a run that vanished from the store (404): show the newest completed citywide run instead of an empty map
      if (e instanceof ApiRequestError && e.status === 404 && api.kind === 'api') { fallBackToCitywide(); return; }
      setError(e instanceof Error ? e.message : String(e));
    });
    api.wards(runId, frameIndex).then((w) => live && setWards(w.wards)).catch(() => live && setWards([]));
    api.incidents(runId, frameIndex, 'watch').then((i) => live && setIncidents(i.incidents)).catch(() => live && setIncidents([]));
    api.shelters(runId, frameIndex, 1).then((s) => live && setShelters(cleanShelters(s))).catch(() => live && setShelters(null));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, runId, frameIndex, runKnown]);

  useEffect(() => {
    let live = true;
    loadFocus(focusArea).then((f) => live && setFocus(f));
    return () => { live = false; };
  }, [focusArea]);

  useEffect(() => {
    if (!api || !runKnown) return;
    let live = true;
    const runBox = run && isFocusRun(run) && run.grid?.bbox_wgs84 ? run.grid.bbox_wgs84 : null;
    let bbox: [number, number, number, number] = roadView ?? runBox ?? focusBbox(focus, focusArea);
    // a focus run only assesses roads inside its box; asking for more fills the 20 000-edge page with NO_MODEL_CELL edges
    if (runBox) {
      bbox = [Math.max(bbox[0], runBox[0]), Math.max(bbox[1], runBox[1]), Math.min(bbox[2], runBox[2]), Math.min(bbox[3], runBox[3])];
      if (bbox[0] >= bbox[2] || bbox[1] >= bbox[3]) { setRoads(null); return () => { live = false; }; }
    }
    const t = window.setTimeout(() => {
      // edges outside the run's model domain are not assessed by this run: leave them to the neutral citywide layer
      api.roads(runId, frameIndex, bbox, 0.3).then((r) => live && setRoads({ ...r, features: r.features.filter((f) => !NOT_IN_RUN.test(f.properties.unknown_reason ?? '')) })).catch(() => live && setRoads(null));
    }, roadView ? 600 : 0);
    return () => { live = false; window.clearTimeout(t); };
  }, [api, runId, frameIndex, focus, focusArea, roadView, run?.grid, runKnown]);

  useEffect(() => {
    const reduce = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (!playing || !run || reduce) return;
    // advance at most every PLAY_STEP_MS and only once the next frame's depth + flow are loaded (no stalls or
    // half-drawn frames); keep the next two frames prefetched
    const n = Math.max(1, run.frames.length);
    let stop = false;
    let last = performance.now();
    const tick = async () => {
      if (stop) return;
      const cur = frameIndexRef.current;
      const next = (cur + 1) % n;
      loadFrame(run.run_id, (next + 1) % n).catch(() => undefined);
      await loadFrame(run.run_id, next).catch(() => undefined);
      if (stop) return;
      const wait = Math.max(0, PLAY_STEP_MS - (performance.now() - last));
      window.setTimeout(() => { if (stop) return; last = performance.now(); setFrameIndex(next); window.setTimeout(tick, 0); }, wait);
    };
    tick();
    return () => { stop = true; };
  }, [playing, run, loadFrame]);
  const frameIndexRef = useRef(frameIndex);
  frameIndexRef.current = frameIndex;

  const refreshWeather = useCallback(() => {
    if (!api) return;
    api.weather(true).then((w) => { setWeather(w); setWeatherError(null); }).catch((e) => setWeatherError(e instanceof Error ? e.message : 'Weather unavailable'));
  }, [api]);

  return {
    api, apiKind: api ? api.kind : 'connecting', runs, run, runId, setRunId: selectRun, frameIndex, setFrameIndex, playing, setPlaying,
    depth, flow, contextRun, contextDepth, setRoadView, wards, wardShapes, incidents, shelters, focusArea, setFocusArea, focus, roads, terrain, weather, weatherError, refreshWeather,
    error, reload: () => setNonce((n) => n + 1), refreshRuns, live, liveRunId, pinned, followLive, refreshLive,
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
