import { ApiRequestError, type ApiError, type DepthLayer, type RouteRequest, type ResourceSet, type Severity, type SimulationRequest, type StaticLayer, type TwinGuardApi } from './v3types';
import type * as T from './v3types';

/** Same-origin C4 v3 base (nginx and the Vite dev proxy forward /api/ai/v3/ to the AI service). */
export const V3_BASE = '/api/ai/v3';
type Fetcher = typeof fetch;

async function call<R>(fetcher: Fetcher, path: string, init?: RequestInit): Promise<R> {
  const res = await fetcher(`${V3_BASE}${path}`, { ...init, headers: { Accept: 'application/json', ...(init?.body ? { 'Content-Type': 'application/json' } : {}), ...init?.headers } });
  if (!res.ok) {
    let body: ApiError | null = null;
    try { body = (await res.json()) as ApiError; } catch { body = null; }
    throw new ApiRequestError(res.status, body);
  }
  return (await res.json()) as R;
}

const q = (params: Record<string, string | number | boolean | null | undefined>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null) s.set(k, String(v));
  const out = s.toString();
  return out ? `?${out}` : '';
};
const bboxParam = (b?: [number, number, number, number]) => (b ? b.map((v) => v.toFixed(5)).join(',') : undefined);

export function createHttpApi(fetcher: Fetcher = fetch): TwinGuardApi {
  const get = <R>(path: string) => call<R>(fetcher, path);
  return {
    kind: 'api',
    status: () => get<T.EngineStatus>('/status'),
    overview: () => get<T.Overview>('/overview'),
    events: () => get<T.EventList>('/events'),
    weather: (refresh = false) => get<T.Weather>(`/weather${q({ refresh: refresh || undefined })}`),
    createSimulation: (req: SimulationRequest) => call<T.SimulationAccepted>(fetcher, '/simulations', { method: 'POST', body: JSON.stringify(req) }),
    listSimulations: () => get<T.SimulationList>('/simulations?limit=50'),
    getSimulation: (id) => get<T.SimulationRun>(`/simulations/${encodeURIComponent(id)}`),
    depth: (id, frame, layer: DepthLayer = 'depth_mean') => get<T.DepthFrame>(`/simulations/${encodeURIComponent(id)}/depth${q({ frame_index: frame, layer })}`),
    buildings: (id, frame, bbox) => get<T.BuildingDepthPage>(`/simulations/${encodeURIComponent(id)}/buildings${q({ frame_index: frame, bbox: bboxParam(bbox), limit: 5000 })}`),
    wards: (id, frame) => get<T.WardSummaryList>(`/simulations/${encodeURIComponent(id)}/wards${q({ frame_index: frame })}`),
    roads: (id, frame, bbox, threshold) => get<T.RoadFeatureCollection>(`/simulations/${encodeURIComponent(id)}/roads${q({ frame_index: frame, bbox: bboxParam(bbox), blocked_depth_threshold_m: threshold })}`),
    shelters: (id, frame, factor) => get<T.ShelterReport>(`/simulations/${encodeURIComponent(id)}/shelters${q({ frame_index: frame, capacity_factor: factor })}`),
    incidents: (id, frame, min?: Severity) => get<T.IncidentList>(`/simulations/${encodeURIComponent(id)}/incidents${q({ frame_index: frame, min_severity: min })}`),
    emergencyPlan: (id, frame) => get<T.EmergencyPlan>(`/simulations/${encodeURIComponent(id)}/emergency-plan${q({ frame_index: frame })}`),
    comparison: (id, base) => get<T.Comparison>(`/simulations/${encodeURIComponent(id)}/comparison${q({ baseline_run_id: base })}`),
    route: (req: RouteRequest) => call<T.RouteResponse>(fetcher, '/routes', { method: 'POST', body: JSON.stringify(req) }),
    getResources: () => get<T.ResourceSet>('/scenario-resources'),
    putResources: (set: ResourceSet) => call<T.ResourceSet>(fetcher, '/scenario-resources', { method: 'PUT', body: JSON.stringify(set) }),
    staticLayer: (layer: StaticLayer, bbox) => get<T.StaticFeatureCollection>(`/static/${layer}${q({ bbox: bboxParam(bbox), limit: 5000 })}`),
  };
}

/**
 * Picks the live C4 v3 API when GET /v3/status answers 200 with an engine; otherwise the typed
 * fixtures. The check is a single request on load and when the user presses "Retry API".
 */
export async function resolveApi(fixtures: () => Promise<TwinGuardApi>, fetcher: Fetcher = fetch, timeoutMs = 2500): Promise<TwinGuardApi> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetcher(`${V3_BASE}/status`, { signal: controller.signal, headers: { Accept: 'application/json' } });
    if (res.ok) {
      const body = (await res.json()) as Partial<T.EngineStatus>;
      if (typeof body.engine_version === 'string' && typeof body.running === 'boolean') return createHttpApi(fetcher);
    }
  } catch {
    /* not mounted yet: fall through to fixtures */
  } finally {
    clearTimeout(timer);
  }
  return fixtures();
}
