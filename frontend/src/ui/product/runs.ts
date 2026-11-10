import { FOCUS_AREAS } from '../api/fixtures';
import type * as T from '../api/v3types';

/** Citywide (A25 120 m) vs 30 m focus-area runs; legacy/fixture runs without a request count as citywide. */
export const isFocusRun = (r: T.SimulationRun | null | undefined) => r?.request?.resolution === 'focus';

/** Grid size for labels: the run's own grid when listed, else the C4 v3 defaults for the resolution. */
export function runCellSize(r: T.SimulationRun): number | null {
  if (r.grid?.cell_size_m) return r.grid.cell_size_m;
  if (!r.request) return null;
  return r.request.resolution === 'focus' ? 30 : 120;
}

export function focusAreaLabel(r: T.SimulationRun | null | undefined): string | null {
  const id = r?.request?.focus_area;
  return id ? FOCUS_AREAS.find((a) => a.id === id)?.label ?? id : null;
}

/** e.g. "Chennai floods, Dec 2015 · citywide 120 m · 48 h" or "Velachery focus 30 m · Chennai floods, Dec 2015 · 24 h". */
export function runTitle(r: T.SimulationRun): string {
  const base = r.label ?? r.run_id;
  const cell = runCellSize(r);
  const hours = r.request?.duration_hours ?? (r.frames.length > 1 && r.frame_interval_minutes ? Math.round(((r.frames.length - 1) * r.frame_interval_minutes) / 60) : null);
  const h = hours ? ` · ${hours} h` : '';
  if (isFocusRun(r)) return `${focusAreaLabel(r) ?? 'Focus'} focus${cell ? ` ${cell} m` : ''} · ${base}${h}`;
  return `${base}${r.request ? ` · citywide${cell ? ` ${cell} m` : ''}` : ''}${h}`;
}

/** Completed citywide runs first, then completed focus runs, then running/queued/failed; newest first within each. */
export function sortRuns(runs: T.SimulationRun[]): T.SimulationRun[] {
  const rank = (r: T.SimulationRun) => (r.state === 'completed' ? (isFocusRun(r) ? 1 : 0) : r.state === 'failed' ? 3 : 2);
  return [...runs].sort((a, b) => rank(a) - rank(b) || (b.created_at ?? '').localeCompare(a.created_at ?? ''));
}

/** The citywide run that gives a focus run its city context: same forcing (event/forecast/custom), longest overlap. */
export function contextRunFor(run: T.SimulationRun | null, runs: T.SimulationRun[]): T.SimulationRun | null {
  if (!run || !isFocusRun(run)) return null;
  const city = runs.filter((r) => r.state === 'completed' && !isFocusRun(r) && r.frames.length);
  const sameForcing = (r: T.SimulationRun) => r.mode === run.mode && (run.mode !== 'event' || r.request?.event_key === run.request?.event_key);
  const pool = city.filter(sameForcing);
  const covers = (r: T.SimulationRun) => (r.request?.duration_hours ?? 0) >= (run.request?.duration_hours ?? 0);
  return pool.find(covers) ?? pool[0] ?? null;
}

/** Index of the frame in `run` closest in valid time to `iso` (null when the run has no frames). */
export function nearestFrameByTime(run: T.SimulationRun, iso: string | undefined): number | null {
  if (!run.frames.length) return null;
  if (!iso) return run.frames[0].index;
  const t = Date.parse(iso);
  let best = run.frames[0];
  for (const f of run.frames) if (Math.abs(Date.parse(f.valid_time_utc) - t) < Math.abs(Date.parse(best.valid_time_utc) - t)) best = f;
  return best.index;
}
