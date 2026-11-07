/**
 * Client for the packaged AI-service CFM-DSS reservoir snapshot (CR-016/CR-017, B44).
 * Same-origin path: the packaged nginx (and the Vite dev server) proxy `/api/ai/` to the AI service.
 */
export const AI_API_BASE = '/api/ai';
export const RESERVOIR_HISTORY_PATH = `${AI_API_BASE}/reservoirs/history`;
export const CFM_DASHBOARD_URL = 'https://chennaifloodmonitor.tn.gov.in/HomePage/Dashboard';

export type ReservoirPeriod = 'daily' | 'monthly';

export interface ReservoirRecord {
  reservoirId: string;
  reservoirName: string;
  sourceDate: string;
  waterLevelM: number;
  averageStorageMcm: number;
  responseSha256: string;
  endpoint: string;
}

export interface ReservoirSeries {
  reservoirId: string;
  reservoirName: string;
  records: ReservoirRecord[];
  latest: ReservoirRecord;
}

export interface ReservoirSnapshot {
  period: ReservoirPeriod;
  sourceMode: 'LIVE';
  freshness: 'unknown';
  receivedAt: string;
  series: ReservoirSeries[];
  limitations: string[];
}

export type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export async function fetchReservoirHistory(period: ReservoirPeriod = 'daily', fetcher: FetchLike = fetch, signal?: AbortSignal): Promise<ReservoirSnapshot> {
  const response = await fetcher(`${RESERVOIR_HISTORY_PATH}?period=${period}`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    credentials: 'omit',
    cache: 'no-store',
    signal,
  });
  if (!response.ok) throw new Error(response.status === 503 ? 'Reservoir source is unavailable or returned invalid data.' : `Reservoir service returned HTTP ${response.status}.`);
  let payload: unknown;
  try { payload = await response.json(); }
  catch { throw new Error('Reservoir service response was not valid JSON.'); }
  return parseReservoirHistory(payload, period);
}

export function parseReservoirHistory(value: unknown, period: ReservoirPeriod): ReservoirSnapshot {
  if (!isRecord(value)) throw new Error('Reservoir response must be an object.');
  if (value.history_kind !== period) throw new Error('Reservoir response period did not match the request.');
  if (value.source_mode !== 'LIVE' || value.freshness !== 'unknown') throw new Error('Reservoir response source mode or freshness was not recognised.');
  const receivedAt = typeof value.received_at === 'string' && !Number.isNaN(Date.parse(value.received_at)) ? value.received_at : null;
  if (!receivedAt) throw new Error('Reservoir response has no valid receipt time.');
  if (!Array.isArray(value.records) || value.records.length === 0 || value.records.length > 75) throw new Error('Reservoir response records are missing or out of bounds.');
  const seen = new Set<string>();
  const rows: ReservoirRecord[] = value.records.map((item) => {
    if (!isRecord(item)) throw new Error('Reservoir record must be an object.');
    if (item.observed_at !== null || item.observation_timezone !== 'unknown' || item.time_precision !== 'date') throw new Error('Reservoir record time semantics were not date-only.');
    const sourceDate = typeof item.source_date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(item.source_date) ? item.source_date : null;
    const level = finiteNonNegative(item.water_level_m);
    const storage = finiteNonNegative(item.average_storage_mcm);
    const provenance = isRecord(item.provenance) ? item.provenance : null;
    if (!sourceDate || level === null || storage === null || typeof item.reservoir_id !== 'string' || typeof item.reservoir_name !== 'string' || !provenance) {
      throw new Error('Reservoir record is incomplete.');
    }
    const sha = typeof provenance.response_sha256 === 'string' && /^[a-f0-9]{64}$/.test(provenance.response_sha256) ? provenance.response_sha256 : null;
    if (!sha || typeof provenance.endpoint !== 'string') throw new Error('Reservoir record provenance is incomplete.');
    const key = `${item.reservoir_id}|${sourceDate}`;
    if (seen.has(key)) throw new Error('Reservoir response contains duplicate records.');
    seen.add(key);
    return { reservoirId: item.reservoir_id, reservoirName: item.reservoir_name, sourceDate, waterLevelM: level, averageStorageMcm: storage, responseSha256: sha, endpoint: provenance.endpoint };
  });
  const groups = new Map<string, ReservoirRecord[]>();
  for (const row of rows) groups.set(row.reservoirId, [...(groups.get(row.reservoirId) ?? []), row]);
  const series = [...groups.values()].map((records) => {
    const sorted = [...records].sort((a, b) => a.sourceDate.localeCompare(b.sourceDate));
    return { reservoirId: sorted[0].reservoirId, reservoirName: sorted[0].reservoirName, records: sorted, latest: sorted[sorted.length - 1] };
  }).sort((a, b) => a.reservoirName.localeCompare(b.reservoirName));
  const limitations = Array.isArray(value.limitations) ? value.limitations.filter((item): item is string => typeof item === 'string') : [];
  return { period, sourceMode: 'LIVE', freshness: 'unknown', receivedAt, series, limitations };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function finiteNonNegative(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null;
}
