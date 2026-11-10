import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { FOCUS_AREAS, depthClass, type FocusFile } from '../api/fixtures';
import { haversineM, lonLatToUtm } from '../api/geo';
import { ApiRequestError } from '../api/v3types';
import type * as T from '../api/v3types';
import { fetchReservoirHistory, CFM_DASHBOARD_URL, type ReservoirSnapshot } from '../reservoir-live/reservoirClient';
import { TRACKB_BACKTEST, TRACKB_REPLAY } from '../evidence/reports';
import { DEPTH_CLASS_STYLE, EDGE_STYLE, WATER_EXAGGERATION, googleTilesConfigured, imagerySourceLabel, ionConfigured } from '../twin/constants';
import type { GpuInfo, PickInfo, TwinLayers } from '../twin/Twin3D';
import { BarList, Columns, Donut, LineChart } from './Charts';
import { DEFAULT_LAYERS, Icon, LAYER_LABELS, MapStage, Timeline, sampleFrames, type ProductSection } from './ProductExperience';
import { depthHistogram, frameArea, type TwinData } from './state';
import { isAssumptionInput, isFocusRun, runTitle } from './runs';

interface TabProps { data: TwinData; go: (s: ProductSection) => void }

/* ───────── shared bits ───────── */

function Panel({ title, icon, sub, actions, children, className = '' }: { title: string; icon?: string; sub?: string; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`tg-panel ${className}`} aria-label={title}>
      <header className="tg-panel__head"><h2>{icon && <Icon name={icon} />}{title}{sub && <small> {sub}</small>}</h2>{actions && <div className="tg-panel__actions">{actions}</div>}</header>
      <div className="tg-panel__body">{children}</div>
    </section>
  );
}
function Stat({ label, value, unit, note, tone, icon }: { label: string; value: ReactNode; unit?: string; note?: ReactNode; tone?: 'red' | 'amber' | 'cyan' | 'green' | 'violet'; icon?: string }) {
  return (
    <div className={`tg-stat${tone ? ` tg-stat--${tone}` : ''}`}>
      {icon && <span className="tg-stat__icon"><Icon name={icon} size={22} /></span>}
      <div><span className="tg-stat__label">{label}</span><strong className="tg-stat__value">{value}{unit && <small> {unit}</small>}</strong>{note && <span className="tg-stat__note">{note}</span>}</div>
    </div>
  );
}
const fmtN = (v: number | null | undefined, d = 1) => (v === null || v === undefined ? '—' : v.toLocaleString('en-IN', { maximumFractionDigits: d }));
const fmtTime = (iso?: string | null) => (iso ? `${iso.slice(0, 16).replace('T', ' ')} UTC` : '—');
const sevTone = (s: T.Severity) => (s === 'critical' ? 'red' : s === 'warning' ? 'amber' : s === 'watch' ? 'cyan' : 'green');
const RISK_TONE: Record<T.RiskLevel, 'red' | 'amber' | 'cyan' | 'green'> = { severe: 'red', high: 'amber', moderate: 'cyan', low: 'green' };
const topRisk = (wards: T.WardSummary[]): T.RiskLevel => (['severe', 'high', 'moderate', 'low'] as T.RiskLevel[]).find((r) => wards.some((w) => w.risk_level === r)) ?? 'low';
const errText = (e: unknown) => (e instanceof ApiRequestError ? `${e.body?.detail ?? e.message}${e.body?.retry_after_s ? ` (retry in ${e.body.retry_after_s} s)` : ''}` : e instanceof Error ? e.message : String(e));

function roadShares(roads: T.RoadFeatureCollection | null) {
  const km: Record<T.EdgeState, number> = { ASSESSED_PASSABLE: 0, ASSESSED_BLOCKED: 0, UNKNOWN: 0 };
  for (const f of roads?.features ?? []) {
    let m = 0;
    const c = f.geometry.coordinates;
    for (let i = 1; i < c.length; i += 1) m += haversineM(c[i - 1], c[i]);
    km[f.properties.state] += m / 1000;
  }
  return km;
}
function RoadDonut({ roads, size = 130 }: { roads: T.RoadFeatureCollection | null; size?: number }) {
  const km = roadShares(roads);
  const total = km.ASSESSED_PASSABLE + km.ASSESSED_BLOCKED + km.UNKNOWN;
  return <Donut title="Road status" size={size} centre={total ? `${Math.round((km.ASSESSED_PASSABLE / total) * 100)}%` : '—'} sub="passable"
    slices={(Object.keys(km) as T.EdgeState[]).map((k) => ({ label: `${EDGE_STYLE[k].label} (${km[k].toFixed(0)} km)`, value: km[k], color: EDGE_STYLE[k].color }))} />;
}
export function focusStats(focus: FocusFile | null, depth: T.DepthFrame | null) {
  const counts: Record<T.DepthClass, number> = { dry: 0, lt_0_15: 0, '0_15_to_0_5': 0, '0_5_to_1_0': 0, gt_1_0: 0, unknown: 0 };
  let osmLevels = 0;
  if (focus) for (const [, levels, e, n] of focus.buildings) {
    if (levels) osmLevels += 1;
    let d: number | null = null;
    if (depth) {
      const c = Math.floor((e - depth.grid.origin_x_m) / depth.grid.cell_size_m);
      const r = Math.floor((depth.grid.origin_y_m - n) / depth.grid.cell_size_m);
      d = r >= 0 && c >= 0 && r < depth.rows && c < depth.cols ? depth.values[r][c] : null;
    }
    counts[depthClass(d)] += 1;
  }
  return { counts, total: focus?.buildings.length ?? 0, osmLevels, affected: counts['0_15_to_0_5'] + counts['0_5_to_1_0'] + counts.gt_1_0 };
}
/** Inundated area (>= 0.10 m) for up to 12 evenly sampled frames of a run; labels match the sampled frames. */
function useFrameAreas(data: TwinData, runId: string | null) {
  const [state, setState] = useState<{ idx: number[]; labels: string[]; areas: (number | null)[] }>({ idx: [], labels: [], areas: [] });
  useEffect(() => {
    const run = data.runs.find((r) => r.run_id === runId);
    if (!data.api || !run) { setState({ idx: [], labels: [], areas: [] }); return; }
    let live = true;
    const idx = sampleFrames(run.frames.length, 12);
    const labels = idx.map((i) => `T+${Math.round((run.frames[i].elapsed_minutes ?? 0) / 60)}h`);
    Promise.all(idx.map((i) => data.api!.depth(run.run_id, run.frames[i].index).then((d) => frameArea(d, 0.1)).catch(() => null))).then((a) => live && setState({ idx, labels, areas: a }));
    return () => { live = false; };
  }, [data.api, data.runs, runId]);
  return state;
}
const nearestIdx = (idx: number[], f: number) => (idx.length ? idx.reduce((best, v, k) => (Math.abs(v - f) < Math.abs(idx[best] - f) ? k : best), 0) : undefined);
async function waitForRun(api: T.TwinGuardApi, accepted: T.SimulationAccepted, onProgress: (p: string) => void): Promise<T.SimulationRun> {
  for (let i = 0; i < 180; i += 1) {
    const run = await api.getSimulation(accepted.run_id);
    if (run.state === 'completed') return run;
    if (run.state === 'failed') throw new Error(run.error ?? 'Simulation failed.');
    onProgress(`${run.state} ${run.progress_pct != null ? `${Math.round(run.progress_pct)}%` : ''}`);
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error('Simulation did not finish in time.');
}
function RunSelect({ data, label = 'Simulation run', value, onChange, completedOnly = false }: { data: TwinData; label?: string; value?: string; onChange?: (id: string) => void; completedOnly?: boolean }) {
  return (
    <label className="tg-field"><span>{label}</span>
      <select aria-label={label} value={value ?? data.runId} onChange={(e) => (onChange ?? data.setRunId)(e.target.value)}>
        {(() => {
          const list = data.runs.filter((r) => !completedOnly || r.state === 'completed');
          const opt = (r: (typeof list)[number]) => <option key={r.run_id} value={r.run_id}>{runTitle(r)}{r.state !== 'completed' ? ` (${r.state})` : ''}</option>;
          const city = list.filter((r) => !isFocusRun(r));
          const focus = list.filter((r) => isFocusRun(r));
          return focus.length ? <><optgroup label="Citywide runs">{city.map(opt)}</optgroup><optgroup label="Focus-area runs (30 m, one 6 km box)">{focus.map(opt)}</optgroup></> : city.map(opt);
        })()}
        {!data.runs.length && <option value={data.runId}>Loading runs…</option>}
      </select>
    </label>
  );
}
function IncidentRow({ i, onClick, active }: { i: T.Incident; onClick?: () => void; active?: boolean }) {
  return (
    <button type="button" className={`tg-alert tg-alert--${sevTone(i.severity)}${active ? ' is-active' : ''}`} onClick={onClick} aria-pressed={active}>
      <span className="tg-alert__sev">{i.severity}</span>
      <span className="tg-alert__text"><strong>{i.title ?? i.type}</strong><small>{i.type.replace(/_/g, ' ')} · generated · {fmtTime(i.valid_time_utc)}</small></span>
    </button>
  );
}
function PickCard({ pick }: { pick: PickInfo | null }) {
  if (!pick) return <p className="tg-muted">Click a building, road, shelter, incident or water cell on the map.</p>;
  return (
    <div className="tg-pick">
      <strong>{pick.title}</strong>
      <small>{pick.location.lat.toFixed(5)}° N, {pick.location.lon.toFixed(5)}° E</small>
      <dl>{pick.lines.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
    </div>
  );
}

/* ───────── 1 · Situation overview ───────── */

let reservoirSnapshot: ReservoirSnapshot | null = null;

export function OverviewTab({ data, go }: TabProps) {
  const s = data.run?.summary;
  const risk = topRisk(data.wards);
  const area = frameArea(data.depth);
  const affected = data.wards.filter((w) => (w.max_depth_m ?? 0) >= 0.1).length;
  const hourly = (data.weather?.hourly ?? []).slice(0, 24);
  const [snap, setSnap] = useState<ReservoirSnapshot | null>(reservoirSnapshot);
  const [snapState, setSnapState] = useState<string | null>(null);
  const [resources, setResources] = useState<T.ResourceSet | null>(null);
  useEffect(() => { data.api?.getResources().then(setResources).catch(() => setResources(null)); }, [data.api]);
  const fetchSnap = () => {
    setSnapState('Fetching…');
    fetchReservoirHistory('daily').then((x) => { reservoirSnapshot = x; setSnap(x); setSnapState(null); }).catch((e) => setSnapState(`Unavailable: ${errText(e)}`));
  };
  return (
    <div className="tg-layout tg-layout--three">
      <div className="tg-col">
        <Panel title="City Risk Snapshot" icon="gauge" sub="(Chennai)">
          <div className={`tg-risk tg-risk--${RISK_TONE[risk]}`}><Icon name="alert" size={28} /><div><small>Highest ward risk</small><strong>{risk.toUpperCase()}</strong></div><div><small>Current frame</small><strong className="tg-risk__time">{data.run?.frames[data.frameIndex] ? `T+${Math.round((data.run.frames[data.frameIndex].elapsed_minutes ?? 0) / 60)} h` : '—'}</strong></div></div>
          <div className="tg-stats tg-stats--2">
            <Stat icon="waves" label="Max depth (peak)" value={fmtN(s?.max_depth_m, 2)} unit="m" tone="cyan" />
            <Stat icon="pin" label="Area ≥ 0.10 m (now)" value={fmtN(area, 1)} unit="km²" tone="violet" />
            <Stat icon="building" label="Wards affected" value={affected} note={`of ${data.wards.length || '—'}`} tone="amber" />
            <Stat icon="route" label="Roads screened ≥ 0.30 m" value={fmtN(s?.roads_blocked_km, 0)} unit="km" note="peak" tone="red" />
          </div>
        </Panel>
        <Panel title={`Active Alerts (${data.incidents.length})`} icon="alert" actions={<button type="button" className="tg-link" onClick={() => go('emergency')}>View all →</button>}>
          <div className="tg-alerts">{data.incidents.slice(0, 4).map((i) => <IncidentRow key={i.incident_id} i={i} onClick={() => go('emergency')} />)}{!data.incidents.length && <p className="tg-muted">No generated alerts for this frame.</p>}</div>
          <p className="tg-source">Alerts are generated from the simulation, not issued warnings.</p>
        </Panel>
      </div>
      <div className="tg-col tg-col--map">
        <MapStage data={data} title="Chennai flood map" height="lg" />
        <Timeline data={data} />
      </div>
      <div className="tg-col">
        <Panel title="Forecast & Event Timeline" icon="clock">
          <RunSelect data={data} />
          <div className="tg-event-steps">
            {sampleFrames(data.run?.frames.length ?? 0, 6).map((i) => { const f = data.run!.frames[i]; return <button type="button" key={f.index} className={i === data.frameIndex ? 'is-current' : i < data.frameIndex ? 'is-past' : ''} onClick={() => data.setFrameIndex(i)}><i /><b>T+{Math.round((f.elapsed_minutes ?? 0) / 60)}h</b><small>{f.valid_time_utc.slice(5, 16).replace('T', ' ')}</small></button>; })}
          </div>
        </Panel>
        <Panel title="Flood Extent & Depth" icon="waves" sub="(current frame)">
          <div className="tg-stats tg-stats--3">
            <Stat label="Inundation area" value={fmtN(area, 1)} unit="km²" tone="cyan" />
            <Stat label="Max depth" value={fmtN(data.depth?.max_value, 2)} unit="m" tone="violet" />
            <Stat label="Affected wards" value={`${affected}/${data.wards.length || '—'}`} tone="amber" />
          </div>
        </Panel>
        <Panel title="Confidence & Data Freshness" icon="shield">
          <ul className="tg-fresh">
            <li><span>Flood run</span><b>{data.run ? 'SIMULATED' : '—'}</b><small>{data.run?.provenance.engine_version ?? ''}</small></li>
            <li><span>Rainfall forcing</span><b>{data.run?.provenance.inputs[0]?.source_mode ?? '—'}</b><small>{data.run?.provenance.inputs[0]?.source ?? ''}</small></li>
            {(data.run?.provenance.inputs ?? []).filter((i) => /inflow|release/i.test(i.name)).map((i) => <li key={i.name}><span>Reservoir inflow</span><b className="tg-assume">ASSUMPTION</b><small>{i.source ?? i.name} · modelled from storage, not an observed release</small></li>)}
            <li><span>Weather</span><b>{data.weather ? 'MODEL_FORECAST' : 'n/a'}</b><small>{data.weather ? `fetched ${fmtTime(data.weather.fetched_at)}` : data.weatherError ?? 'loading'}</small></li>
            <li><span>Data service</span><b>{data.apiKind === 'api' ? 'C4 v3 API' : 'Saved results'}</b><small>{data.apiKind === 'api' ? 'live engine' : 'B47 API not mounted yet'}</small></li>
          </ul>
        </Panel>
      </div>
      <div className="tg-row4">
        <Panel title="Rainfall Forecast" icon="cloud" sub="(Open-Meteo model, next 24 h)" actions={<button type="button" className="tg-link" onClick={data.refreshWeather}>Refresh</button>}>
          {hourly.length ? <Columns title="Hourly precipitation" unit="mm" labels={hourly.map((h) => `${new Date(h.time_utc).toLocaleTimeString('en-IN', { hour: '2-digit', hour12: false, timeZone: 'Asia/Kolkata' })}h`)} values={hourly.map((h) => h.precipitation_mm ?? null)} />
            : <p className="tg-muted">{data.weatherError ?? 'Loading weather…'}</p>}
          <p className="tg-source">{data.weather?.attribution ?? 'Weather data by Open-Meteo.com (CC BY 4.0)'} · min refresh 10 min</p>
        </Panel>
        <Panel title="Reservoir Summary" icon="dam" sub="(CFM-DSS published snapshot)" actions={<button type="button" className="tg-link" onClick={() => go('reservoirs')}>Details →</button>}>
          {snap ? <table className="tg-table"><thead><tr><th>Reservoir</th><th>Level (m)</th><th>Storage (MCM)</th><th>Date</th></tr></thead>
            <tbody>{snap.series.map((r) => <tr key={r.reservoirId}><th>{r.reservoirName}</th><td>{r.latest.waterLevelM.toFixed(2)}</td><td>{r.latest.averageStorageMcm.toFixed(1)}</td><td>{r.latest.sourceDate}</td></tr>)}</tbody></table>
            : <div className="tg-empty"><p>{snapState ?? 'Not fetched. Snapshots are read only when you ask.'}</p><button type="button" className="tg-btn" onClick={fetchSnap}>Fetch published snapshot</button></div>}
        </Panel>
        <Panel title="Emergency Resources" icon="people" sub="(scenario inputs)" actions={<button type="button" className="tg-link" onClick={() => go('emergency')}>Edit →</button>}>
          <ul className="tg-resources">{(resources?.resources ?? []).map((r) => <li key={r.resource_id}><Icon name={r.type === 'boat' ? 'boat' : r.type === 'rescue_team' ? 'people' : 'route'} /><span>{r.type.replace('_', ' ')}<small>{r.base.name}</small></span><b>{r.count}</b></li>)}</ul>
          <p className="tg-source">SCENARIO_INPUT · owner-set counts</p>
        </Panel>
        <Panel title="Road Status" icon="route" sub={`(${FOCUS_AREAS.find((a) => a.id === data.focusArea)!.label})`} actions={<button type="button" className="tg-link" onClick={() => go('routing')}>Routing →</button>}>
          <RoadDonut roads={data.roads} />
        </Panel>
      </div>
    </div>
  );
}

/* ───────── 2 · Flood simulation ───────── */

export function SimulationTab({ data }: TabProps) {
  const [mode, setMode] = useState<T.SimMode>('event');
  const [events, setEvents] = useState<T.ApiEvent[]>([]);
  const [eventKey, setEventKey] = useState('2015-12-02');
  const [rain, setRain] = useState<number[]>([5, 12, 30, 45, 22, 8, 2, 0, 0, 0, 0, 0]);
  const [duration, setDuration] = useState(48);
  const [resolution, setResolution] = useState<'citywide' | 'focus'>('citywide');
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const areas = useFrameAreas(data, data.runId);
  const hist = depthHistogram(data.depth);
  useEffect(() => { data.api?.events().then((e) => { setEvents(e.events); if (e.events[0]) setEventKey(e.events[0].event_key); }).catch(() => setEvents([])); }, [data.api]);
  const run = async () => {
    if (!data.api) return;
    setBusy(true);
    setStatus('Submitting…');
    try {
      const req: T.SimulationRequest = { mode, duration_hours: duration, resolution, frame_interval_minutes: 30, ...(resolution === 'focus' ? { focus_area: data.focusArea } : {}),
        ...(mode === 'event' ? { event_key: eventKey } : {}),
        ...(mode === 'custom' ? { custom_rainfall: { start_time_utc: new Date().toISOString().slice(0, 13) + ':00:00Z', interval_minutes: 60, values_mm: rain } } : {}) };
      const acc = await data.api.createSimulation(req);
      setStatus(acc.state === 'cached' ? 'Identical run already computed (cached).' : `Run ${acc.state}…`);
      const done = acc.state === 'cached' ? await data.api.getSimulation(acc.run_id) : await waitForRun(data.api, acc, (p) => setStatus(`Running: ${p}`));
      await data.refreshRuns();
      data.setRunId(done.run_id);
      setStatus(`Completed: ${done.label ?? done.run_id}`);
    } catch (e) {
      setStatus(errText(e));
    } finally {
      setBusy(false);
    }
  };
  const s = data.run?.summary;
  const topWards = [...data.wards].filter((w) => w.max_depth_m !== null).sort((a, b) => (b.max_depth_m ?? 0) - (a.max_depth_m ?? 0)).slice(0, 7);
  return (
    <div className="tg-layout tg-layout--three">
      <div className="tg-col">
        <Panel title="Simulation Setup" icon="gauge">
          <fieldset className="tg-radio-row"><legend>Simulation event</legend>
            {(['event', 'custom', 'forecast'] as T.SimMode[]).map((m) => <label key={m}><input type="radio" name="sim-mode" checked={mode === m} onChange={() => setMode(m)} />{m === 'event' ? 'Historical event' : m === 'custom' ? 'Custom rainfall' : 'Open-Meteo forecast'}</label>)}
          </fieldset>
          {mode === 'event' && <label className="tg-field"><span>Event</span><select aria-label="Simulation event" value={eventKey} onChange={(e) => setEventKey(e.target.value)}>{events.map((e) => <option key={e.event_key} value={e.event_key}>{e.label}</option>)}</select></label>}
          {mode === 'custom' && <div className="tg-hyeto"><span>Rainfall input (mm per hour)</span>
            <Columns title="Custom hyetograph" unit="mm" labels={rain.map((_, i) => `${i}h`)} values={rain} height={110} />
            <div className="tg-hyeto__inputs">{rain.map((v, i) => <input key={i} type="number" min={0} max={200} value={v} aria-label={`Rainfall hour ${i}`} onChange={(e) => setRain(rain.map((x, j) => (j === i ? Math.max(0, Math.min(200, Number(e.target.value))) : x)))} />)}</div></div>}
          {mode === 'forecast' && <p className="tg-muted">Fetches the Open-Meteo forecast on demand (cached, at most once every 10 minutes).</p>}
          <div className="tg-field-row">
            <label className="tg-field"><span>Duration</span><select aria-label="Duration" value={duration} onChange={(e) => setDuration(Number(e.target.value))}>{[6, 12, 24, 48, 72].map((h) => <option key={h} value={h}>{h} hours</option>)}</select></label>
            <label className="tg-field"><span>Resolution</span><select aria-label="Resolution" value={resolution} onChange={(e) => setResolution(e.target.value as 'citywide' | 'focus')}><option value="citywide">Citywide</option><option value="focus">Focus area (30 m)</option></select></label>
          </div>
          <button type="button" className="tg-btn tg-btn--primary tg-btn--wide" onClick={run} disabled={busy || !data.api}><Icon name="play" />Run Simulation</button>
          {status && <p className="tg-status" role="status">{status}</p>}
        </Panel>
        <Panel title="Saved Simulations" icon="layers" sub={`(${data.runs.length})`}>
          <div className="tg-runlist">{data.runs.map((r) => <button type="button" key={r.run_id} className={r.run_id === data.runId ? 'is-active' : ''} onClick={() => data.setRunId(r.run_id)}><span>{runTitle(r)}</span><small>{r.summary?.max_depth_m != null ? `${r.summary.max_depth_m.toFixed(2)} m max` : r.state}</small></button>)}</div>
        </Panel>
      </div>
      <div className="tg-col tg-col--map">
        <MapStage data={data} title="Flood simulation map" height="lg" layersInit={{ incidents: false, shelters: false }} />
        <Timeline data={data} />
      </div>
      <div className="tg-col">
        <Panel title={`Simulation Results @ T+${data.run?.frames[data.frameIndex] ? Math.round((data.run.frames[data.frameIndex].elapsed_minutes ?? 0) / 60) : '—'} h`} icon="waves">
          <div className="tg-stats tg-stats--2">
            <Stat label="Flood extent" value={fmtN(frameArea(data.depth), 1)} unit="km²" tone="cyan" />
            <Stat label="Max depth" value={fmtN(data.depth?.max_value, 2)} unit="m" tone="violet" />
            <Stat label="Peak extent" value={fmtN(s?.flooded_area_km2, 1)} unit="km²" note={fmtTime(s?.peak_time_utc)} tone="amber" />
            <Stat label="Wards affected (peak)" value={fmtN(s?.wards_affected, 0)} tone="red" />
            <Stat label="Buildings affected" value={fmtN(s?.buildings_affected, 0)} note={s?.buildings_affected == null ? 'needs engine (A25)' : undefined} />
            <Stat label="Roads screened" value={fmtN(s?.roads_blocked_km, 0)} unit="km" />
          </div>
        </Panel>
        <Panel title="Run Details" icon="shield">
          <ul className="tg-fresh">
            <li><span>Run</span><b>{data.run?.state ?? '—'}</b><small>{data.run?.run_id}</small></li>
            <li><span>Engine</span><b>SIMULATED</b><small>{data.run?.provenance.engine_version}</small></li>
            {data.run?.provenance.device?.used && <li><span>Compute</span><b>{data.run.provenance.device.used.toUpperCase()}</b><small>{data.run.provenance.device.name ?? ''}{data.run.provenance.device.fallback_reason ? ` · fallback: ${data.run.provenance.device.fallback_reason}` : ''}</small></li>}
            <li><span>Water motion</span><b>{data.flow ? 'MODELLED /flow' : 'ESTIMATED'}</b><small>{data.flow ? `u/v velocity, frame ${data.flow.frame_index}, stride ${data.flow.stride}` : 'no flow output for this run; surface-slope estimate'}</small></li>
            <li><span>Grid</span><b>{data.run?.grid ? `${data.run.grid.cell_size_m} m` : '—'}</b><small>{data.run?.grid ? `${data.run.grid.cols} × ${data.run.grid.rows} · ${data.run.grid.crs}` : ''}</small></li>
            {(data.run?.limitations ?? []).slice(0, 3).map((l) => <li key={l}><span>Note</span><small>{l}</small></li>)}
          </ul>
        </Panel>
      </div>
      <div className="tg-row4">
        <Panel title="Inundation Area" icon="waves" sub="(≥ 0.10 m by frame)">
          <LineChart title="Inundation area by frame" unit="km²" xLabels={areas.labels} series={[{ name: 'Area', values: areas.areas.map((a) => a ?? 0), color: '#2fa8ff' }]} highlightIndex={nearestIdx(areas.idx, data.frameIndex)} height={170} />
        </Panel>
        <Panel title="Depth Distribution" icon="layers" sub="(model cells)">
          <Donut title="Depth distribution" centre={`${fmtN(frameArea(data.depth, 0.01), 0)}`} sub="km² wet" slices={[
            { label: '< 0.15 m', value: hist.bins[0], color: '#7fe3ff' }, { label: '0.15 – 0.3 m', value: hist.bins[1], color: '#2fa8ff' }, { label: '0.3 – 0.5 m', value: hist.bins[2], color: '#1f5cff' }, { label: '0.5 – 1.0 m', value: hist.bins[3], color: '#9b5cff' }, { label: '> 1.0 m', value: hist.bins[4], color: '#ff3b8a' }]} />
        </Panel>
        <Panel title="Most Affected Wards" icon="building">
          <BarList title="Ward max depth" unit="m" rows={topWards.map((w) => ({ label: `${w.ward_name}`, value: w.max_depth_m ?? null, color: w.risk_level === 'severe' ? '#ff3b5c' : w.risk_level === 'high' ? '#ff9f43' : '#2fa8ff' }))} />
        </Panel>
        <Panel title="Rainfall Forcing" icon="cloud">
          <ul className="tg-fresh">{(data.run?.provenance.inputs ?? []).map((i) => <li key={i.name}><span>{i.name.replace(/_/g, ' ')}</span><b>{i.source_mode}{isAssumptionInput(i) && /inflow|release/i.test(i.name) && <em className="tg-assume"> · ASSUMPTION</em>}</b><small>{i.source}</small></li>)}</ul>
        </Panel>
      </div>
    </div>
  );
}

/* ───────── 3 · Emergency support ───────── */

export function EmergencyTab({ data }: TabProps) {
  const [selected, setSelected] = useState<string | null>(null);
  const [plan, setPlan] = useState<T.EmergencyPlan | null>(null);
  const [resources, setResources] = useState<T.ResourceSet | null>(null);
  const [draft, setDraft] = useState<Record<string, number>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [pick, setPick] = useState<PickInfo | null>(null);
  useEffect(() => { data.api?.getResources().then((r) => { setResources(r); setDraft(Object.fromEntries(r.resources.map((x) => [x.resource_id, x.count]))); }).catch(() => setResources(null)); }, [data.api]);
  useEffect(() => { data.api?.emergencyPlan(data.runId, data.frameIndex).then(setPlan).catch(() => setPlan(null)); }, [data.api, data.runId, data.frameIndex, resources?.version]);
  const inc = data.incidents.find((i) => i.incident_id === selected) ?? data.incidents[0] ?? null;
  const shelters = data.shelters?.shelters ?? [];
  const near = inc ? shelters.filter((s) => s.reachable).map((s) => ({ s, d: haversineM([s.location.lon, s.location.lat], [inc.location.lon, inc.location.lat]) })).sort((a, b) => a.d - b.d).slice(0, 4) : [];
  const save = async () => {
    if (!data.api || !resources) return;
    try {
      const next = await data.api.putResources({ ...resources, resources: resources.resources.map((r) => ({ ...r, count: draft[r.resource_id] ?? r.count })) });
      setResources(next);
      setMsg(`Saved scenario resources (version ${next.version}).`);
    } catch (e) { setMsg(errText(e)); }
  };
  const used = new Map<string, number>();
  for (const a of plan?.assignments ?? []) used.set(a.resource_id, (used.get(a.resource_id) ?? 0) + a.units);
  const exposure = [...data.wards].filter((w) => (w.flooded_fraction ?? 0) > 0).sort((a, b) => (b.flooded_fraction ?? 0) - (a.flooded_fraction ?? 0)).slice(0, 6);
  return (
    <div className="tg-layout tg-layout--three">
      <div className="tg-col">
        <Panel title={`Incident Priority Queue (${data.incidents.length})`} icon="alert">
          <div className="tg-alerts tg-alerts--scroll">{data.incidents.map((i) => <IncidentRow key={i.incident_id} i={i} active={inc?.incident_id === i.incident_id} onClick={() => setSelected(i.incident_id)} />)}{!data.incidents.length && <p className="tg-muted">No generated incidents for this frame.</p>}</div>
          <p className="tg-source">Generated from the simulation (generated: true). Not real reports.</p>
        </Panel>
      </div>
      <div className="tg-col tg-col--map">
        <MapStage data={data} title="Emergency map" height="lg" layersInit={{ wards: true, buildings: true }} onPick={setPick} flyKey={inc?.incident_id}
          center={inc ? { lon: inc.location.lon, lat: inc.location.lat, range: 6000 } : null} />
        <Timeline data={data} compact />
      </div>
      <div className="tg-col">
        <Panel title={inc ? 'Selected Incident' : 'Selected Incident — none'} icon="siren">
          {inc ? <>
            <div className={`tg-incident tg-incident--${sevTone(inc.severity)}`}><strong>{inc.title}</strong><small>{inc.type.replace(/_/g, ' ')} · {inc.severity.toUpperCase()} · {fmtTime(inc.valid_time_utc)}</small></div>
            <div className="tg-stats tg-stats--3">{Object.entries(inc.metrics ?? {}).slice(0, 3).map(([k, v]) => <Stat key={k} label={k.replace(/_/g, ' ')} value={fmtN(v, 2)} />)}</div>
            <h3 className="tg-h3">Recommended assignment (greedy, nearest scenario resource)</h3>
            <ul className="tg-actions">{(plan?.assignments ?? []).filter((a) => a.incident_id === inc.incident_id).map((a) => <li key={a.resource_id}><b>{a.units} × {resources?.resources.find((r) => r.resource_id === a.resource_id)?.type.replace('_', ' ') ?? a.resource_id}</b> from {resources?.resources.find((r) => r.resource_id === a.resource_id)?.base.name}{a.eta_s != null && <> · ETA ≈ {Math.round(a.eta_s / 60)} min</>}</li>)}
              {plan && !plan.assignments.some((a) => a.incident_id === inc.incident_id) && <li className="tg-muted">No resource assigned (watch-level or resources exhausted).</li>}</ul>
            <h3 className="tg-h3">Nearest reachable shelters</h3>
            <ul className="tg-actions">{near.map(({ s, d }) => <li key={s.shelter_id}><b>{s.name}</b> · {(d / 1000).toFixed(1)} km · cap. {s.capacity_people} ({s.capacity_source})</li>)}{!near.length && <li className="tg-muted">No reachable candidate shelter found.</li>}</ul>
          </> : <p className="tg-muted">Select an incident.</p>}
        </Panel>
        <Panel title="Map Inspector" icon="search"><PickCard pick={pick} /></Panel>
      </div>
      <div className="tg-row4">
        <Panel title="Relief Shelter Capacity & Reachability" icon="shelter" className="tg-span-2">
          <div className="tg-table-wrap tg-table-wrap--scroll"><table className="tg-table"><thead><tr><th>Shelter</th><th>Ward</th><th>Capacity</th><th>Site depth</th><th>Status</th></tr></thead>
            <tbody>{[...shelters].sort((a, b) => (b.site_max_depth_m ?? -1) - (a.site_max_depth_m ?? -1)).slice(0, 40).map((s) => <tr key={s.shelter_id}><th>{s.name}</th><td>{s.ward_id ?? '—'}</td><td>{s.capacity_people} <small>{s.capacity_source}</small></td><td>{s.site_max_depth_m == null ? 'Unknown' : `${s.site_max_depth_m.toFixed(2)} m`}</td><td><span className={`tg-pill ${s.reachable ? 'is-ok' : 'is-bad'}`}>{s.reachable ? 'Reachable' : 'Not reachable'}</span></td></tr>)}</tbody></table></div>
          <p className="tg-source">{data.shelters?.totals.reachable_shelters ?? 0} of {shelters.length} candidate sites dry · capacities assumed (A10)</p>
        </Panel>
        <Panel title="Emergency Resources (scenario)" icon="boat">
          <table className="tg-table"><thead><tr><th>Resource</th><th>Total</th><th>Assigned</th><th>Base</th></tr></thead>
            <tbody>{(resources?.resources ?? []).map((r) => <tr key={r.resource_id}><th>{r.type.replace('_', ' ')}</th><td><input className="tg-num" type="number" min={0} max={500} aria-label={`${r.type} count`} value={draft[r.resource_id] ?? r.count} onChange={(e) => setDraft({ ...draft, [r.resource_id]: Number(e.target.value) })} /></td><td>{used.get(r.resource_id) ?? 0}</td><td>{r.base.name}</td></tr>)}</tbody></table>
          <div className="tg-row-actions"><button type="button" className="tg-btn" onClick={save}>Save scenario inputs</button>{msg && <small role="status">{msg}</small>}</div>
        </Panel>
        <Panel title="Highest Flooded Share" icon="people" sub="(wards)">
          <BarList title="Flooded fraction by ward" unit="%" max={100} rows={exposure.map((w) => ({ label: w.ward_name, value: +((w.flooded_fraction ?? 0) * 100).toFixed(1), color: w.risk_level === 'severe' ? '#ff3b5c' : '#ff9f43' }))} />
          <p className="tg-source">Population exposure needs the engine API (WorldPop at run time).</p>
        </Panel>
      </div>
    </div>
  );
}

/* ───────── 4 · Road routing ───────── */

export function RoutingTab({ data }: TabProps) {
  const area = FOCUS_AREAS.find((a) => a.id === data.focusArea)!;
  const shelters = useMemo(() => (data.shelters?.shelters ?? []).filter((s) => haversineM([s.location.lon, s.location.lat], [area.centre.lon, area.centre.lat]) < 2600), [data.shelters, area]);
  const [origin, setOrigin] = useState<T.LonLat>(area.centre);
  const [destId, setDestId] = useState<string>('');
  const [clickSets, setClickSets] = useState<'origin' | 'destination' | null>(null);
  const [customDest, setCustomDest] = useState<T.LonLat | null>(null);
  const [policy, setPolicy] = useState<T.RoutePolicy>('avoid_blocked');
  const [profile, setProfile] = useState<T.RouteProfile>('emergency_vehicle');
  const [threshold, setThreshold] = useState(0.3);
  const [result, setResult] = useState<T.RouteResponse | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [pick, setPick] = useState<PickInfo | null>(null);
  useEffect(() => { setOrigin(area.centre); setResult(null); setCustomDest(null); }, [area]);
  useEffect(() => { if (!destId && shelters.length) setDestId(shelters.find((s) => s.reachable)?.shelter_id ?? shelters[0].shelter_id); }, [shelters, destId]);
  const dest = customDest ?? shelters.find((s) => s.shelter_id === destId)?.location ?? null;
  const find = async () => {
    if (!data.api || !dest) return;
    setStatus('Searching…');
    try {
      const r = await data.api.route({ run_id: data.runId, frame_index: data.frameIndex, origin, destination: dest, policy, profile, blocked_depth_threshold_m: threshold });
      setResult(r);
      setStatus(r.status === 'found' ? null : r.status.replace(/_/g, ' '));
    } catch (e) { setStatus(errText(e)); }
  };
  const routes = result ? [...result.routes, ...(result.dry_baseline?.geometry ? [] : [])] : null;
  const main = result?.routes[0];
  const roadKm = roadShares(data.roads);
  return (
    <div className="tg-layout tg-layout--three">
      <div className="tg-col">
        <Panel title="Route Request" icon="route" sub="(evacuation / mobility)">
          <div className="tg-field"><span>Origin</span><div className="tg-inline"><code>{origin.lat.toFixed(4)}, {origin.lon.toFixed(4)}</code><button type="button" className={`tg-btn tg-btn--small${clickSets === 'origin' ? ' is-on' : ''}`} onClick={() => setClickSets(clickSets === 'origin' ? null : 'origin')}>Pick on map</button></div></div>
          <label className="tg-field"><span>Destination (relief shelter)</span><select aria-label="Destination shelter" value={customDest ? '' : destId} onChange={(e) => { setCustomDest(null); setDestId(e.target.value); }}>
            {customDest && <option value="">Map point {customDest.lat.toFixed(4)}, {customDest.lon.toFixed(4)}</option>}
            {shelters.map((s) => <option key={s.shelter_id} value={s.shelter_id}>{s.name} {s.reachable ? '' : '(site wet)'}</option>)}
          </select></label>
          <button type="button" className={`tg-btn tg-btn--small${clickSets === 'destination' ? ' is-on' : ''}`} onClick={() => setClickSets(clickSets === 'destination' ? null : 'destination')}>Pick destination on map</button>
          <label className="tg-field"><span>Mode / vehicle</span><select aria-label="Profile" value={profile} onChange={(e) => setProfile(e.target.value as T.RouteProfile)}><option value="emergency_vehicle">Ambulance / emergency</option><option value="car">Car</option><option value="walk">Walk</option></select></label>
          <fieldset className="tg-radio-col"><legend>Routing policy</legend>
            {([['avoid_blocked', 'Avoid assessed-blocked roads'], ['avoid_blocked_and_unknown', 'Avoid blocked and unknown roads'], ['shortest_dry', 'Shortest (ignore flooding)']] as [T.RoutePolicy, string][]).map(([v, l]) => <label key={v}><input type="radio" name="policy" checked={policy === v} onChange={() => setPolicy(v)} />{l}</label>)}
          </fieldset>
          <label className="tg-field"><span>Blocked depth threshold</span><select aria-label="Blocked depth threshold" value={threshold} onChange={(e) => setThreshold(Number(e.target.value))}>{[0.15, 0.3, 0.5].map((t) => <option key={t} value={t}>≥ {t.toFixed(2)} m</option>)}</select></label>
          <button type="button" className="tg-btn tg-btn--primary tg-btn--wide" onClick={find} disabled={!dest || !data.api}><Icon name="search" />Find Routes</button>
          {status && <p className="tg-status" role="status">{status}</p>}
        </Panel>
      </div>
      <div className="tg-col tg-col--map">
        <MapStage data={data} title="Routing map" height="lg" layersInit={{ incidents: false }} route={routes} onPick={setPick}
          onMapClick={(p) => { if (clickSets === 'origin') { setOrigin(p); setClickSets(null); } else if (clickSets === 'destination') { setCustomDest(p); setClickSets(null); } }}
          overlay={<div className="tg-legend tg-legend--right"><strong>Road status (3-state)</strong><ul>{(Object.keys(EDGE_STYLE) as T.EdgeState[]).map((k) => <li key={k}><i style={{ background: EDGE_STYLE[k].color }} />{EDGE_STYLE[k].label}</li>)}<li><i style={{ background: '#3ddc84', height: 4 }} />Selected route</li><li><i style={{ background: '#b36bff', height: 4 }} />Alternative</li></ul></div>} />
      </div>
      <div className="tg-col">
        <Panel title="Candidate Routes" icon="route">
          {result ? <table className="tg-table"><thead><tr><th>Route</th><th>ETA</th><th>Dist.</th><th>Status</th></tr></thead>
            <tbody>{result.routes.map((r, i) => <tr key={r.policy}><th>R{i + 1} · {r.policy.replace(/_/g, ' ')}</th><td>{r.travel_time_s != null ? `${Math.round(r.travel_time_s / 60)} min` : '—'}</td><td>{r.distance_m != null ? `${(r.distance_m / 1000).toFixed(1)} km` : '—'}</td><td><span className={`tg-pill ${r.route_status === 'ASSESSED_PASSABLE' ? 'is-ok' : r.route_status === 'CONDITIONAL' ? 'is-warn' : 'is-bad'}`}>{r.route_status === 'CONDITIONAL' ? 'Conditional · verify' : r.route_status === 'ASSESSED_PASSABLE' ? 'Assessed passable' : 'No route'}</span></td></tr>)}
              {result.dry_baseline && <tr><th>Dry baseline</th><td>{result.dry_baseline.travel_time_s != null ? `${Math.round(result.dry_baseline.travel_time_s / 60)} min` : '—'}</td><td>{result.dry_baseline.distance_m != null ? `${(result.dry_baseline.distance_m / 1000).toFixed(1)} km` : '—'}</td><td><span className="tg-pill">no flooding</span></td></tr>}</tbody></table>
            : <p className="tg-muted">Choose an origin and a shelter, then Find Routes.</p>}
        </Panel>
        <Panel title="Selected Route Details" icon="shield">
          {main ? <ul className="tg-fresh">
            <li><span>Travel time</span><b>{main.travel_time_s != null ? `${Math.round(main.travel_time_s / 60)} min` : '—'}</b></li>
            <li><span>Distance</span><b>{main.distance_m != null ? `${(main.distance_m / 1000).toFixed(2)} km` : '—'}</b></li>
            <li><span>Max depth on route</span><b>{main.max_depth_on_route_m != null ? `${main.max_depth_on_route_m.toFixed(2)} m` : 'Unknown'}</b></li>
            {(Object.keys(EDGE_STYLE) as T.EdgeState[]).map((k) => <li key={k}><span>{EDGE_STYLE[k].label}</span><b>{fmtN((main.length_by_state_m?.[k] ?? 0) / 1000, 2)} km</b></li>)}
          </ul> : <p className="tg-muted">No route selected.</p>}
          <p className="tg-source">Conditional routes use unknown roads and need on-ground verification.</p>
        </Panel>
        <Panel title="Map Inspector" icon="search"><PickCard pick={pick} /></Panel>
      </div>
      <div className="tg-row4">
        <Panel title="Road Segment Status" icon="route" sub={`(${area.label})`}><RoadDonut roads={data.roads} /></Panel>
        <Panel title="Road Length by State" icon="layers"><BarList title="Road km by state" unit="km" rows={(Object.keys(roadKm) as T.EdgeState[]).map((k) => ({ label: EDGE_STYLE[k].label, value: +roadKm[k].toFixed(1), color: EDGE_STYLE[k].color }))} /></Panel>
        <Panel title="Route Comparison" icon="clock">{result ? <BarList title="Travel time" unit="min" rows={[...result.routes.map((r, i) => ({ label: `R${i + 1}`, value: r.travel_time_s != null ? Math.round(r.travel_time_s / 60) : null, color: i === 0 ? '#3ddc84' : '#b36bff' })), ...(result.dry_baseline ? [{ label: 'Dry', value: result.dry_baseline.travel_time_s != null ? Math.round(result.dry_baseline.travel_time_s / 60) : null, color: '#5b6b7a' }] : [])]} /> : <p className="tg-muted">Run a route search to compare.</p>}</Panel>
        <Panel title="Shelters in Area" icon="shelter"><ul className="tg-resources">{shelters.slice(0, 6).map((s) => <li key={s.shelter_id}><Icon name="shelter" /><span>{s.name}<small>{s.category} · cap. {s.capacity_people}</small></span><b className={s.reachable ? 'is-ok' : 'is-bad'}>{s.reachable ? 'Dry' : 'Wet'}</b></li>)}</ul></Panel>
      </div>
    </div>
  );
}

/* ───────── 5 · What-if simulation ───────── */

export function WhatIfTab({ data }: TabProps) {
  const [baseId, setBaseId] = useState(data.runId);
  useEffect(() => { const done = data.runs.filter((r) => r.state === 'completed'); if (done.length && !done.some((r) => r.run_id === baseId)) setBaseId(done.some((r) => r.run_id === data.runId) ? data.runId : done[0].run_id); }, [data.runs, data.runId, baseId]);
  const [rainPct, setRainPct] = useState(130);
  const [release, setRelease] = useState<Record<T.ReservoirKey, number>>({ CHEMBARAMBAKKAM: 0, POONDI: 0, PUZHAL: 0, CHOLAVARAM: 0 });
  const [tide, setTide] = useState(0);
  const [scenarioId, setScenarioId] = useState<string | null>(null);
  const [cmp, setCmp] = useState<T.Comparison | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [show, setShow] = useState<'baseline' | 'scenario'>('scenario');
  const baseAreas = useFrameAreas(data, baseId);
  const scenAreas = useFrameAreas(data, scenarioId);
  const base = data.runs.find((r) => r.run_id === baseId) ?? null;
  const scen = data.runs.find((r) => r.run_id === scenarioId) ?? null;
  useEffect(() => { if (scenarioId) data.setRunId(show === 'scenario' ? scenarioId : baseId); }, [show, scenarioId, baseId]);
  const run = async () => {
    if (!data.api) return;
    setBusy(true);
    setStatus('Submitting what-if…');
    try {
      const rel = Object.fromEntries(Object.entries(release).filter(([, v]) => v > 0)) as Partial<Record<T.ReservoirKey, number>>;
      const acc = await data.api.createSimulation({ mode: 'what_if', what_if: { base_run_id: baseId, rainfall_scale_pct: rainPct, reservoir_release_m3s: rel, tide_offset_m: tide }, duration_hours: 72 });
      const done = acc.state === 'cached' ? await data.api.getSimulation(acc.run_id) : await waitForRun(data.api, acc, (p) => setStatus(`Running: ${p}`));
      await data.refreshRuns();
      setScenarioId(done.run_id);
      setCmp(await data.api.comparison(done.run_id, baseId));
      setShow('scenario');
      setStatus(data.api.kind === 'fixture' ? `Saved-results mode: closest saved rainfall scenario is “${done.label}”. Reservoir release and tide are applied once the engine API is live.` : `Completed: ${done.label ?? done.run_id}`);
    } catch (e) { setStatus(errText(e)); } finally { setBusy(false); }
  };
  const rows: [string, (s?: T.SimulationSummary) => number | null | undefined, string, number][] = [
    ['Inundation extent', (s) => s?.flooded_area_km2, 'km²', 1], ['Max depth', (s) => s?.max_depth_m, 'm', 2], ['Wards affected', (s) => s?.wards_affected, '', 0],
    ['Roads screened', (s) => s?.roads_blocked_km, 'km', 0], ['Buildings affected', (s) => s?.buildings_affected, '', 0], ['Population exposed', (s) => s?.population_exposed, '', 0],
  ];
  return (
    <div className="tg-layout tg-layout--three">
      <div className="tg-col">
        <Panel title="Scenario Builder" icon="branch">
          <RunSelect data={data} label="Baseline run" value={baseId} onChange={setBaseId} completedOnly />
          <label className="tg-field"><span>Rainfall vs baseline <b>{rainPct}%</b></span><input type="range" min={0} max={300} step={5} value={rainPct} aria-label="Rainfall percent of baseline" onChange={(e) => setRainPct(Number(e.target.value))} /></label>
          <div className="tg-field"><span>Reservoir release (m³/s) <small className="tg-assume">assumed · scenario input</small></span>
            {(Object.keys(release) as T.ReservoirKey[]).map((k) => <label key={k} className="tg-inline-field"><small>{k.charAt(0) + k.slice(1).toLowerCase()}</small><input className="tg-num" type="number" min={0} max={3000} step={50} value={release[k]} aria-label={`${k} release m3/s`} onChange={(e) => setRelease({ ...release, [k]: Math.max(0, Math.min(3000, Number(e.target.value))) })} /><small>{(release[k] * 35.3147).toFixed(0)} cusecs</small></label>)}
          </div>
          <label className="tg-field"><span>Tide / sea level offset <b>{tide.toFixed(1)} m</b></span><input type="range" min={-1} max={2} step={0.1} value={tide} aria-label="Tide offset metres" onChange={(e) => setTide(Number(e.target.value))} /></label>
          <button type="button" className="tg-btn tg-btn--primary tg-btn--wide" onClick={run} disabled={busy || !data.api}><Icon name="play" />Run What-if Simulation</button>
          {status && <p className="tg-status" role="status">{status}</p>}
        </Panel>
      </div>
      <div className="tg-col tg-col--map">
        <MapStage data={data} title="What-if comparison map" height="lg" toolbarExtra={scen && <div className="tg-seg" role="group" aria-label="Compare"><button type="button" aria-pressed={show === 'baseline'} onClick={() => setShow('baseline')}>Baseline</button><button type="button" aria-pressed={show === 'scenario'} onClick={() => setShow('scenario')}>Scenario</button></div>} />
        <Timeline data={data} compact />
      </div>
      <div className="tg-col">
        <Panel title="Impact Comparison" icon="gauge">
          <table className="tg-table"><thead><tr><th>Metric</th><th>Baseline</th><th>Scenario</th><th>Δ</th></tr></thead>
            <tbody>{rows.map(([label, get, unit, d]) => { const a = get(base?.summary); const b = get(scen?.summary); const delta = a != null && b != null ? b - a : null; return <tr key={label}><th>{label}</th><td>{fmtN(a, d)} {a != null ? unit : ''}</td><td>{scen ? `${fmtN(b, d)} ${b != null ? unit : ''}` : '—'}</td><td className={delta != null ? (delta > 0 ? 'is-up' : delta < 0 ? 'is-down' : '') : ''}>{delta != null ? `${delta > 0 ? '▲ +' : delta < 0 ? '▼ ' : ''}${fmtN(delta, d)}` : '—'}</td></tr>; })}</tbody></table>
        </Panel>
        <Panel title="Scenario Outcome" icon="alert">
          {cmp ? <>
            <p className="tg-outcome">Rainfall {cmp.modifiers?.rainfall_scale_pct ?? rainPct}% of baseline changes the peak extent by <b>{fmtN(cmp.delta.flooded_area_km2, 1)} km²</b> and max depth by <b>{fmtN(cmp.delta.max_depth_m, 2)} m</b>.</p>
            <h3 className="tg-h3">Largest ward changes</h3>
            <ul className="tg-actions">{(cmp.ward_changes ?? []).slice(0, 5).map((w) => <li key={w.ward_id}><b>Ward {w.ward_id}</b> {w.max_depth_change_m != null ? `${w.max_depth_change_m > 0 ? '+' : ''}${w.max_depth_change_m.toFixed(2)} m` : ''} · {w.risk_level_before} → {w.risk_level_after}</li>)}</ul>
          </> : <p className="tg-muted">Run a what-if to compare against the baseline.</p>}
        </Panel>
      </div>
      <div className="tg-row4">
        <Panel title="Inundation Growth (Area)" icon="waves" className="tg-span-2">
          <LineChart title="Inundation area baseline vs scenario" unit="km²" xLabels={baseAreas.labels} series={[{ name: 'Baseline', values: baseAreas.areas.map((a) => a ?? 0), color: '#7fe3ff' }, ...(scen && scenAreas.areas.length === baseAreas.areas.length ? [{ name: 'Scenario', values: scenAreas.areas.map((a) => a ?? 0), color: '#ff6b8a' }] : [])]} height={170} />
        </Panel>
        <Panel title="Road Accessibility" icon="route" sub="(current map)"><RoadDonut roads={data.roads} /></Panel>
        <Panel title="Ward Risk Shift" icon="building">
          {cmp ? <BarList title="Ward max depth change" unit="m" rows={(cmp.ward_changes ?? []).slice(0, 6).map((w) => ({ label: `Ward ${w.ward_id}`, value: Math.abs(w.max_depth_change_m ?? 0), color: (w.max_depth_change_m ?? 0) > 0 ? '#ff6b8a' : '#3ddc84' }))} /> : <p className="tg-muted">No comparison yet.</p>}
        </Panel>
      </div>
    </div>
  );
}

/* ───────── 6 · Reservoir monitoring ───────── */

const RESERVOIR_POS: Record<string, T.LonLat> = { CHEMBARAMBAKKAM: { lon: 80.053, lat: 13.007 }, REDHILLS: { lon: 80.165, lat: 13.165 }, POONDI: { lon: 79.86, lat: 13.19 }, CHOLAVARAM: { lon: 80.155, lat: 13.23 } };
const RES_NAME: Record<string, string> = { CHEMBARAMBAKKAM: 'Chembarambakkam', REDHILLS: 'Puzhal (Red Hills)', POONDI: 'Poondi', CHOLAVARAM: 'Cholavaram' };

export function ReservoirTab({ data }: TabProps) {
  const [snap, setSnap] = useState<ReservoirSnapshot | null>(reservoirSnapshot);
  const [state, setState] = useState<string | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const fetchSnap = (period: 'daily' | 'monthly' = 'daily') => {
    setState('Fetching the public CFM-DSS dashboard…');
    fetchReservoirHistory(period).then((x) => { reservoirSnapshot = x; setSnap(x); setState(null); }).catch((e) => setState(`Unavailable: ${errText(e)}`));
  };
  const series = snap?.series ?? [];
  const cur = series.find((s) => s.reservoirId === sel) ?? series[0] ?? null;
  const days = Array.from(new Set(TRACKB_REPLAY.map((r) => r[1]))).sort();
  const lookup = new Map(TRACKB_REPLAY.map((r) => [`${r[0]}|${r[1]}`, r]));
  return (
    <div className="tg-layout tg-layout--three">
      <div className="tg-col">
        <Panel title={`Chennai Reservoirs (${series.length || 4})`} icon="dam" actions={<button type="button" className="tg-btn tg-btn--small" onClick={() => fetchSnap('daily')}>{snap ? 'Refresh' : 'Fetch snapshot'}</button>}>
          {state && <p className="tg-status" role="status">{state}</p>}
          {series.length ? <div className="tg-res-cards">{series.map((s) => <button type="button" key={s.reservoirId} className={cur?.reservoirId === s.reservoirId ? 'is-active' : ''} onClick={() => setSel(s.reservoirId)}>
            <span className="tg-res-cards__name"><Icon name="dam" />{s.reservoirName}</span><strong>{s.latest.waterLevelM.toFixed(2)} m</strong><span>Storage {s.latest.averageStorageMcm.toFixed(1)} MCM</span><small>Published {s.latest.sourceDate}</small></button>)}</div>
            : <div className="tg-empty"><p>No snapshot yet. TwinGuard reads the public CFM-DSS dashboard only when you ask (no polling).</p><button type="button" className="tg-btn tg-btn--primary" onClick={() => fetchSnap('daily')}>Fetch published snapshot</button></div>}
          <p className="tg-source">PUBLISHED_SNAPSHOT · freshness unknown · <a href={CFM_DASHBOARD_URL} target="_blank" rel="noreferrer">CFM-DSS dashboard</a></p>
        </Panel>
      </div>
      <div className="tg-col tg-col--map">
        <MapStage data={data} title="Reservoir map" height="lg" layersInit={{ buildings: false, roads: false, incidents: false, shelters: false, water: false, wards: true }} center={{ lon: 80.05, lat: 13.12, range: 52000 }} flyKey="reservoirs"
          overlay={<div className="tg-res-markers">{Object.entries(RESERVOIR_POS).map(([k, p]) => <span key={k}><Icon name="dam" />{RES_NAME[k]}<small>{p.lat.toFixed(3)}, {p.lon.toFixed(3)}</small></span>)}</div>} />
      </div>
      <div className="tg-col">
        <Panel title={cur ? `Reservoir Detail: ${cur.reservoirName}` : 'Reservoir Detail'} icon="gauge">
          {cur ? <>
            <div className="tg-stats tg-stats--2"><Stat label="Water level" value={cur.latest.waterLevelM.toFixed(2)} unit="m" tone="cyan" /><Stat label="Average storage" value={cur.latest.averageStorageMcm.toFixed(1)} unit="MCM" tone="violet" /></div>
            <LineChart title="Published water level" unit="m" xLabels={cur.records.map((r) => r.sourceDate.slice(5))} series={[{ name: 'Level', values: cur.records.map((r) => r.waterLevelM), color: '#2fa8ff' }]} height={150} />
            <LineChart title="Published storage" unit="MCM" xLabels={cur.records.map((r) => r.sourceDate.slice(5))} series={[{ name: 'Storage', values: cur.records.map((r) => r.averageStorageMcm), color: '#9b8cff' }]} height={150} />
          </> : <p className="tg-muted">Fetch a snapshot to see published levels and storage.</p>}
          <p className="tg-source">No inflow, outflow or release is published in this source.</p>
          <p className="tg-source"><b className="tg-assume">ASSUMPTION</b> Live forecast runs derive reservoir outlet inflows from the published storage (A28 method); they are model assumptions, not observed releases.</p>
        </Panel>
      </div>
      <div className="tg-row4">
        <Panel title="Historical Alert Replay (2015)" icon="clock" sub="(Track B rule, REPLAY)" className="tg-span-3">
          <div className="tg-replay" role="table" aria-label="2015 replay alert level by reservoir and date">
            <div className="tg-replay__row tg-replay__head" role="row"><span role="columnheader">Reservoir</span>{days.map((d) => <span role="columnheader" key={d}>{d.slice(8)}<small>{d.slice(5, 7) === '11' ? 'Nov' : 'Dec'}</small></span>)}</div>
            {Object.keys(RES_NAME).map((res) => <div className="tg-replay__row" role="row" key={res}><span role="rowheader">{RES_NAME[res]}</span>{days.map((d) => { const r = lookup.get(`${res}|${d}`); return <span role="cell" key={d} className={`tg-replay__cell is-${r ? r[2].toLowerCase() : 'none'}`} title={r ? `${r[2]} · storage ${r[3]}% · 3-day rain ${r[4]}` : 'no alert emitted'}>{r ? <><b>{r[2][0]}</b><small>{Math.round(r[3])}%</small></> : <small>—</small>}</span>; })}</div>)}
          </div>
          <p className="tg-source">2015 REPLAY alert sequence from historical daily storage (docs/trackb/replay_2015_alerts.jsonl). REPLAY of past data, not a live feed or flood warning.</p>
        </Panel>
        <Panel title="Storage Backtest (2018–2020)" icon="shield">
          <BarList title="Rule CSI" unit="" max={1} rows={TRACKB_BACKTEST.rows.filter((r) => r.entity !== 'Combined').map((r) => ({ label: r.entity, value: Number(r.rule.split(' / ')[2]), color: '#9b8cff' }))} />
          <p className="tg-source">Held-out storage-target CSI (docs/trackb/BACKTEST_REPORT.md).</p>
        </Panel>
      </div>
    </div>
  );
}

/* ───────── 7 · Digital twin (3D city) ───────── */

export function TwinTab({ data }: TabProps) {
  const [gpu, setGpu] = useState<GpuInfo | null>(null);
  useEffect(() => { let off: (() => void) | undefined; import('../twin/Twin3D').then((m) => { off = m.onGpuInfo(setGpu); }); return () => off?.(); }, []);
  const [layers, setLayers] = useState<TwinLayers>({ ...DEFAULT_LAYERS, wards: true });
  const [pick, setPick] = useState<PickInfo | null>(null);
  const stats = focusStats(data.focus, data.depth);
  const area = FOCUS_AREAS.find((a) => a.id === data.focusArea)!;
  const roadKm = roadShares(data.roads);
  const focusCells = useMemo(() => {
    if (!data.depth || !data.focus) return { wet: 0, max: null as number | null };
    const [x0, y0, x1, y1] = data.focus.bbox_utm;
    let wet = 0;
    let max: number | null = null;
    const g = data.depth.grid;
    for (let r = 0; r < data.depth.rows; r += 1) for (let c = 0; c < data.depth.cols; c += 1) {
      const x = g.origin_x_m + (c + 0.5) * g.cell_size_m;
      const y = g.origin_y_m - (r + 0.5) * g.cell_size_m;
      if (x < x0 || x > x1 || y < y0 || y > y1) continue;
      const v = data.depth.values[r][c];
      if (v === null) continue;
      if (v >= 0.1) wet += 1;
      max = max === null ? v : Math.max(max, v);
    }
    return { wet: (wet * g.cell_size_m * g.cell_size_m) / 1e6, max };
  }, [data.depth, data.focus]);
  const pickDepth = pick ? (() => { const [e, n] = lonLatToUtm(pick.location.lon, pick.location.lat); return { e, n }; })() : null;
  return (
    <div className="tg-layout tg-layout--three">
      <div className="tg-col">
        <Panel title="Digital Twin Layers" icon="layers">
          <div className="tg-toggles">{(Object.keys(LAYER_LABELS) as (keyof TwinLayers)[]).map((k) => <label key={k} className={`tg-toggle${k === 'google' && !googleTilesConfigured() ? ' is-disabled' : ''}`}><span>{LAYER_LABELS[k]}{k === 'google' && <small>{googleTilesConfigured() ? (ionConfigured() ? 'via Cesium ion' : 'via Google Map Tiles key') : 'add a Cesium ion token to enable'}</small>}</span><input type="checkbox" role="switch" checked={layers[k] && (k !== 'google' || googleTilesConfigured())} disabled={k === 'google' && !googleTilesConfigured()} onChange={(e) => setLayers({ ...layers, [k]: e.target.checked })} /></label>)}</div>
        </Panel>
        <Panel title="Time & Animation" icon="clock">
          <RunSelect data={data} />
          <Timeline data={data} compact />
          <p className="tg-source">Animation steps through saved frames; nothing is interpolated.</p>
        </Panel>
      </div>
      <div className="tg-col tg-col--map">
        <MapStage data={data} title="3D city digital twin" height="lg" layers={layers} onLayers={setLayers} onPick={setPick} />
      </div>
      <div className="tg-col">
        <Panel title="Selected Area Inspector" icon="search">
          <PickCard pick={pick} />
          {pickDepth && <small className="tg-source">UTM 44N {Math.round(pickDepth.e)} E, {Math.round(pickDepth.n)} N</small>}
        </Panel>
        <Panel title="City Twin Health" icon="shield">
          <ul className="tg-fresh">
            <li><span>Buildings ({area.label})</span><b>{stats.total.toLocaleString('en-IN')}</b><small>OSM footprints · {stats.osmLevels} with levels, rest estimated</small></li>
                        <li><span>3D buildings</span><b>{ionConfigured() ? 'OSM Buildings' : 'OSM extrusion'}</b><small>{ionConfigured() ? `Cesium OSM Buildings coloured by depth${layers.google && googleTilesConfigured() ? '; Google Photorealistic 3D Tiles on up close' : '; Google 3D Tiles off'}` : 'no Cesium ion token configured'}</small></li>
            <li><span>Terrain</span><b>{ionConfigured() ? 'Cesium World' : data.terrain ? 'GLO-30' : 'flat'}</b><small>{ionConfigured() ? 'ion asset 1 (GLO-30 DEM as fallback)' : 'project cleaned DEM'}</small></li>
            <li><span>Flood run</span><b>SIMULATED</b><small>{data.run ? `${runTitle(data.run)} · ${data.run.run_id}` : ''}</small></li>
            <li><span>Rainfall input</span><b>{data.run?.provenance.inputs[0]?.source_mode ?? '—'}</b><small>{data.run?.provenance.inputs[0]?.source ?? ''}</small></li>
            {(data.run?.provenance.inputs ?? []).filter((i) => /inflow|release/i.test(i.name)).map((i) => <li key={i.name}><span>Reservoir inflow</span><b className="tg-assume">ASSUMPTION</b><small>{i.source ?? i.name} · modelled from storage, not an observed release</small></li>)}
            <li><span>Water motion</span><b>{data.flow ? 'MODELLED /flow' : 'ESTIMATED'}</b><small>{data.flow ? `u/v velocity, frame ${data.flow.frame_index}, stride ${data.flow.stride}` : 'no flow output for this run; surface-slope estimate'}</small></li>
            <li><span>Data service</span><b>{data.apiKind === 'api' ? 'C4 v3 API' : 'Saved results'}</b></li>
          </ul>
        </Panel>
        <Panel title="3D Rendering" icon="cube">
          <ul className="tg-fresh"><li><span>GPU</span><b>{gpu ? (gpu.tier === 'high' ? 'High quality' : gpu.tier === 'standard' ? 'Standard' : 'Reduced') : '—'}</b><small>{gpu ? gpu.renderer : 'detecting…'}</small></li><li><span>Water surface</span><b>×{WATER_EXAGGERATION}</b><small>vertical exaggeration of depth</small></li><li><span>Building height</span><b>{3} m/level</b><small>OSM levels or area estimate</small></li><li><span>Imagery</span><b>{imagerySourceLabel()}</b><small>dark-tinted in 3D mode</small></li></ul>
        </Panel>
      </div>
      <div className="tg-row4">
        <Panel title="Simulation Timeline" icon="clock" className="tg-span-2"><Timeline data={data} /></Panel>
        <Panel title="3D Building Impact" icon="building" sub={`(${area.label})`}>
          <Donut title="Buildings by depth class" centre={stats.affected.toLocaleString('en-IN')} sub="≥ 0.15 m" slices={(['gt_1_0', '0_5_to_1_0', '0_15_to_0_5', 'lt_0_15', 'dry', 'unknown'] as T.DepthClass[]).map((k) => ({ label: DEPTH_CLASS_STYLE[k].label, value: stats.counts[k], color: DEPTH_CLASS_STYLE[k].color }))} />
        </Panel>
        <Panel title={`Area Summary (${area.label})`} icon="pin">
          <ul className="tg-fresh">
            <li><span>Inundation area (≥ 0.10 m)</span><b>{focusCells.wet.toFixed(2)} km²</b></li>
            <li><span>Max depth</span><b>{focusCells.max != null ? `${focusCells.max.toFixed(2)} m` : '—'}</b></li>
            <li><span>Buildings ≥ 0.15 m</span><b>{stats.affected.toLocaleString('en-IN')} / {stats.total.toLocaleString('en-IN')}</b></li>
            <li><span>Roads blocked</span><b>{roadKm.ASSESSED_BLOCKED.toFixed(1)} km</b></li>
            <li><span>Roads unknown</span><b>{roadKm.UNKNOWN.toFixed(1)} km</b></li>
          </ul>
          <p className="tg-source">Depth per building is sampled from its {data.depth?.grid.cell_size_m ?? data.run?.grid?.cell_size_m ?? '—'} m model cell.</p>
        </Panel>
      </div>
    </div>
  );
}
