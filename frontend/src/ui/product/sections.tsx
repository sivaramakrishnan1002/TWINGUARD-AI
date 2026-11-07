import { useState } from 'react';
import { ReservoirLivePanel } from '../reservoir-live/ReservoirLivePanel';
import type { EventGrids } from '../evidence/grids';
import {
  A05_SUMMARY, A07_CONTEXT, A07_IMPACT, A09_CONTEXT, A09_METHODS, A10, A11, A13, A21, EVENTS, GATES_SNAPSHOT, LEADS, PRODUCT_STATUS, SCENARIOS,
  TRACKB_BACKTEST, TRACKB_REPLAY, TRACKB_RULE, eventLabel, scenarioLabel, type ScenarioId,
} from '../evidence/reports';
import { DepthMap, diffColor } from './DepthMap';
import { BarList, LineChart } from './Charts';
import { Card, DepthLegend, InfoLine, Kpi, Segmented, StateBadge, Tag, num, people, pct, utc } from './ui';
import type { GateStatus, ProductSection, Selection } from './ProductExperience';

const SCEN_COLORS = ['#4cc3e6', '#5ad1a4', '#9b8cff', '#f2b45a', '#8d9aa5'];

/* ───────────────────────── Impacts & shelters ───────────────────────── */

export function ImpactsSection({ sel, go }: { sel: Selection; go: (s: ProductSection) => void }) {
  const row = A07_IMPACT[sel.event][sel.scenario][sel.lead];
  const access = A07_CONTEXT.access72.find((a) => a.event === sel.event)!;
  const seriesFor = (i: 0 | 1 | 2) => SCENARIOS.map((s, si) => ({ name: s.short, color: SCEN_COLORS[si], values: LEADS.map((l) => A07_IMPACT[sel.event][s.id][l][i]) }));
  return (
    <div className="tg-grid tg-grid--sections">
      <div className="tg-span-3 tg-kpis tg-kpis--strip">
        <Kpi label="People in depth-screened cells" value={people(row[0])} note="known WorldPop estimate · PARTIAL" tone={row[0] ? 'warn' : undefined} />
        <Kpi label="Screened road length" value={num(row[1])} unit="km" note="road midpoints ≥ 0.30 m" />
        <Kpi label="Mapped facilities screened" value={num(row[2], 1)} note="ensemble mean of OSM points" />
        <Kpi label="Hazard coverage" value="1.000" note="share of eligible cells assessed" tone="muted" />
      </div>
      <Card title="People in screened cells by lead" eyebrow={`${eventLabel(sel.event).toUpperCase()} · ALL SCENARIOS`} source={A07_CONTEXT.source} className="tg-span-2">
        <LineChart title="Known population in depth-screened cells by lead" unit="people" xLabels={LEADS.map((l) => `+${l}h`)} series={seriesFor(0)} highlightIndex={LEADS.indexOf(sel.lead)} />
        <p className="tg-fine">{A07_CONTEXT.threshold}</p>
      </Card>
      <Card title="Screened road length by lead" eyebrow="KM, ENSEMBLE MEAN" source={A07_CONTEXT.source}>
        <LineChart title="Screened road length by lead" unit="km" xLabels={LEADS.map((l) => `+${l}h`)} series={seriesFor(1)} highlightIndex={LEADS.indexOf(sel.lead)} height={210} />
      </Card>

      <Card title="Facility access cascade at +72 h" eyebrow="PERFECT-FORESIGHT SCENARIO · COARSE GRAPH" source={A07_CONTEXT.source}>
        <div className="tg-table-wrap"><table className="tg-table">
          <thead><tr><th scope="col">Category</th><th scope="col">Reachable / baseline</th><th scope="col">Unreachable</th></tr></thead>
          <tbody>
            {([['Hospitals', access.hospital], ['Shelters', access.shelter], ['Candidate shelters', access.candidate]] as const).map(([label, v]) => <tr key={label}><th scope="row">{label}</th><td>{v[0]} / {v[1]}</td><td>{v[2]}</td></tr>)}
          </tbody>
        </table></div>
        <InfoLine label="Overall access-loss fraction" value={access.loss.toFixed(4)} />
        <p className="tg-fine">Connectivity screen on a 600 m collapsed graph, not routing or facility operation. Shown for {eventLabel(sel.event)}.</p>
      </Card>

      <Card title="Shelter allocation sensitivity" eyebrow="A10 · HYPOTHETICAL CAPACITIES" source={A10.source}>
        <div className="tg-table-wrap"><table className="tg-table">
          <thead><tr><th scope="col">Capacity factor</th><th scope="col">Assumed capacity</th><th scope="col">Mean served</th><th scope="col">Mean unserved</th></tr></thead>
          <tbody>{A10.factors.map((f) => <tr key={f.factor}><th scope="row">× {f.factor}</th><td>{people(f.capacity)}</td><td>{people(f.served)}</td><td>{people(f.unserved)}</td></tr>)}</tbody>
        </table></div>
        <p className="tg-fine">{A10.candidates} Demand in components with no usable candidate: {people(A10.factors[0].unreachable)} on average.</p>
      </Card>

      <Card title="Descriptive layers (A11)" eyebrow="KEPT SEPARATE · NO RANKING" source={A11.source}>
        <ul className="tg-list">{A11.products.map((p) => <li key={p.name}><strong>{p.name}</strong><span>{p.detail}</span></li>)}</ul>
        <p className="tg-callout">{A11.rule}</p>
      </Card>

      <Card title="Coverage and inputs" eyebrow="WHAT THE COUNTS INCLUDE" source={A07_CONTEXT.source} className="tg-span-3">
        <div className="tg-states">
          <StateBadge kind="value" label="Roads" detail={A07_CONTEXT.roadsAssessed} />
          <StateBadge kind="value" label="Facilities" detail={A07_CONTEXT.facilities} />
          <StateBadge kind="nodata" label="Population" detail={A07_CONTEXT.population} />
          <StateBadge kind="unknown" label="Shelter status" detail="No facility is verified as open or operating; candidate shelters are schools and colleges by assumption." />
        </div>
        <button type="button" className="tg-link" onClick={() => go('response')}>Continue to road routing <span aria-hidden="true">→</span></button>
      </Card>
    </div>
  );
}

/* ───────────────────────── Road routing ───────────────────────── */

export function RoutingSection() {
  const share = (v: number) => +(v / A21.primaryCases * 100).toFixed(2);
  return (
    <div className="tg-grid tg-grid--sections">
      <Card title="Three-state road evidence" eyebrow="A21 EDGE STATES" source={A21.source}>
        <div className="tg-states">
          <StateBadge kind="value" label="Assessed passable" detail="Simulated depth below the assumed 0.30 m road screen (0.15 m for tunnel proxies)." />
          <StateBadge kind="unavailable" label="Assessed blocked" detail="Simulated depth at or above the screen in that member and snapshot." />
          <StateBadge kind="unknown" label="Unknown · verify" detail="Edge not mapped to a depth cell, or a bridge without deck elevation. Never treated as passable." />
        </div>
        <p className="tg-fine">Routes containing any unknown edge are CONDITIONAL / NEEDS VERIFICATION, never passable or safe.</p>
      </Card>
      <Card title="Route outcomes across 108,000 cases" eyebrow="120 OD PAIRS × 3 EVENTS × SCENARIOS × HORIZONS × 20 MEMBERS" source={A21.source} className="tg-span-2">
        <BarList title="Primary route outcomes" unit="%" max={100} rows={[
          { label: 'Fail-closed assessed route', value: share(A21.failClosed), color: '#5ad1a4' },
          { label: 'Three-state: conditional, verify', value: share(A21.conditional), color: '#f2b45a' },
          { label: 'Three-state: any route incl. conditional', value: share(A21.anyRoute), color: '#4cc3e6' },
          { label: 'No three-state path', value: share(A21.noPath), color: '#8d9aa5' },
        ]} />
        <div className="tg-kpis tg-kpis--3">
          {A21.intervals.map((i) => <Kpi key={i.label} label={i.label} value={i.range} note="95% cluster bootstrap (3 events)" tone="muted" />)}
        </div>
        <p className="tg-fine">Only three event clusters exist, so intervals are unstable and are not real-world probabilities. Held-out member 20 had no simulated blocked outcome among 13,438 fully assessed routes.</p>
      </Card>

      <Card title="Verification queue" eyebrow="UNKNOWN EDGES TO CHECK FIRST" source={A21.source}>
        <LineChart title="Conditional cases resolved by verifying the top unknown edges" unit="cases" xLabels={A21.verificationQueue.map((q) => `${q.edges}`)} series={[{ name: 'Cases covered', values: A21.verificationQueue.map((q) => q.covered), color: '#f2b45a' }]} height={170} />
        <p className="tg-fine">Edges verified (x) vs conditional cases they touch (of 92,750). {A21.queueNote}</p>
      </Card>

      <Card title="Decision stability" eyebrow="SAVED ROUTE CHOICES, NOT PROBABILITIES" source={A21.source} className="tg-span-2">
        <div className="tg-table-wrap"><table className="tg-table">
          <thead><tr><th scope="col">Comparison</th><th scope="col">Method</th><th scope="col">Paired</th><th scope="col">Identical</th><th scope="col">Changed</th></tr></thead>
          <tbody>{A21.stability.map((r) => <tr key={r.comparison + r.method}><th scope="row">{r.comparison}</th><td>{r.method}</td><td>{r.paired.toLocaleString('en-IN')}</td><td>{pct(r.identical, r.paired)}</td><td>{r.changed.toLocaleString('en-IN')} ({pct(r.changed, r.paired)})</td></tr>)}</tbody>
        </table></div>
        <p className="tg-fine">Scenario-associated changes are correlates of the saved scenario label, not causal effects.</p>
      </Card>

      <Card title="Routing method comparison (A09)" eyebrow="54 ROUTE RECORDS PER METHOD · OSSE" source={A09_CONTEXT.source} className="tg-span-3">
        <div className="tg-table-wrap"><table className="tg-table">
          <thead><tr><th scope="col">Method</th><th scope="col">Records with path</th><th scope="col">Probabilities computable</th><th scope="col">Mean route-failure fraction</th><th scope="col">Simulated-truth failures</th><th scope="col">Mean travel time</th><th scope="col">Depth-distance exposure</th></tr></thead>
          <tbody>{A09_METHODS.map((m) => <tr key={m.method}><th scope="row">{m.method}</th><td>{m.withPath}</td><td>{m.computable}</td><td>{m.failure === null ? 'Not assessed' : m.failure.toFixed(4)}</td><td>{m.truth}</td><td>{m.time === null ? 'Not assessed' : `${num(m.time)} s`}</td><td>{m.exposure === null ? 'Not assessed' : `${num(m.exposure)} m²`}</td></tr>)}</tbody>
        </table></div>
        <p className="tg-fine">{A09_CONTEXT.graph} {A09_CONTEXT.design} Route geometries live in the git-ignored A09 output and are not drawn here. {A21.novelty}</p>
      </Card>
    </div>
  );
}

/* ───────────────────────── What-if comparison ───────────────────────── */

export function WhatIfSection({ sel, grids }: { sel: Selection; grids: EventGrids | null }) {
  const [a, setA] = useState<ScenarioId>('perfect_foresight_imerg');
  const [b, setB] = useState<ScenarioId>('rain_error_q90');
  const [mode, setMode] = useState<'side' | 'diff'>('side');
  const ga = grids?.get(a, sel.lead, 'p50') ?? null;
  const gb = grids?.get(b, sel.lead, 'p50') ?? null;
  const ia = A07_IMPACT[sel.event][a][sel.lead];
  const ib = A07_IMPACT[sel.event][b][sel.lead];
  const sa = grids?.stats(a, sel.lead);
  const sb = grids?.stats(b, sel.lead);
  const rows: [string, number | undefined, number | undefined, string][] = [
    ['72 h rainfall', A05_SUMMARY[sel.event][a].rain72, A05_SUMMARY[sel.event][b].rain72, 'mm'],
    ['Area p50 ≥ 0.10 m', sa?.area_ge_0_10_km2, sb?.area_ge_0_10_km2, 'km²'],
    ['Area p50 ≥ 0.30 m', sa?.area_ge_0_30_km2, sb?.area_ge_0_30_km2, 'km²'],
    ['People in screened cells', ia[0], ib[0], 'people'],
    ['Screened road length', ia[1], ib[1], 'km'],
    ['Facilities screened', ia[2], ib[2], ''],
  ];
  const select = (label: string, value: ScenarioId, onChange: (v: ScenarioId) => void) => (
    <label className="tg-select"><span>{label}</span><select aria-label={label} value={value} onChange={(e) => onChange(e.target.value as ScenarioId)}>{SCENARIOS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}</select></label>
  );
  return (
    <div className="tg-grid tg-grid--sections">
      <Card title="Compare saved scenarios" eyebrow={`${eventLabel(sel.event).toUpperCase()} · +${sel.lead} h · p50`} source="saved A05 rasters · docs/PHASE13_IMPACT_BATCH2_V4.md" className="tg-span-3"
        actions={<Segmented label="Comparison view" value={mode} options={[{ value: 'side', label: 'Side by side' }, { value: 'diff', label: 'Difference B − A' }]} onChange={setMode} />}>
        <div className="tg-compare-controls">{select('Scenario A', a, setA)}{select('Scenario B', b, setB)}</div>
        {mode === 'side' ? (
          <div className="tg-compare">
            <figure><figcaption><Tag tone="sim">A</Tag> {scenarioLabel(a)}</figcaption><div className="tg-compare__map"><DepthMap grid={ga} mode="2d" label={`Saved p50 depth, ${scenarioLabel(a)}`} /></div></figure>
            <figure><figcaption><Tag tone="info">B</Tag> {scenarioLabel(b)}</figcaption><div className="tg-compare__map"><DepthMap grid={gb} mode="2d" label={`Saved p50 depth, ${scenarioLabel(b)}`} /></div></figure>
            <DepthLegend />
          </div>
        ) : (
          <div className="tg-compare tg-compare--diff">
            <figure><figcaption>Depth difference, B − A</figcaption><div className="tg-compare__map is-wide"><DepthMap grid={gb} compareTo={ga} mode="2d" label={`Depth difference ${scenarioLabel(b)} minus ${scenarioLabel(a)}`} /></div></figure>
            <div className="tg-depth-legend"><strong>Difference (m)</strong><ul>
              {[['≥ +0.10', 0.2], ['+0.03 – +0.10', 0.05], ['0 – +0.03', 0.01], ['≈ 0', 0], ['−0.03 – 0', -0.01], ['−0.10 – −0.03', -0.05], ['≤ −0.10', -0.2]].map(([l, v]) => <li key={l as string}><i style={{ background: diffColor(v as number) }} />{l}</li>)}
              <li><i className="tg-swatch-nodata" />NoData in either: unknown</li>
            </ul></div>
          </div>
        )}
        <div className="tg-table-wrap"><table className="tg-table">
          <thead><tr><th scope="col">Measure</th><th scope="col">A · {SCENARIOS.find((s) => s.id === a)!.short}</th><th scope="col">B · {SCENARIOS.find((s) => s.id === b)!.short}</th><th scope="col">Change B − A</th></tr></thead>
          <tbody>{rows.map(([label, va, vb, unit]) => <tr key={label}><th scope="row">{label}</th><td>{va === undefined ? 'Grid not bundled' : `${num(va)} ${unit}`}</td><td>{vb === undefined ? 'Grid not bundled' : `${num(vb)} ${unit}`}</td><td>{va === undefined || vb === undefined ? '—' : <Delta a={va} b={vb} unit={unit} />}</td></tr>)}</tbody>
        </table></div>
        <p className="tg-fine">Both columns are saved simulations from the same 20-member ensemble; differences are scenario contrasts, not predictions or validated counterfactual outcomes.</p>
      </Card>

      <Card title="H2 · uncertainty vs deterministic depth" eyebrow="A13 · SYNTHETIC HELD-OUT MEMBER" source={A13.source} className="tg-span-2">
        <div className="tg-table-wrap"><table className="tg-table">
          <thead><tr><th scope="col">Event</th><th scope="col">Member 12 MAE</th><th scope="col">Ensemble median MAE</th><th scope="col">p05–p95 coverage</th><th scope="col">Mean width</th></tr></thead>
          <tbody>{A13.h2.map((r) => <tr key={r.event}><th scope="row">{eventLabel(r.event)}</th><td>{r.m12.toFixed(6)} m</td><td>{r.median.toFixed(6)} m</td><td>{r.coverage}%</td><td>{r.width.toFixed(6)} m</td></tr>)}</tbody>
        </table></div>
        <p className="tg-fine">{A13.h2Summary}</p>
      </Card>
      <Card title="H5 · counterfactual checks" eyebrow="WHAT THE SAVED ARTIFACTS SUPPORT" source={A13.source}>
        <ul className="tg-list">{A13.h5.map((h) => <li key={h.check}><strong>{h.check} <Tag tone={h.status === 'Unavailable' ? 'bad' : 'warn'}>{h.status}</Tag></strong><span>{h.detail}</span></li>)}</ul>
      </Card>
      <Card title="H3 · uncertainty-aware vs current-state routes" eyebrow="54 PAIRED CASES · WINS / TIES / LOSSES / MISSING" source={A13.source} className="tg-span-3">
        <div className="tg-table-wrap"><table className="tg-table">
          <thead><tr><th scope="col">Outcome</th><th scope="col">W / T / L / missing</th><th scope="col">Paired mean difference</th><th scope="col">95% event-cluster interval</th></tr></thead>
          <tbody>{A13.h3.map((r) => <tr key={r.outcome}><th scope="row">{r.outcome}</th><td>{r.record}</td><td>{r.diff}</td><td>{r.interval}</td></tr>)}</tbody>
        </table></div>
        <p className="tg-fine">H4: {A13.h4} H2–H5 are not confirmed by these experiments.</p>
      </Card>
    </div>
  );
}

function Delta({ a, b, unit }: { a: number; b: number; unit: string }) {
  const d = b - a;
  if (Math.abs(d) < 1e-9) return <span className="tg-delta">No change</span>;
  const rel = a ? ` (${d > 0 ? '+' : ''}${((d / a) * 100).toFixed(1)}%)` : '';
  return <span className={`tg-delta ${d > 0 ? 'is-up' : 'is-down'}`}><span aria-hidden="true">{d > 0 ? '▲' : '▼'}</span> {d > 0 ? '+' : '−'}{num(Math.abs(d))} {unit}{rel}</span>;
}

/* ───────────────────────── Reservoirs ───────────────────────── */

const RESERVOIRS = ['CHEMBARAMBAKKAM', 'REDHILLS', 'POONDI', 'CHOLAVARAM'] as const;
const RES_NAME: Record<string, string> = { CHEMBARAMBAKKAM: 'Chembarambakkam', REDHILLS: 'Red Hills (Puzhal)', POONDI: 'Poondi', CHOLAVARAM: 'Cholavaram' };

export function ReservoirsSection() {
  const days = Array.from(new Set(TRACKB_REPLAY.map((r) => r[1]))).sort();
  const lookup = new Map(TRACKB_REPLAY.map((r) => [`${r[0]}|${r[1]}`, r]));
  return (
    <div className="tg-grid tg-grid--sections">
      <div className="tg-span-3"><ReservoirLivePanel /></div>

      <Card title="2015 REPLAY alert sequence" eyebrow="TRACK B RULE · HISTORICAL DAILY STORAGE" source="docs/trackb/replay_2015_alerts.jsonl" className="tg-span-3">
        <div className="tg-replay" role="table" aria-label="Replay alert level by reservoir and date, 20 November to 4 December 2015">
          <div className="tg-replay__row tg-replay__head" role="row">
            <span role="columnheader">Reservoir</span>
            {days.map((d) => <span role="columnheader" key={d}>{d.slice(8)}<small>{d.slice(5, 7) === '11' ? 'Nov' : 'Dec'}</small></span>)}
          </div>
          {RESERVOIRS.map((res) => (
            <div className="tg-replay__row" role="row" key={res}>
              <span role="rowheader">{RES_NAME[res]}</span>
              {days.map((d) => {
                const r = lookup.get(`${res}|${d}`);
                return r ? (
                  <span role="cell" key={d} className={`tg-replay__cell is-${r[2].toLowerCase()}`} title={`${RES_NAME[res]} ${d}: ${r[2]}, storage ${r[3]}%, 3-day rain ${r[4]}`}>
                    <b>{r[2][0]}{r[2] === 'Watch' ? 'a' : ''}</b><small>{Math.round(r[3])}%</small>
                  </span>
                ) : <span role="cell" key={d} className="tg-replay__cell is-none" title={`${RES_NAME[res]} ${d}: no alert emitted`}><small>—</small></span>;
              })}
            </div>
          ))}
        </div>
        <div className="tg-legend-row">
          <span><i className="tg-replay__key is-critical" />C · Critical</span><span><i className="tg-replay__key is-warning" />W · Warning</span><span><i className="tg-replay__key is-watch" />Wa · Watch</span><span><i className="tg-replay__key is-none" />— no alert emitted</span>
        </div>
        <p className="tg-fine">{TRACKB_RULE} Rainfall units are INFERRED; the date-only source timezone is unconfirmed. This is REPLAY of past data, not a live feed or flood warning.</p>
      </Card>

      <Card title="Held-out storage-target backtest" eyebrow={TRACKB_BACKTEST.split.toUpperCase()} source={TRACKB_BACKTEST.source} className="tg-span-2">
        <div className="tg-table-wrap"><table className="tg-table">
          <thead><tr><th scope="col">Reservoir</th><th scope="col">Test prevalence</th><th scope="col">Rule POD / FAR / CSI</th><th scope="col">Persistence CSI</th><th scope="col">Logistic CSI</th><th scope="col">Gradient boosting CSI</th><th scope="col">GB Brier</th></tr></thead>
          <tbody>{TRACKB_BACKTEST.rows.map((r) => <tr key={r.entity}><th scope="row">{r.entity}</th><td>{r.prevalence.toFixed(3)}</td><td>{r.rule}</td><td>{r.persistence}</td><td>{r.logistic}</td><td>{r.gb}</td><td>{r.brier}</td></tr>)}</tbody>
        </table></div>
        <p className="tg-fine">{TRACKB_BACKTEST.target}</p>
      </Card>
      <Card title="2015 case study and limits" eyebrow="LEGACY SCREEN" source={TRACKB_BACKTEST.source}>
        <p className="tg-body">{TRACKB_BACKTEST.caseStudy}</p>
        <p className="tg-callout">{TRACKB_BACKTEST.limits}</p>
      </Card>
    </div>
  );
}

/* ───────────────────────── Data & evidence ───────────────────────── */

const STATUS_TONE: Record<string, 'ok' | 'warn' | 'bad' | 'info'> = { done_with_caveats: 'ok', done: 'ok', running: 'info', blocked_prerequisite: 'bad' };

export function SystemSection({ sel, grids, gate }: { sel: Selection; grids: EventGrids | null; gate: GateStatus }) {
  const g = grids?.get(sel.scenario, sel.lead, 'p50');
  return (
    <div className="tg-grid tg-grid--sections">
      <Card title="Where each section's numbers come from" eyebrow="TASK RECORDS · docs/master/STATE.json" source="docs/master/STATE.json" className="tg-span-2">
        <div className="tg-table-wrap"><table className="tg-table">
          <thead><tr><th scope="col">Task</th><th scope="col">Product</th><th scope="col">Status</th><th scope="col">Report</th></tr></thead>
          <tbody>{PRODUCT_STATUS.map((p) => <tr key={p.id}><th scope="row">{p.id}</th><td>{p.name}</td><td><Tag tone={STATUS_TONE[p.status] ?? 'neutral'}>{p.status.replace(/_/g, ' ')}</Tag></td><td><code>{p.report}</code></td></tr>)}</tbody>
        </table></div>
      </Card>
      <Card title="Sources and connections" eyebrow="WHAT IS LIVE AND WHAT IS SAVED" source="docs/master/STATE.json · CR-014 · CR-018">
        <div className="tg-states">
          <StateBadge kind="value" label="Saved research outputs · SIMULATED" detail="A05–A21 results, bundled from committed reports and saved rasters. No refresh; not observations." />
          <StateBadge kind="value" label="Open-Meteo weather model · LIVE fetch" detail="One external weather-model request on the Overview. Model estimates, not gauge observations." />
          <StateBadge kind="value" label="CFM-DSS reservoir snapshot · on request" detail="Public dashboard read through the local AI service when you press fetch. Freshness unknown." />
          <StateBadge kind="unavailable" label="IMD rainfall connector · Unavailable" detail="B40 is blocked pending authorization." />
          <StateBadge kind="unavailable" label="Flood-model recomputation · Unavailable" detail="B42 (observation-triggered recompute) is blocked; nothing on these pages re-runs a model." />
        </div>
      </Card>

      <Card title="Gates" eyebrow="BUILD-TIME SNAPSHOT" source="docs/master/GATES.md">
        <InfoLine label="G0 (packaged snapshot)" value={<Tag tone={gate === 'ready' ? 'ok' : gate === 'not_ready' ? 'bad' : 'neutral'}>G0 {gate === 'ready' ? 'READY' : gate === 'not_ready' ? 'NOT READY' : 'STATUS UNKNOWN'}</Tag>} />
        <p className="tg-fine">{GATES_SNAPSHOT} A ready gate does not make any result operational.</p>
      </Card>
      <Card title="Selected grid provenance" eyebrow="CURRENT MAP LAYER" source="data/features/visualization3d/batch2_v1/manifest.json">
        <InfoLine label="Event / scenario" value={`${eventLabel(sel.event)} · ${scenarioLabel(sel.scenario)}`} />
        <InfoLine label="Lead / valid time" value={g ? `+${sel.lead} h · ${utc(g.validTimeUtc)}` : `+${sel.lead} h`} />
        <InfoLine label="Grid" value={g ? `${g.width} × ${g.height} · ${g.cellSizeM} m · ${g.crs}` : 'Not bundled'} />
        <InfoLine label="p50 raster SHA-256" value={g ? <code title={g.sha256}>{g.sha256.slice(0, 16)}…</code> : 'Not bundled'} />
        <InfoLine label="Depth unit" value="m (per reports; TIFF band unit tag unset)" />
      </Card>
      <Card title="Coverage states" eyebrow="NEVER COLLAPSED TO ZERO OR DRY" source="docs/FLOOD_3D_SCENARIO_READINESS.md">
        <div className="tg-states">
          <StateBadge kind="value" label="Known value" detail="A saved simulated or report value with its source." />
          <StateBadge kind="zero" label="Known zero (0)" detail="A valid zero inside assessed coverage, e.g. 0 km screened road." />
          <StateBadge kind="nodata" label="NoData" detail="Outside the assessed CMA grid or an open-water sink. Unknown, not dry." />
          <StateBadge kind="unknown" label="Unknown" detail="Unassessed road edge or bridge; routes using it need verification." />
          <StateBadge kind="unavailable" label="Unavailable" detail="No authorized source or saved result exists for this item." />
        </div>
      </Card>

      <Card title="Interpretation limits" eyebrow="APPLY TO EVERY SECTION" source="docs/VALIDATION_REPORT.md" className="tg-span-3">
        <ul className="tg-list tg-list--cols">
          <li><strong>Simulation</strong><span>600 m local-inertial pilot on a surface DEM; no storm drains, external inflow or street-scale flow. Member spread is not calibrated confidence.</span></li>
          <li><strong>Rainfall</strong><span>Perfect-foresight IMERG is hindsight forcing. No archived forecasts exist, so no operational forecast skill can be computed.</span></li>
          <li><strong>Validation</strong><span>No independent date-matched depth or extent references exist for these windows; 2021/2023 references are PDF or preliminary.</span></li>
          <li><strong>Routing & shelters</strong><span>Depth thresholds, speeds and capacities are assumptions. No route is safe and no shelter is verified as operating.</span></li>
          <li><strong>Population</strong><span>WorldPop is a model estimate; NoData cells are excluded, never counted as zero.</span></li>
          <li><strong>Reservoirs</strong><span>Storage is not release. Capacity histories are unverified; Track B metrics are storage-target scores.</span></li>
        </ul>
        <p className="tg-fine">Event windows: {EVENTS.map((e) => `${e.label} (${e.windowUtc})`).join(' · ')}.</p>
      </Card>
    </div>
  );
}
