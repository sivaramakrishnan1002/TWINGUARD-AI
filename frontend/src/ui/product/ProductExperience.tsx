import { lazy, Suspense, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { FOCUS_AREAS, loadGazetteer, type GazPlace, type GazWard } from '../api/fixtures';
import { haversineM } from '../api/geo';
import { buildIndex, type SearchHit } from './search';
import type { FocusArea, LonLat, RouteOption } from '../api/v3types';
import type { CameraInfo, PickInfo, TwinCommand, TwinLayers, ViewMode } from '../twin/Twin3D';
import { frameArea, useTwinData, type TwinData } from './state';
import { badgeFor, focusAreaLabel, isFocusRun, istTime, LIVE_DISCLAIMER, runKindOf } from './runs';
import { EmergencyTab, OverviewTab, ReservoirTab, RoutingTab, SimulationTab, TwinTab, WhatIfTab } from './tabs';
import './product.css';

const Twin3D = lazy(() => import('../twin/Twin3D').then((m) => ({ default: m.Twin3D })));

const sections = [
  { id: 'overview', label: 'Situation Overview', icon: 'home' },
  { id: 'simulation', label: 'Flood Simulation', icon: 'waves' },
  { id: 'emergency', label: 'Emergency Support', icon: 'siren' },
  { id: 'routing', label: 'Road Routing', icon: 'route' },
  { id: 'what-if', label: 'What-if Simulation', icon: 'branch' },
  { id: 'reservoirs', label: 'Reservoir Monitoring', icon: 'dam' },
  { id: 'twin', label: 'Digital Twin (3D City)', icon: 'cube' },
] as const;
export type ProductSection = typeof sections[number]['id'];

export type GateStatus = 'ready' | 'not_ready' | 'unknown';
export function normalizeGateStatus(value: unknown): GateStatus { return value === 'ready' || value === 'not_ready' ? value : 'unknown'; }
export function gateText(value: GateStatus): string { return value === 'ready' ? 'READY' : value === 'not_ready' ? 'NOT READY' : 'STATUS UNKNOWN'; }

export function ProductExperience({ initialSection = 'overview' }: { initialSection?: ProductSection }) {
  const [section, setSectionState] = useState<ProductSection>(() => {
    if (typeof window === 'undefined') return initialSection;
    const t = new URLSearchParams(window.location.search).get('tab');
    return sections.some((s) => s.id === t) ? (t as ProductSection) : initialSection;
  });
  const setSection = (s: ProductSection) => {
    setSectionState(s);
    try { const u = new URL(window.location.href); u.searchParams.set('tab', s); window.history.replaceState(null, '', u); } catch { /* non-browser */ }
  };
  const data = useTwinData();
  const gate = normalizeGateStatus(import.meta.env.VITE_GATE_G0_STATUS);
  const tabProps = { data, go: setSection };
  return (
    <div className="tg-app">
      <a className="tg-skip" href="#tg-main">Skip to main content</a>
      <Header data={data} />
      <nav className="tg-nav" aria-label="Product sections">
        {sections.map((s, i) => (
          <button type="button" key={s.id} className={section === s.id ? 'is-active' : ''} aria-label={s.label} aria-current={section === s.id ? 'page' : undefined} onClick={() => setSection(s.id)}>
            <Icon name={s.icon} /><span aria-hidden="true">{i + 1}. {s.label}</span>
          </button>
        ))}
      </nav>
      <main id="tg-main" className="tg-main" tabIndex={-1}>
        <h1 className="tg-visually-hidden">{sections.find((s) => s.id === section)!.label}</h1>
        <div className="tg-livebar">
          <p className="tg-disclaimer" role="note"><Icon name="alert" /> {LIVE_DISCLAIMER}. Results are SIMULATED by the flood model; follow official advisories.</p>
          <LiveStrip data={data} />
        </div>
        {data.live?.last_error && <p className="tg-toast tg-toast--warn" role="alert">
          Last live cycle failed at {istTime(data.live.last_error.at)} IST ({data.live.last_error.stage.replace('_', ' ')}): {data.live.last_error.message}
          {data.live.last_good_run_id ? ` Showing the last good live run ${data.live.last_good_run_id}.` : ' No earlier live run is available.'}
        </p>}
        {data.error && data.apiKind !== 'connecting' && <p className="tg-toast" role="status">{data.error}</p>}
        {section === 'overview' && <OverviewTab {...tabProps} />}
        {section === 'simulation' && <SimulationTab {...tabProps} />}
        {section === 'emergency' && <EmergencyTab {...tabProps} />}
        {section === 'routing' && <RoutingTab {...tabProps} />}
        {section === 'what-if' && <WhatIfTab {...tabProps} />}
        {section === 'reservoirs' && <ReservoirTab {...tabProps} />}
        {section === 'twin' && <TwinTab {...tabProps} />}
      </main>
      <footer className="tg-foot">
        <span>TwinGuard AI · Chennai Digital Twin · final-year project</span>
        <span>Simulated results, OSM © OpenStreetMap contributors (ODbL) · Weather: Open-Meteo (CC BY 4.0) · Map data: see on-map credits</span>
        <small className="tg-gate" role="status" aria-label={`Gate G0: ${gateText(gate)}`} data-gate-status={gate}>G0 {gateText(gate)}</small>
      </footer>
    </div>
  );
}

/** Badge of the run on screen (run_kind): LIVE FORECAST with its run time, REPLAY, WHAT-IF, else DEMO / SIMULATION. */
export function RunBadge({ data, compact = false }: { data: TwinData; compact?: boolean }) {
  const kind = runKindOf(data.run);
  const text = badgeFor(kind);
  const issued = kind === 'LIVE_FORECAST' ? (data.live?.latest?.run_id === data.runId ? data.live.latest.issued_at : data.run?.created_at) : null;
  return (
    <span className={`tg-badge tg-badge--${text === 'LIVE FORECAST' ? 'live' : text === 'REPLAY' ? 'replay' : text === 'WHAT-IF' ? 'whatif' : 'demo'}`} role="note" data-run-kind={kind ?? 'none'}
      title={kind === 'LIVE_FORECAST' ? `${LIVE_DISCLAIMER}. Live forecast run ${data.runId}` : kind === 'REPLAY' ? 'Replay of an archived event (REPLAY rainfall); results SIMULATED' : kind === 'WHAT_IF' ? 'What-if scenario; results SIMULATED' : 'Simulation; results SIMULATED'}>
      {text}{!compact && issued ? ` · ${istTime(issued)} IST` : ''}
    </span>
  );
}

const HEALTH_LABEL: Record<string, string> = { ok: 'OK', stale: 'Stale', error: 'Error', disabled: 'Off', unknown: 'Unknown' };
function SourceDot({ name, h }: { name: string; h: { state: string; refresh_policy: string; last_success_at?: string | null; data_time?: string | null; last_error?: string | null } }) {
  const tip = `${name}: ${HEALTH_LABEL[h.state] ?? h.state} · ${h.refresh_policy}${h.last_success_at ? ` · last success ${istTime(h.last_success_at)} IST` : ''}${h.data_time ? ` · data ${h.data_time}` : ''}${h.last_error ? ` · ${h.last_error}` : ''}`;
  return <span className={`tg-health tg-health--${h.state}`} title={tip} aria-label={tip}><i aria-hidden="true" />{name}</span>;
}

/** Live strip: "Updated HH:MM IST · next HH:MM", source health, Refresh, follow-live. Hidden without the live API. */
function LiveStrip({ data }: { data: TwinData }) {
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const live = data.live;
  // the "cycle started" note is done once a new live run lands
  useEffect(() => { setMsg(null); }, [data.liveRunId]);
  if (!live || data.apiKind !== 'api') return null;
  const latest = live.latest;
  const refresh = async () => { setBusy(true); setMsg(await data.refreshLive()); setBusy(false); };
  const onLive = !!data.liveRunId && data.runId === data.liveRunId;
  return (
    <div className="tg-live" role="group" aria-label="Live forecast status">
      <span className="tg-live__state" data-live-state={live.state}>
        {live.state === 'disabled' || !live.enabled ? 'Live forecast off' : live.state === 'running' ? 'Live cycle running…' : latest ? `Updated ${istTime(latest.completed_at ?? latest.issued_at)} IST` : 'No live run yet'}
        {live.enabled && live.next_scheduled_at && <> · next {istTime(live.next_scheduled_at)}</>}
      </span>
      <SourceDot name="Open-Meteo" h={live.sources.open_meteo} />
      <SourceDot name="CFM-DSS" h={live.sources.cfm_dss} />
      {live.enabled && <button type="button" className="tg-btn tg-btn--small" onClick={refresh} disabled={busy || live.state === 'running'}>{busy ? 'Requesting…' : 'Refresh'}</button>}
      {data.pinned && data.liveRunId && !onLive && <button type="button" className="tg-link" onClick={data.followLive}>Back to live forecast</button>}
      {msg && <span className="tg-live__msg" role="status">{msg}</span>}
    </div>
  );
}

function Header({ data }: { data: TwinData }) {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => { setNow(new Date()); const t = window.setInterval(() => setNow(new Date()), 30_000); return () => window.clearInterval(t); }, []);
  const w = data.weather?.current;
  return (
    <header className="tg-top">
      <a className="tg-brand" href="#tg-main" aria-label="TwinGuard AI home">
        <span className="tg-brand__mark" aria-hidden="true"><svg viewBox="0 0 48 40"><path d="M6 30V14l5-3v19M14 30V8l6-4v26M23 30V12l5-2v20M31 30V16l5-2v16M39 30V20l4-1v11" /><path d="M2 32c5-3 9-3 14 0s9 3 14 0 9-3 14 0" /><path d="M2 37c5-3 9-3 14 0s9 3 14 0 9-3 14 0" /></svg></span>
        <span className="tg-brand__text"><strong>TwinGuard AI</strong><small>Chennai Digital Twin</small></span>
      </a>
      <p className="tg-top__tagline">Intelligent Digital Twin for<br />Flood Simulation, Early Warning &amp; Emergency Decision Support</p>
      <div className="tg-top__status">
        <span className="tg-chip"><i className="tg-dot" aria-hidden="true" />Chennai, Tamil Nadu</span>
        <RunBadge data={data} />
        <span className="tg-chip tg-chip--mono" title={data.apiKind === 'api' ? 'Connected to the C4 v3 API' : 'C4 v3 API not reachable yet; showing typed fixtures from saved project results'}>
          DATA: {data.apiKind === 'api' ? 'C4 v3 API' : data.apiKind === 'fixture' ? 'SAVED RESULTS' : 'CONNECTING'}
          {data.apiKind === 'fixture' && <button type="button" className="tg-chip__btn" onClick={data.reload} aria-label="Retry C4 v3 API connection">↻</button>}
        </span>
        {now && <span className="tg-chip tg-chip--mono">{now.toLocaleDateString('en-IN', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata' })} · {now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Kolkata' })} IST</span>}
        <span className="tg-chip tg-chip--weather" title={data.weather ? `Open-Meteo model estimate, fetched ${data.weather.fetched_at}` : data.weatherError ?? 'Weather loading'}>
          <Icon name="cloud" />
          {w ? <>{w.temperature_c ?? '—'}°C <span className="tg-chip__sep">RH {w.relative_humidity_pct ?? '—'}%</span><span className="tg-chip__sep">Wind {w.wind_speed_kmh != null ? `${Math.round(w.wind_speed_kmh)} km/h` : '—'}</span><small>model</small></> : <small>weather n/a</small>}
        </span>
      </div>
    </header>
  );
}

/* ───────── shared map stage ───────── */

/** Google 3D tiles are opt-in: most of Chennai has no photogrammetry mesh, so OSM buildings over Google 2D imagery is the default. */
export const DEFAULT_LAYERS: TwinLayers = { water: true, hqWater: true, buildings: true, roads: true, wards: false, shelters: true, incidents: true, google: false, photoreal: false };
export const LAYER_LABELS: Record<keyof TwinLayers, string> = { water: 'Flood depth (water)', hqWater: 'High-quality animated water', buildings: '3D buildings', roads: 'Road network (3-state)', wards: 'Ward boundaries', shelters: 'Relief shelters', incidents: 'Generated incidents', google: 'Google Photorealistic 3D Tiles', photoreal: 'Photoreal roofs (experimental)' };

const MAP_INCIDENT_LIMIT = 60;

export function MapStage({ data, title, layersInit, layers: controlled, onLayers, center, route, onPick, onMapClick, height = 'md', overlay, toolbarExtra, flyKey }: {
  data: TwinData;
  layers?: TwinLayers;
  onLayers?: (l: TwinLayers) => void;
  center?: { lon: number; lat: number; range?: number } | null;
  title?: string;
  layersInit?: Partial<TwinLayers>;
  route?: RouteOption[] | null;
  onPick?: (p: PickInfo | null) => void;
  onMapClick?: (p: LonLat) => void;
  height?: 'sm' | 'md' | 'lg';
  overlay?: ReactNode;
  toolbarExtra?: ReactNode;
  flyKey?: string;
}) {
  const [mode, setMode] = useState<ViewMode>('3d');
  const [own, setOwn] = useState<TwinLayers>({ ...DEFAULT_LAYERS, ...layersInit });
  const layers = controlled ?? own;
  const setLayers = (l: TwinLayers) => (onLayers ? onLayers(l) : setOwn(l));
  // The map shows the most severe generated incidents only (peak frames can hold hundreds); the Emergency tab lists all of them.
  const mapIncidents = useMemo(() => {
    const rank = { critical: 3, warning: 2, watch: 1, info: 0 } as const;
    return [...data.incidents].sort((a, b) => rank[b.severity] - rank[a.severity]).slice(0, MAP_INCIDENT_LIMIT);
  }, [data.incidents]);
  const [menu, setMenu] = useState(false);
  const [cmd, setCmd] = useState<TwinCommand | null>(null);
  const [cam, setCam] = useState<CameraInfo | null>(null);
  const send = (type: TwinCommand['type']) => setCmd({ type, key: Date.now() });
  const [highlight, setHighlight] = useState<number | null>(null);
  const goTo = (hit: SearchHit) => {
    setHighlight(hit.ward_id);
    setFly({ lon: hit.lon, lat: hit.lat, range: hit.kind === 'ward' ? 5200 : 2600, key: `s-${hit.label}-${Date.now()}` });
    const nearArea = FOCUS_AREAS.map((a) => ({ a, d: haversineM([a.centre.lon, a.centre.lat], [hit.lon, hit.lat]) })).sort((x, y) => x.d - y.d)[0];
    if (nearArea.d < 5000 && nearArea.a.id !== data.focusArea) { firstArea.current = true; data.setFocusArea(nearArea.a.id); }
  };
  const area = FOCUS_AREAS.find((a) => a.id === data.focusArea)!;
  const HOME = { lon: 80.2, lat: 13.02, range: 46000 };
  const [fly, setFly] = useState<{ lon: number; lat: number; range?: number; key: string }>(() => (center ? { ...center, key: 'init' } : { ...HOME, key: 'home' }));
  const onCam = (c: CameraInfo) => {
    setCam(c);
    // three-state road colours for what is on screen once zoomed in; the default run/focus box otherwise
    // oblique views reach the horizon, so use ~9 km around the screen centre (clipped to the view), not the whole view rectangle
    if (c.heightM < 14000 && c.center) {
      const r = 0.04;
      let b: [number, number, number, number] = [c.center.lon - r, c.center.lat - r, c.center.lon + r, c.center.lat + r];
      if (c.viewBbox) b = [Math.max(b[0], c.viewBbox[0]), Math.max(b[1], c.viewBbox[1]), Math.min(b[2], c.viewBbox[2]), Math.min(b[3], c.viewBbox[3])];
      data.setRoadView(b[0] < b[2] && b[1] < b[3] ? b : null);
    } else data.setRoadView(null);
  };
  const focusRun = isFocusRun(data.run) ? data.run : null;
  const focusBox = useMemo(() => (focusRun?.grid?.bbox_wgs84 ? { bbox: focusRun.grid.bbox_wgs84 as [number, number, number, number], label: `${focusAreaLabel(focusRun) ?? 'Focus'} · ${focusRun.grid.cell_size_m} m focus area — detailed simulation inside` } : null), [focusRun?.run_id, focusRun?.grid]);
  useEffect(() => {
    if (!focusBox) return;
    const [w, s, e, n] = focusBox.bbox;
    setFly({ lon: (w + e) / 2, lat: (s + n) / 2 - 0.035, range: 11000, key: `box-${focusRun?.run_id}` });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusBox?.bbox.join(',')]);
  const firstArea = useRef(true);
  useEffect(() => {
    if (firstArea.current) { firstArea.current = false; return; }
    setFly({ lon: area.centre.lon, lat: area.centre.lat, range: 2800, key: `${area.id}-${Date.now()}` });
  }, [area.id]);
  useEffect(() => { if (center) setFly({ lon: center.lon, lat: center.lat, range: center.range, key: `c-${flyKey ?? ''}-${center.lon},${center.lat}` }); }, [flyKey, center?.lon, center?.lat]);
  return (
    <section className={`tg-stage tg-stage--${height}`} aria-label={title ?? '3D city map'}>
      <div className="tg-stage__toolbar">
        <div className="tg-seg" role="group" aria-label="Map view mode">
          {(['3d', '2d', 'satellite'] as ViewMode[]).map((m) => <button type="button" key={m} aria-pressed={mode === m} onClick={() => setMode(m)}>{m === '3d' ? '3D Digital Twin' : m === '2d' ? '2D Map' : 'Satellite'}</button>)}
        </div>
        <div className="tg-menu">
          <button type="button" className="tg-btn tg-btn--ghost" aria-expanded={menu} onClick={() => setMenu(!menu)}><Icon name="layers" />Layers ▾</button>
          {menu && <div className="tg-menu__panel" role="group" aria-label="Map layers">
            {(Object.keys(LAYER_LABELS) as (keyof TwinLayers)[]).map((k) => <label key={k} className="tg-check"><input type="checkbox" checked={layers[k]} onChange={(e) => setLayers({ ...layers, [k]: e.target.checked })} />{LAYER_LABELS[k]}</label>)}
          </div>}
        </div>
        <AreaSearch onPick={goTo} />
        <AreasMenu data={data} onPick={goTo} />
        {toolbarExtra}
      </div>
      <div className="tg-stage__map">
        <Suspense fallback={<div className="tg-twin tg-twin--loading" role="status">Loading 3D city…</div>}>
          <Twin3D mode={mode} layers={layers} terrain={data.terrain} frame={layers.water || layers.buildings ? data.depth : null} flow={layers.water ? data.flow : null} contextFrame={layers.water ? data.contextDepth : null} focusBox={focusBox} focus={data.focus} roads={data.roads} wards={layers.wards ? data.wardShapes : null} wardShapes={data.wardShapes} highlightWard={highlight}
            shelters={data.shelters?.shelters ?? null} incidents={mapIncidents} route={route} flyTo={fly} command={cmd} onCamera={onCam} onPick={onPick} onMapClick={onMapClick} />
        </Suspense>
        <span className="tg-stage__badge" data-run-kind={runKindOf(data.run) ?? 'none'}>{badgeFor(runKindOf(data.run))}</span>
        <div className="tg-tools" role="toolbar" aria-label="Map tools">
          <button type="button" aria-label="Whole city view" title="Whole study area" onClick={() => setFly({ ...HOME, key: `home-${Date.now()}` })}><Icon name="home" /></button>
          <button type="button" aria-label="Fly to focus area" title="Locate focus area" onClick={() => setFly({ lon: area.centre.lon, lat: area.centre.lat, range: 2800, key: `${area.id}-${Date.now()}` })}><Icon name="pin" /></button>
          <button type="button" aria-label="Layers" title="Layers" aria-expanded={menu} onClick={() => setMenu(!menu)}><Icon name="layers" /></button>
          <button type="button" aria-label="Zoom in" title="Zoom in" onClick={() => send('zoomIn')}>＋</button>
          <button type="button" aria-label="Zoom out" title="Zoom out" onClick={() => send('zoomOut')}>－</button>
          <button type="button" aria-label="Toggle tilt" title="Tilt / top view" onClick={() => send('tilt')}>3D</button>
        </div>
        <button type="button" className="tg-compass" aria-label="Reset to north" title="Reset to north" onClick={() => send('north')} style={{ transform: `rotate(${-(cam?.headingDeg ?? 0)}deg)` }}><span>N</span></button>
        {cam?.metersPer100px != null && <ScaleBar metersPer100px={cam.metersPer100px} />}
        <MapLegend flow={data.flow && layers.water ? { speedMax: data.flow.speed_max_mps ?? null } : null} context={focusRun ? data.contextRun?.label ?? null : undefined} />
        <NoFloodHint data={data} />
        {overlay}
      </div>
    </section>
  );
}

/** T+0 / dry frames: tell the viewer why the map is dry and when this run floods (from the run itself, never assumed). */
function NoFloodHint({ data }: { data: TwinData }) {
  const run = data.run;
  const area = frameArea(data.depth, 0.1);
  if (!run || !data.depth || area == null || area >= 0.05 || data.playing) return null;
  const f0 = run.frames[0];
  const hoursFrom = (iso?: string | null) => (iso && f0 ? Math.round((Date.parse(iso) - Date.parse(f0.valid_time_utc)) / 36e5) : null);
  const rain = run.request?.custom_rainfall;
  const firstWet = rain ? rain.values_mm.findIndex((v) => v > 0) : -1;
  const rainStart = rain && firstWet >= 0 ? hoursFrom(new Date(Date.parse(rain.start_time_utc) + firstWet * rain.interval_minutes * 60000).toISOString()) : null;
  const peak = hoursFrom(run.summary?.peak_time_utc);
  const now = run.frames.find((f) => f.index === data.frameIndex);
  const when = now ? `T+${Math.round((now.elapsed_minutes ?? 0) / 60)} h` : 'this frame';
  const detail = rainStart != null ? ` Rain starts at T+${Math.max(0, rainStart)} h.` : peak != null && peak > 0 ? ` Flooding peaks at T+${peak} h in this run.` : '';
  return (
    <div className="tg-hint" role="status">
      <strong>No flooding at {when}.</strong> Press play ▶ to watch the water rise.{detail}
    </div>
  );
}

let gazCache: { places: GazPlace[]; wards: GazWard[] } | null = null;
function useGazetteer() {
  const [g, setG] = useState(gazCache);
  useEffect(() => { if (!gazCache) loadGazetteer().then((x) => { gazCache = x ?? { places: [], wards: [] }; setG(gazCache); }); }, []);
  return g;
}
const CURATED = [
  { name: 'Velachery', lon: 80.2209, lat: 12.9815 }, { name: 'Adyar', lon: 80.2565, lat: 13.0012 }, { name: 'T. Nagar', lon: 80.2341, lat: 13.0418 },
  { name: 'Porur', lon: 80.1565, lat: 13.0382 }, { name: 'Guindy', lon: 80.2206, lat: 13.0067 }, { name: 'Anna Nagar', lon: 80.2101, lat: 13.085 },
  { name: 'Tiruvottiyur', lon: 80.3014, lat: 13.1643 }, { name: 'Marina Beach', lon: 80.2824, lat: 13.05 },
];

function AreaSearch({ onPick }: { onPick: (h: SearchHit) => void }) {
  const gaz = useGazetteer();
  const search = useMemo(() => buildIndex(gaz?.places ?? [], gaz?.wards ?? [], CURATED), [gaz]);
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const hits = useMemo(() => search(q), [search, q]);
  const pick = (h: SearchHit) => { onPick(h); setQ(h.label); setOpen(false); };
  return (
    <div className="tg-search">
      <Icon name="search" />
      <input type="search" role="combobox" aria-label="Search area, locality or ward" placeholder="Search area or ward (e.g. Royapuram, Ward 178)" value={q}
        aria-expanded={open && hits.length > 0} aria-autocomplete="list" aria-controls="tg-search-list" aria-activedescendant={open && hits[active] ? `tg-hit-${active}` : undefined}
        onChange={(e) => { setQ(e.target.value); setOpen(true); setActive(0); }} onFocus={() => setOpen(true)} onBlur={() => window.setTimeout(() => setOpen(false), 150)}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(hits.length - 1, a + 1)); }
          else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(0, a - 1)); }
          else if (e.key === 'Enter' && hits[active]) { e.preventDefault(); pick(hits[active]); }
          else if (e.key === 'Escape') setOpen(false);
        }} />
      {open && q && <ul id="tg-search-list" role="listbox" className="tg-search__list">
        {hits.map((h, i) => <li key={`${h.label}-${h.lon}-${i}`} id={`tg-hit-${i}`} role="option" aria-selected={i === active} className={i === active ? 'is-active' : ''} onMouseDown={(e) => { e.preventDefault(); pick(h); }}>
          <Icon name={h.kind === 'ward' ? 'layers' : 'pin'} size={15} /><span><b>{h.label}</b><small>{h.sub}</small></span></li>)}
        {!hits.length && <li className="tg-search__none" role="option" aria-selected={false}>{gaz ? 'No matching area in the CMA' : 'Loading places…'}</li>}
      </ul>}
    </div>
  );
}

function AreasMenu({ data, onPick }: { data: TwinData; onPick: (h: SearchHit) => void }) {
  const gaz = useGazetteer();
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState('');
  const byWard = new Map(data.wards.map((w) => [w.ward_id, w]));
  const placesByWard = useMemo(() => {
    const m = new Map<number, string[]>();
    for (const p of gaz?.places ?? []) if (p.ward_id && p.rank <= 3) m.set(p.ward_id, [...(m.get(p.ward_id) ?? []), p.name]);
    return m;
  }, [gaz]);
  const zones = useMemo(() => {
    const m = new Map<string, GazWard[]>();
    for (const w of gaz?.wards ?? []) m.set(w.zone ?? 'Other', [...(m.get(w.zone ?? 'Other') ?? []), w]);
    return [...m.entries()];
  }, [gaz]);
  const f = filter.trim().toLowerCase();
  return (
    <div className="tg-menu">
      <button type="button" className="tg-btn tg-btn--ghost" aria-expanded={open} onClick={() => setOpen(!open)}><Icon name="pin" />Areas ▾</button>
      {open && <div className="tg-menu__panel tg-areas" role="dialog" aria-label="Areas by zone and ward">
        <label className="tg-field"><span>Detailed area (roads, shelters)</span>
          <select aria-label="Focus area" value={data.focusArea} onChange={(e) => data.setFocusArea(e.target.value as FocusArea)}>{FOCUS_AREAS.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}</select>
        </label>
        <input className="tg-areas__filter" type="search" aria-label="Filter wards" placeholder="Filter wards or localities" value={filter} onChange={(e) => setFilter(e.target.value)} />
        <div className="tg-areas__list">
          {zones.map(([zone, wards]) => {
            const rows = wards.filter((w) => !f || w.name.toLowerCase().includes(f) || String(w.ward_id) === f || (placesByWard.get(w.ward_id) ?? []).some((n) => n.toLowerCase().includes(f)));
            if (!rows.length) return null;
            return <details key={zone} open={!!f}>
              <summary>{zone}<small>{rows.length} wards</small></summary>
              {rows.map((w) => {
                const s = byWard.get(w.ward_id);
                const tone = s?.risk_level === 'severe' ? 'is-bad' : s?.risk_level === 'high' ? 'is-warn' : s?.risk_level === 'moderate' ? 'is-info' : 'is-ok';
                return <button type="button" key={w.ward_id} onClick={() => { onPick({ kind: 'ward', label: w.name, sub: zone, lon: w.lon, lat: w.lat, ward_id: w.ward_id, rank: 2, score: 0, bbox: w.bbox }); setOpen(false); }}>
                  <span><b>{w.name}</b><small>{(placesByWard.get(w.ward_id) ?? []).slice(0, 3).join(', ') || '—'}</small></span>
                  <span className={`tg-pill ${tone}`}>{s?.max_depth_m != null ? `${s.max_depth_m.toFixed(2)} m` : 'n/a'}</span>
                </button>;
              })}
            </details>;
          })}
        </div>
      </div>}
    </div>
  );
}

function ScaleBar({ metersPer100px }: { metersPer100px: number }) {
  const nice = [50, 100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000, 20000, 50000];
  const target = metersPer100px * 1.4;
  const m = nice.reduce((a, b) => (Math.abs(b - target) < Math.abs(a - target) ? b : a), nice[0]);
  const px = Math.round((m / metersPer100px) * 100);
  return <div className="tg-scale" aria-label={`Scale ${m >= 1000 ? `${m / 1000} km` : `${m} m`}`}><span>0</span><i style={{ width: px }} /><span>{m >= 1000 ? `${m / 1000} km` : `${m} m`}</span></div>;
}

function MapLegend({ flow, context }: { flow: { speedMax: number | null } | null; /** focus runs: label of the citywide context run (null = none found) */ context?: string | null }) {
  return (
    <div className="tg-legend" aria-label="Map legend">
      <strong>Flood Depth (m)</strong>
      <div className="tg-legend__ramp" aria-hidden="true" />
      <div className="tg-legend__ticks"><span>0.05</span><span>0.3</span><span>0.8</span><span>1.5+</span></div>
      <ul><li><i className="is-dry" />No flood (transparent)</li></ul>
      <p className="tg-legend__note" data-flow-source={flow ? 'modelled' : 'estimated'}>
        {context !== undefined && <>{context ? `Faded water outside the focus box: citywide context run (${context})` : 'No matching citywide run for context outside the focus box'}<br /></>}
        {flow ? `Water motion: modelled velocity${flow.speedMax != null && flow.speedMax >= 0.05 ? ` (max ${flow.speedMax.toFixed(1)} m/s)` : ''}` : 'Water motion: estimated from surface slope'}
      </p>
      <strong>Network</strong>
      <ul>
        <li><i className="is-line" style={{ background: '#36b9ff' }} />River / canal</li>
        <li><i className="is-line" style={{ background: '#3ddc84' }} />Road passable</li>
        <li><i className="is-line" style={{ background: '#ff3b5c' }} />Road blocked</li>
        <li><i className="is-line" style={{ background: '#f5c542' }} />Road unknown</li>
        <li><i className="is-line" style={{ background: '#8696a8' }} />Not assessed in this run</li>
      </ul>
      <strong>Buildings</strong>
      <ul>
        <li><i style={{ background: '#ff3b5c' }} />&gt; 1.0 m</li>
        <li><i style={{ background: '#ff9f43' }} />0.5 – 1.0 m</li>
        <li><i style={{ background: '#2f7cff' }} />0.15 – 0.5 m</li>
        <li><i style={{ background: '#5b6b7a' }} />Dry</li>
      </ul>
    </div>
  );
}

/** Evenly sampled frame indices (always including first and last) for long A25 runs (e.g. 49 frames). */
export function sampleFrames(n: number, max: number): number[] {
  if (n <= max) return Array.from({ length: n }, (_, i) => i);
  const out = new Set<number>();
  for (let k = 0; k < max; k += 1) out.add(Math.round((k * (n - 1)) / (max - 1)));
  return [...out].sort((a, b) => a - b);
}
const hoursLabel = (f?: { elapsed_minutes?: number }) => `T+${Math.round(((f?.elapsed_minutes ?? 0) / 60) * 10) / 10}h`.replace('.0h', 'h');

export function Timeline({ data, compact = false }: { data: TwinData; compact?: boolean }) {
  const frames = data.run?.frames ?? [];
  const cur = frames[data.frameIndex];
  const ticks = sampleFrames(frames.length, compact ? 6 : 9);
  const long = frames.length > ticks.length;
  return (
    <div className={`tg-timeline${compact ? ' is-compact' : ''}`}>
      <button type="button" className="tg-play" aria-pressed={data.playing} aria-label={data.playing ? 'Pause timeline' : 'Play timeline'} onClick={() => data.setPlaying(!data.playing)}>{data.playing ? '❚❚' : '▶'}</button>
      <div className="tg-timeline__body">
        <div className="tg-timeline__track" role="radiogroup" aria-label="Simulation frame">
          {ticks.map((i) => {
            const f = frames[i];
            return (
              <button type="button" role="radio" key={f.index} aria-checked={i === data.frameIndex} className={i < data.frameIndex ? 'is-past' : i === data.frameIndex ? 'is-current' : ''} onClick={() => { data.setPlaying(false); data.setFrameIndex(i); }}>
                <i aria-hidden="true" /><span>{hoursLabel(f)}</span>
              </button>
            );
          })}
          {!frames.length && <span className="tg-muted">Loading frames…</span>}
        </div>
        {long && <input className="tg-timeline__range" type="range" min={0} max={frames.length - 1} step={1} value={data.frameIndex} aria-label={`Simulation frame ${data.frameIndex + 1} of ${frames.length}`} onChange={(e) => { data.setPlaying(false); data.setFrameIndex(Number(e.target.value)); }} />}
      </div>
      {!compact && <div className="tg-timeline__now"><small>{long ? `Frame ${data.frameIndex + 1}/${frames.length} · ${hoursLabel(cur)}` : 'Current frame'}</small><strong>{cur ? `${cur.valid_time_utc.slice(0, 16).replace('T', ' ')} UTC` : '—'}</strong></div>}
    </div>
  );
}

const ICONS: Record<string, string> = {
  home: 'M3 11 12 3l9 8v10h-6v-6H9v6H3z',
  waves: 'M2 8c3-2 5-2 8 0s5 2 8 0 3-1 4-1M2 13c3-2 5-2 8 0s5 2 8 0 3-1 4-1M2 18c3-2 5-2 8 0s5 2 8 0 3-1 4-1',
  siren: 'M6 18v-6a6 6 0 0 1 12 0v6M4 21h16M12 2v2M3.5 6.5l1.5 1.5M20.5 6.5 19 8',
  route: 'M5 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM19 9a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM7 17l10-10',
  branch: 'M6 4a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM6 16a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM18 10a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM6 8v8M8 6c6 0 8 2 8 4M8 18c6 0 8-2 8-4',
  dam: 'M3 20h18M4 20V8h16v12M7 8v12M11 8v12M15 8v12M19 8v12M2 8h20M4 5h16',
  cube: 'M12 2 21 7v10l-9 5-9-5V7zM3 7l9 5 9-5M12 12v10',
  cloud: 'M7 18a4 4 0 0 1 0-8 6 6 0 0 1 11.3 1.5A3.5 3.5 0 0 1 18 18z',
  layers: 'M12 3 2 8l10 5 10-5zM2 13l10 5 10-5M2 18l10 5 10-5',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM21 21l-5-5',
  alert: 'M12 3 2 21h20zM12 10v5M12 18v.5',
  pin: 'M12 22s7-7 7-12a7 7 0 0 0-14 0c0 5 7 12 7 12zM12 12a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
  people: 'M8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM16 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM2 20c0-3 3-5 6-5s6 2 6 5M14 15c3 0 8 1 8 5',
  boat: 'M3 16l2 4h14l2-4zM12 4v12M12 5l6 8h-6',
  shelter: 'M3 11 12 4l9 7M5 10v10h14V10M10 20v-6h4v6',
  clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7v5l3 3',
  gauge: 'M4 18a8 8 0 1 1 16 0M12 18l4-6',
  shield: 'M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z',
  building: 'M4 21V7l8-4v18M12 21V9l8 3v9M7 10v.5M7 14v.5M15 14v.5M15 17v.5',
  play: 'M7 5v14l12-7z',
};
export function Icon({ name, size = 18 }: { name: string; size?: number }) {
  return <svg className="tg-icon" viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" focusable="false"><path d={ICONS[name] ?? ICONS.alert} /></svg>;
}
