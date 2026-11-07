import { useEffect, useState } from 'react';
import { OpenMeteoWeatherCard } from '../weather/OpenMeteoWeatherCard';
import { loadEventGrids, type Band, type EventGrids } from '../evidence/grids';
import { A05_SUMMARY, A06_CALIBRATION, A07_IMPACT, A10, A21, EVENTS, LEADS, SCENARIOS, TRACKB_BACKTEST, TRACKB_REPLAY, eventLabel, scenarioLabel, type EventId, type Lead, type ScenarioId } from '../evidence/reports';
import { DepthMap, type HoverCell } from './DepthMap';
import { BarList, LineChart } from './Charts';
import { Card, DepthLegend, InfoLine, Kpi, LeadStepper, Segmented, Tag, num, people, pct, utc } from './ui';
import { ImpactsSection, ReservoirsSection, RoutingSection, SystemSection, WhatIfSection } from './sections';
import './product.css';

const sections = [
  { id: 'overview', label: 'Situation Overview', short: 'Overview' },
  { id: 'twin', label: 'Flood Simulation', short: 'Simulation' },
  { id: 'impacts', label: 'Impacts & Shelters', short: 'Impacts' },
  { id: 'response', label: 'Road Routing', short: 'Routing' },
  { id: 'what-if', label: 'What-if Comparison', short: 'What-if' },
  { id: 'reservoirs', label: 'Reservoirs (Track B)', short: 'Reservoirs' },
  { id: 'system', label: 'Data & Evidence', short: 'Evidence' },
] as const;

export type ProductSection = typeof sections[number]['id'];

const headings: Record<ProductSection, { title: string; lead: string }> = {
  overview: { title: 'Situation overview', lead: 'Saved hindcast scenarios for three Chennai flood windows, with impact, routing, shelter and reservoir results from the project reports.' },
  twin: { title: 'Flood simulation', lead: 'Saved A05 depth grids on the 600 m model grid: 3 event windows × 5 rainfall scenarios × 5 lead times × p05/p50/p95.' },
  impacts: { title: 'Impacts & shelters', lead: 'A07 depth-screened exposure, A11 descriptive layers and A10 shelter allocation, each kept separate.' },
  response: { title: 'Road routing', lead: 'A21 three-state routing (assessed passable, assessed blocked, unknown) and the A09 method comparison.' },
  'what-if': { title: 'What-if comparison', lead: 'Compare two saved rainfall scenarios side by side, plus the A13 decision-lab checks. No new model run is started.' },
  reservoirs: { title: 'Reservoirs (Track B)', lead: 'The public CFM-DSS dashboard snapshot on request, the 2015 REPLAY alert sequence and the held-out storage-target backtest.' },
  system: { title: 'Data & evidence', lead: 'Where every number on these pages comes from, which tasks produced it, and what it cannot be used for.' },
};

export interface Selection { event: EventId; scenario: ScenarioId; lead: Lead; band: Band }

function useEventGrids(event: EventId) {
  const [state, setState] = useState<{ event: EventId; grids: EventGrids | null; loading: boolean }>({ event, grids: null, loading: true });
  useEffect(() => {
    let live = true;
    setState((s) => ({ ...s, event, loading: true }));
    loadEventGrids(event).then((grids) => { if (live) setState({ event, grids, loading: false }); });
    return () => { live = false; };
  }, [event]);
  return state.event === event ? state : { event, grids: null, loading: true };
}

export function ProductExperience({ initialSection = 'overview' }: { initialSection?: ProductSection }) {
  const [section, setSection] = useState<ProductSection>(initialSection);
  const [sel, setSel] = useState<Selection>({ event: '2015-12-02', scenario: 'perfect_foresight_imerg', lead: 48, band: 'p50' });
  const [view, setView] = useState<'2d' | '3d'>('2d');
  const { grids, loading } = useEventGrids(sel.event);
  const update = (next: Partial<Selection>) => setSel((s) => ({ ...s, ...next }));
  const heading = headings[section];
  const gate = normalizeGateStatus(import.meta.env.VITE_GATE_G0_STATUS);
  const shared = { sel, update, grids, loading, view, setView, go: setSection };

  return (
    <div className="tg-app">
      <a className="tg-skip" href="#tg-main">Skip to main content</a>
      <header className="tg-top">
        <a className="tg-brand" href="#tg-main" onClick={() => setSection('overview')} aria-label="TwinGuard overview">
          <span className="tg-brand__mark" aria-hidden="true"><svg viewBox="0 0 32 32"><path d="M4 22c3-2 5-2 8 0s5 2 8 0 5-2 8 0" /><path d="M4 27c3-2 5-2 8 0s5 2 8 0 5-2 8 0" /><path d="M9 18V9l5-3 5 3v9M19 18v-6l4-2 4 2v6" /></svg></span>
          <span><strong>TwinGuard AI</strong><small>Chennai flood decision-support research</small></span>
        </a>
        <div className="tg-top__status">
          <span className="tg-chip"><span aria-hidden="true">⌖</span>Chennai CMA (pre-2022 boundary)</span>
          <span className="tg-chip tg-chip--warn" role="note"><i aria-hidden="true" />Research prototype · not an official warning</span>
          <small className="tg-gate" role="status" aria-label={`Gate G0: ${gateText(gate)}`} data-gate-status={gate}>G0 {gateText(gate)}</small>
        </div>
      </header>

      <nav className="tg-nav" aria-label="Product sections">
        {sections.map((item, i) => (
          <button type="button" key={item.id} className={section === item.id ? 'is-active' : ''} aria-label={item.label} aria-current={section === item.id ? 'page' : undefined} onClick={() => setSection(item.id)}>
            <span className="tg-nav__n" aria-hidden="true">{i + 1}</span>
            <span className="tg-nav__full" aria-hidden="true">{item.label}</span>
            <span className="tg-nav__short" aria-hidden="true">{item.short}</span>
          </button>
        ))}
      </nav>

      <div className="tg-context" role="region" aria-label="Selected saved scenario">
        <label className="tg-select"><span>Event window</span>
          <select aria-label="Select event window" value={sel.event} onChange={(e) => update({ event: e.target.value as EventId })}>
            {EVENTS.map((e) => <option key={e.id} value={e.id}>{e.label} · {e.windowUtc}</option>)}
          </select>
        </label>
        <label className="tg-select"><span>Rainfall scenario</span>
          <select aria-label="Select rainfall scenario" value={sel.scenario} onChange={(e) => update({ scenario: e.target.value as ScenarioId })}>
            {SCENARIOS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
        </label>
        <div className="tg-context__lead">
          <span>Lead</span>
          <Segmented label="Select saved lead time" value={sel.lead} options={LEADS.map((l) => ({ value: l, label: `+${l} h` }))} onChange={(lead) => update({ lead })} />
        </div>
        <div className="tg-context__time"><span>Valid time</span><strong>{grids ? utc(grids.validTime(sel.scenario, sel.lead)) : validTimeFallback(sel)}</strong></div>
        <Tag tone="sim">SIMULATED · HINDCAST</Tag>
      </div>

      <main id="tg-main" className="tg-main" tabIndex={-1}>
        <header className="tg-page-head">
          <div><h1>{heading.title}</h1><p>{heading.lead}</p></div>
        </header>
        <p className="tg-banner" role="note"><strong>SAVED RESEARCH SCENARIOS · NOT AN OPERATIONAL SERVICE</strong><span>Results come from saved project runs and reports. They are not live observations, official flood warnings, safe routes or shelter instructions.</span></p>

        {section === 'overview' && <OverviewSection {...shared} />}
        {section === 'twin' && <SimulationSection {...shared} />}
        {section === 'impacts' && <ImpactsSection sel={sel} go={setSection} />}
        {section === 'response' && <RoutingSection />}
        {section === 'what-if' && <WhatIfSection sel={sel} grids={grids} />}
        {section === 'reservoirs' && <ReservoirsSection />}
        {section === 'system' && <SystemSection sel={sel} grids={grids} gate={gate} />}

        <footer className="tg-foot"><span>TwinGuard AI · final-year research prototype</span><span>Saved DERIVED results · 600 m model grid · EPSG:32644</span><span>G0 {gateText(gate)}</span></footer>
      </main>
    </div>
  );
}

function validTimeFallback(sel: Selection) {
  const start = EVENTS.find((e) => e.id === sel.event)!.windowStartUtc;
  return utc(new Date(new Date(start).getTime() + sel.lead * 3600_000).toISOString());
}

interface Shared { sel: Selection; update: (n: Partial<Selection>) => void; grids: EventGrids | null; loading: boolean; view: '2d' | '3d'; setView: (v: '2d' | '3d') => void; go: (s: ProductSection) => void }

function MapPanel({ sel, update, grids, loading, view, setView, title, tall = false }: Shared & { title: string; tall?: boolean }) {
  const [hover, setHover] = useState<HoverCell | null>(null);
  const grid = grids ? grids.get(sel.scenario, sel.lead, sel.band) : null;
  const label = `${view === '3d' ? '3D extrusion' : 'Map'} of saved ${sel.band} simulated depth, ${eventLabel(sel.event)}, ${scenarioLabel(sel.scenario)}, +${sel.lead} h, on the 600 m model grid. Values are simulated, not observed.`;
  return (
    <Card title={title} eyebrow="SAVED A05 DEPTH GRID · 600 m CELLS" className={`tg-mapcard${tall ? ' is-tall' : ''}`}
      actions={<>
        <Segmented label="Depth band" value={sel.band} options={[{ value: 'p05', label: 'p05' }, { value: 'p50', label: 'p50' }, { value: 'p95', label: 'p95' }]} onChange={(band) => update({ band })} />
        <Segmented label="Map display mode" value={view} options={[{ value: '2d', label: '2D map' }, { value: '3d', label: '3D view' }]} onChange={setView} />
      </>}
      source="data/features/forecast/batch2_v1/ · docs/FLOOD_3D_SCENARIO_READINESS.md">
      <div className="tg-mapwrap">
        {loading && !grid ? <div className="tg-map tg-map--loading" role="status">Loading saved grid…</div> : <DepthMap grid={grid} mode={view} label={label} onHover={setHover} />}
        <div className="tg-map__overlay-top">
          <Tag tone="sim">{scenarioLabel(sel.scenario)}</Tag>
          <Tag>+{sel.lead} h · {sel.band}</Tag>
        </div>
        <div className="tg-map__readout" aria-live="polite">
          {view === '3d' ? 'Hover readout is available in the 2D map.' : hover ? (
            <>Cell {hover.col}, {hover.row} · E {hover.easting.toLocaleString('en-IN')} / N {hover.northing.toLocaleString('en-IN')} · <strong>{hover.depthM === null ? 'NoData (unknown, not dry)' : `${hover.depthM.toFixed(3)} m`}</strong></>
          ) : 'Hover the map to read a cell value.'}
        </div>
      </div>
      <DepthLegend compact />
      <LeadStepper lead={sel.lead} onChange={(lead) => update({ lead })} />
    </Card>
  );
}

function StateResults({ sel, grids }: { sel: Selection; grids: EventGrids | null }) {
  const s = grids?.stats(sel.scenario, sel.lead);
  return (
    <Card title="Model state at this lead" eyebrow="COMPUTED FROM THE SAVED p50 GRID" source={grids ? 'saved A05 p50 raster for this event, scenario and lead' : 'docs/PHASE11_FORECAST_BATCH2.md'}>
      {s ? (
        <div className="tg-kpis tg-kpis--2">
          <Kpi label="Cells with p50 ≥ 0.10 m" value={num(s.area_ge_0_10_km2)} unit="km²" tone="water" />
          <Kpi label="Cells with p50 ≥ 0.30 m" value={num(s.area_ge_0_30_km2)} unit="km²" tone="water" />
          <Kpi label="Maximum p50 depth" value={s.max_m.toFixed(2)} unit="m" />
          <Kpi label="Mean p50 depth" value={s.mean_m.toFixed(4)} unit="m" />
          <Kpi label="Assessed cells" value={s.valid_cells.toLocaleString('en-IN')} note="600 m cells" tone="muted" />
          <Kpi label="NoData cells" value={s.nodata_cells.toLocaleString('en-IN')} note="unknown, not dry" tone="muted" />
        </div>
      ) : <p className="tg-muted">Saved grid not bundled. See the scenario summary table for report figures.</p>}
      <p className="tg-fine">Area counts whole 0.36 km² cells and uses the p50 member statistic, so it differs slightly from the report's ensemble-mean areas.</p>
    </Card>
  );
}

function OverviewSection(props: Shared) {
  const { sel, grids, go } = props;
  const [peopleIn, roadKm, facilities] = A07_IMPACT[sel.event][sel.scenario][sel.lead];
  const rep = A05_SUMMARY[sel.event][sel.scenario];
  const ev = EVENTS.find((e) => e.id === sel.event)!;
  const levels = TRACKB_REPLAY.reduce<Record<string, number>>((acc, r) => ({ ...acc, [r[2]]: (acc[r[2]] ?? 0) + 1 }), {});
  const areaSeries = (scenario: ScenarioId) => LEADS.map((l) => (grids ? grids.stats(scenario, l).area_ge_0_10_km2 : 0));
  const f1 = A10.factors[1];
  return (
    <div className="tg-grid tg-grid--overview">
      <div className="tg-col">
        <Card title="Scenario snapshot" eyebrow="A07 IMPACT · 0.30 m SCREEN" source="docs/PHASE13_IMPACT_BATCH2_V4.md">
          <div className="tg-snapshot"><strong>{ev.label}</strong><span>{ev.windowUtc}</span><small>{ev.reference}</small></div>
          <div className="tg-kpis">
            <Kpi label="People in screened cells" value={people(peopleIn)} note="WorldPop model estimate · PARTIAL" tone={peopleIn > 0 ? 'warn' : undefined} />
            <Kpi label="Screened road length" value={num(roadKm)} unit="km" note="midpoint-assessed roads" />
            <Kpi label="Mapped facilities screened" value={num(facilities, 1)} note="ensemble mean, OSM points" />
          </div>
          <InfoLine label="72 h rainfall in this scenario" value={`${num(rep.rain72)} mm`} />
          <InfoLine label="Ensemble-mean area ≥ 0.10 m at 72 h" value={`${num(rep.area72_010)} km²`} />
          <button type="button" className="tg-link" onClick={() => go('impacts')}>Open impacts & shelters <span aria-hidden="true">→</span></button>
        </Card>
        <Card title="2015 reservoir replay" eyebrow="TRACK B · REPLAY, NOT LIVE" source="docs/trackb/replay_2015_alerts.jsonl">
          <div className="tg-levels">
            {(['Critical', 'Warning', 'Watch'] as const).map((l) => <div key={l} className={`tg-level tg-level--${l.toLowerCase()}`}><strong>{levels[l] ?? 0}</strong><span>{l}</span></div>)}
          </div>
          <p className="tg-fine">50 rule alerts for 4 reservoirs, 20 Nov – 4 Dec 2015, replayed from historical daily storage. Storage-target rule, not a flood warning.</p>
          <button type="button" className="tg-link" onClick={() => go('reservoirs')}>Open reservoirs <span aria-hidden="true">→</span></button>
        </Card>
      </div>

      <div className="tg-col tg-col--wide">
        <MapPanel {...props} title="Simulated flood depth" />
      </div>

      <div className="tg-col">
        <OpenMeteoWeatherCard />
        <StateResults sel={sel} grids={grids} />
      </div>

      <div className="tg-row4">
        <Card title="Area ≥ 0.10 m by lead" eyebrow="SAVED p50 GRIDS" source="saved A05 rasters">
          {grids ? <LineChart title="Area at or above 0.10 m by lead time" unit="km²" xLabels={LEADS.map((l) => `+${l}h`)} highlightIndex={LEADS.indexOf(sel.lead)} height={160}
            series={[{ name: 'q10', values: areaSeries('rain_error_q10'), color: '#5ad1a4' }, { name: scenarioLabel(sel.scenario), values: areaSeries(sel.scenario), color: '#4cc3e6' }, { name: 'q90', values: areaSeries('rain_error_q90'), color: '#f2b45a' }]} /> : <p className="tg-muted">Saved grid not bundled.</p>}
        </Card>
        <Card title="Route evidence (A21)" eyebrow="108,000 SIMULATED CASES" source={A21.source}>
          <BarList title="Route outcome share" unit="%" max={100} rows={[
            { label: 'Assessed passable route', value: +(A21.failClosed / A21.primaryCases * 100).toFixed(1), color: '#5ad1a4' },
            { label: 'Conditional · verify', value: +(A21.conditional / A21.primaryCases * 100).toFixed(1), color: '#f2b45a' },
            { label: 'No path', value: +(A21.noPath / A21.primaryCases * 100).toFixed(1), color: '#8d9aa5' },
          ]} />
          <button type="button" className="tg-link" onClick={() => go('response')}>Open road routing <span aria-hidden="true">→</span></button>
        </Card>
        <Card title="Shelter allocation (A10)" eyebrow="CAPACITY FACTOR 1.0 · HYPOTHETICAL" source={A10.source}>
          <div className="tg-kpis tg-kpis--2">
            <Kpi label="Mean served" value={people(f1.served)} note="people (model estimate)" tone="ok" />
            <Kpi label="Assumed capacity" value={people(f1.capacity)} note="795 OSM candidates" />
          </div>
          <p className="tg-fine">{pct(f1.served, A10.demand)} of known modelled demand fits assumed capacity; this is a sensitivity result, not shelter readiness.</p>
        </Card>
        <Card title="Storage backtest" eyebrow="HELD-OUT 2018–2020 · CSI" source={TRACKB_BACKTEST.source}>
          <BarList title="Rule critical success index by reservoir" unit="" max={1} rows={TRACKB_BACKTEST.rows.filter((r) => r.entity !== 'Combined').map((r) => ({ label: r.entity, value: Number(r.rule.split(' / ')[2]), color: '#9b8cff' }))} />
          <p className="tg-fine">Storage-target metric, not flood skill.</p>
        </Card>
      </div>
    </div>
  );
}

function SimulationSection(props: Shared) {
  const { sel, update, grids } = props;
  const rep = A05_SUMMARY[sel.event][sel.scenario];
  const series = SCENARIOS.map((s, i) => ({ name: s.short, values: LEADS.map((l) => (grids ? grids.stats(s.id, l).area_ge_0_10_km2 : 0)), color: ['#4cc3e6', '#5ad1a4', '#9b8cff', '#f2b45a', '#8d9aa5'][i] }));
  return (
    <div className="tg-grid tg-grid--sim">
      <div className="tg-col">
        <Card title="Simulation setup" eyebrow="SAVED RUN · NOT RE-RUN HERE" source="docs/PHASE11_FORECAST_BATCH2.md">
          <fieldset className="tg-radios"><legend>Event window</legend>
            {EVENTS.map((e) => <label key={e.id}><input type="radio" name="sim-event" checked={sel.event === e.id} onChange={() => update({ event: e.id })} /><span><strong>{e.label}</strong><small>{e.windowUtc}</small></span></label>)}
          </fieldset>
          <fieldset className="tg-radios"><legend>Rainfall scenario</legend>
            {SCENARIOS.map((s) => <label key={s.id}><input type="radio" name="sim-scenario" checked={sel.scenario === s.id} onChange={() => update({ scenario: s.id })} /><span><strong>{s.label}</strong><small>{s.note}</small></span></label>)}
          </fieldset>
          <InfoLine label="Model" value="A06 NumPy local-inertial solver" />
          <InfoLine label="Ensemble" value="20 parameter members · seed 20261026" />
          <InfoLine label="Grid" value="69 × 88 cells · 600 m · EPSG:32644" />
          <InfoLine label="Saved runs" value="300 member-runs · 687.71 s on CPU" />
          <InfoLine label="Max mass-balance error" value="0.591%" />
        </Card>
      </div>
      <div className="tg-col tg-col--wide"><MapPanel {...props} title="Simulated flood depth" tall /></div>
      <div className="tg-col">
        <StateResults sel={sel} grids={grids} />
        <Card title="Report summary" eyebrow="ENSEMBLE-MEAN FIGURES" source="docs/PHASE11_FORECAST_BATCH2.md">
          <InfoLine label="Rainfall total" value={`${num(rep.rain72)} mm / 72 h`} />
          <InfoLine label="Mean depth at 24 h" value={`${rep.mean24} m`} />
          <InfoLine label="Area ≥ 0.10 m at 24 h" value={`${num(rep.area24_010)} km²`} />
          <InfoLine label="Mean depth at 72 h" value={`${rep.mean72} m`} />
          <InfoLine label="Area ≥ 0.10 m at 72 h" value={`${num(rep.area72_010)} km²`} />
          <InfoLine label="Area ≥ 0.30 m at 72 h" value={`${num(rep.area72_030)} km²`} />
        </Card>
      </div>
      <div className="tg-row3">
        <Card title="Area ≥ 0.10 m by scenario and lead" eyebrow={`${eventLabel(sel.event).toUpperCase()} · SAVED p50 GRIDS`} source="saved A05 rasters">
          {grids ? <LineChart title="Area at or above 0.10 m by lead, all scenarios" unit="km²" xLabels={LEADS.map((l) => `+${l}h`)} series={series} highlightIndex={LEADS.indexOf(sel.lead)} /> : <p className="tg-muted">Saved grid not bundled.</p>}
        </Card>
        <Card title="72 h rainfall forcing" eyebrow="CMA-MEAN SCENARIO TOTALS" source="docs/PHASE11_FORECAST_BATCH2.md">
          <BarList title="72 hour rainfall by scenario" unit="mm" rows={SCENARIOS.map((s) => ({ label: s.short, value: A05_SUMMARY[sel.event][s.id].rain72, color: s.id === sel.scenario ? '#4cc3e6' : '#3a5a6e' }))} />
        </Card>
        <Card title="Calibration pilot (A06, Nov 2015)" eyebrow="HELD-OUT SPATIAL BLOCKS" source={A06_CALIBRATION.source}>
          <div className="tg-table-wrap"><table className="tg-table">
            <thead><tr><th scope="col">Map date</th><th scope="col">ROC-AUC</th><th scope="col">F1</th><th scope="col">IoU</th></tr></thead>
            <tbody>{A06_CALIBRATION.rows.map((r) => <tr key={r.date}><th scope="row">{r.date}</th><td>{r.roc}</td><td>{r.f1}</td><td>{r.iou}</td></tr>)}</tbody>
          </table></div>
          <p className="tg-fine">Within-event block folds against UNOSAT outlines. Low thresholds and wide area sensitivity show the depths do not reproduce mapped extent robustly.</p>
        </Card>
      </div>
    </div>
  );
}

export type GateStatus = 'ready' | 'not_ready' | 'unknown';
export function normalizeGateStatus(value: unknown): GateStatus { return value === 'ready' || value === 'not_ready' ? value : 'unknown'; }
export function gateText(value: GateStatus): string { return value === 'ready' ? 'READY' : value === 'not_ready' ? 'NOT READY' : 'STATUS UNKNOWN'; }
