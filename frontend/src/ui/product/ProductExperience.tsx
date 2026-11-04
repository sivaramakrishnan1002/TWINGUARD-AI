import { useEffect, useId, useMemo, useState } from 'react';
import type { DemoFrame, DemoReservoir, DemoScenario, DemoStateKind, DemoWorkspace, ProductExperienceAdapter, WhatIfInputs } from '../demo/types';
import { advanceDemoFrame, demoAdapter, defaultWhatIfInputs, setDemoShelterAvailability } from '../demo/adapter';
import { DEMO_STATE_EXAMPLES } from '../demo/fixtures';
import { SourceReadinessPanel } from '../live-readiness/SourceReadinessPanel';
import { demoScenarioMetadata, unavailableLiveMetadata } from '../live-readiness/model';
import floodCityConcept from './assets/flood-city-concept-v1.webp';
import './product.css';

const sections = [
  { id: 'overview', label: 'Situation Overview', short: 'Overview', number: '01' },
  { id: 'twin', label: '3D Flood Twin', short: 'Flood twin', number: '02' },
  { id: 'reservoirs', label: 'Reservoirs & Alerts', short: 'Reservoirs', number: '03' },
  { id: 'impacts', label: 'Impacts', short: 'Impacts', number: '04' },
  { id: 'response', label: 'Emergency Response', short: 'Response', number: '05' },
  { id: 'what-if', label: 'What-if Lab', short: 'What-if', number: '06' },
  { id: 'system', label: 'Data & System', short: 'Data & System', number: '07' },
] as const;

export type ProductSection = typeof sections[number]['id'];

const sectionTitles: Record<ProductSection, { eyebrow: string; title: string; description: string }> = {
  overview: { eyebrow: 'COMMAND VIEW · DEMO', title: 'Situation overview', description: 'Explore the TwinGuard workflow with synthetic, clearly labeled demonstration data.' },
  twin: { eyebrow: 'SPATIAL WORKSPACE · SIMULATED', title: '3D Flood Twin', description: 'Illustrative water animation over demo geometry. No hydraulic or geographic result is being shown.' },
  reservoirs: { eyebrow: 'WATER SYSTEM · DEMO', title: 'Reservoirs & alerts', description: 'Synthetic reservoir values demonstrate the interface. No observed reservoir feed is connected.' },
  impacts: { eyebrow: 'EXPOSURE · SIMULATED', title: 'Impacts', description: 'Separate demo views for hazard footprint, exposure, facilities, and road access.' },
  response: { eyebrow: 'PLANNING WORKSPACE · DEMO', title: 'Emergency response', description: 'Compare fictional route candidates and shelter records. Nothing here is operational advice.' },
  'what-if': { eyebrow: 'SCENARIO EXPLORATION · DEMO', title: 'What-if lab', description: 'Change synthetic assumptions and compare local demo arithmetic with its baseline.' },
  system: { eyebrow: 'PROVENANCE & READINESS', title: 'Data & system', description: 'Inspect the demo source boundary, provenance, freshness semantics, and distinct unknown states.' },
};

export function ProductExperience({ initialSection = 'overview', initialViewMode = '3d', adapter = demoAdapter }: { initialSection?: ProductSection; initialViewMode?: '3d' | '2d'; adapter?: ProductExperienceAdapter }) {
  const scenarios = adapter.listScenarios();
  const [section, setSection] = useState<ProductSection>(initialSection);
  const [scenarioId, setScenarioId] = useState(scenarios[0].id);
  const [frameIndex, setFrameIndex] = useState(0);
  const [viewMode, setViewMode] = useState<'3d' | '2d'>(initialViewMode);
  const [playing, setPlaying] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [selectedReservoirId, setSelectedReservoirId] = useState(scenarios[0].reservoirs[0].id);
  const [inputs, setInputs] = useState<WhatIfInputs>({ ...defaultWhatIfInputs });
  const [layers, setLayers] = useState({ water: true, blocks: true, roads: true });
  const scenario = scenarios.find((item) => item.id === scenarioId) ?? scenarios[0];
  const workspace = useMemo(() => adapter.getWorkspace(scenarioId, frameIndex, inputs), [adapter, scenarioId, frameIndex, inputs]);
  const heading = sectionTitles[section];

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReducedMotion(media.matches);
    update();
    media.addEventListener?.('change', update);
    return () => media.removeEventListener?.('change', update);
  }, []);

  useEffect(() => {
    if (!playing || reducedMotion) return;
    const timer = window.setInterval(() => setFrameIndex((current) => advanceDemoFrame(current, 1, scenario.frames.length, true)), 1400);
    return () => window.clearInterval(timer);
  }, [playing, reducedMotion, scenario.frames.length]);

  useEffect(() => {
    if (reducedMotion && playing) setPlaying(false);
  }, [playing, reducedMotion]);

  function selectScenario(id: string) {
    setScenarioId(id);
    setFrameIndex(0);
    setSelectedReservoirId((scenarios.find((item) => item.id === id) ?? scenarios[0]).reservoirs[0].id);
    setInputs(adapter.getInitialInputs(id));
    setPlaying(false);
  }

  function updateInputs(next: Partial<WhatIfInputs>) {
    setInputs((current) => ({ ...current, ...next }));
  }

  function navigateTo(next: ProductSection) {
    setSection(next);
    if (next !== 'twin') setPlaying(false);
  }

  return (
    <div className="tg-product">
      <a className="tg-product__skip" href="#tg-product-main">Skip to main content</a>
      <header className="tg-product__masthead">
        <a className="tg-product__brand" href="#tg-product-main" onClick={() => navigateTo('overview')} aria-label="TwinGuard demo overview">
          <span className="tg-product__brand-mark" aria-hidden="true"><i /><i /><i /></span>
          <span><strong>TwinGuard</strong><small>CHENNAI FLOOD MANAGEMENT</small></span>
        </a>
        <div className="tg-product__brand-pitch"><strong>Urban flood intelligence &amp; decision support</strong><small>Scenario workspace · synthetic values · research outputs clearly identified</small></div>
        <div className="tg-product__masthead-status">
          <span className="tg-product__location-chip"><span aria-hidden="true">⌖</span> Chennai study area <b>DEMO</b></span>
          <span className="tg-product__live-status" role="status" aria-label="Live data is not connected"><i aria-hidden="true"/><span><small>LIVE INPUT</small><strong>NOT CONNECTED</strong></span></span>
        </div>
      </header>
      <nav className="tg-product__nav" aria-label="Product sections">
          {sections.map((item) => <button type="button" key={item.id} className={section === item.id ? 'is-active' : ''} aria-label={item.label} aria-current={section === item.id ? 'page' : undefined} onClick={() => navigateTo(item.id)}>
            <span className="tg-product__nav-icon" aria-hidden="true"><SectionIcon section={item.id} /></span><span className="tg-product__nav-text" aria-hidden="true"><strong className="tg-product__nav-full">{item.label}</strong><strong className="tg-product__nav-compact">{item.short}</strong><small>{item.number} · {item.short}</small></span>
          </button>)}
      </nav>

      <div className="tg-product__main">
        <header className="tg-product__topbar">
          <div className="tg-product__crumb"><span>TWINGUARD</span><span aria-hidden="true">/</span><strong>{heading.title}</strong></div>
          <div className="tg-product__top-actions">
            <label className="tg-product__scenario-select"><span>DEMO SCENARIO</span><select value={scenarioId} onChange={(event) => selectScenario(event.target.value)} aria-label="Select demo scenario">
              {scenarios.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select></label>
            <DemoPill mode={scenario.provenance.sourceMode} />
            <small className="tg-product__gate-snapshot" role="status" aria-label={`Gate G0: ${gateText(normalizeGateStatus(import.meta.env.VITE_GATE_G0_STATUS))}`} data-gate-status={normalizeGateStatus(import.meta.env.VITE_GATE_G0_STATUS)}>G0 {gateText(normalizeGateStatus(import.meta.env.VITE_GATE_G0_STATUS))}</small>
          </div>
        </header>

        <main id="tg-product-main" className="tg-product__content" tabIndex={-1}>
          <header className="tg-product__page-heading"><div><span className="tg-product__eyebrow">{heading.eyebrow}</span><h1>{heading.title}</h1><p>{heading.description}</p></div><div className="tg-product__heading-status"><DemoPill mode="DEMO" /><span>NOT AN OPERATIONAL SERVICE</span></div></header>
          <div className="tg-product__demo-banner" role="note"><strong>DEMO / SIMULATED</strong><span>Every changing value and water shape is a synthetic UI example. This workspace does not provide flood warnings, safe routes, or operational readiness.</span></div>
          <ScenarioContextBar scenario={scenario} frame={workspace.frame} frameIndex={workspace.frameIndex} onSection={navigateTo} />

          {section === 'overview' && <OverviewSection scenario={scenario} frame={workspace.adjustedFrame} workspace={workspace} frameIndex={workspace.frameIndex} setFrameIndex={setFrameIndex} viewMode={viewMode} setViewMode={setViewMode} onSection={navigateTo} />}
          {section === 'twin' && <TwinSection scenario={scenario} frame={workspace.adjustedFrame} frameIndex={workspace.frameIndex} viewMode={viewMode} setViewMode={setViewMode} playing={playing} setPlaying={setPlaying} reducedMotion={reducedMotion} setFrameIndex={setFrameIndex} layers={layers} setLayers={setLayers} />}
          {section === 'reservoirs' && <ReservoirsSection scenario={scenario} selectedId={selectedReservoirId} onSelect={setSelectedReservoirId} frame={workspace.frame} />}
          {section === 'impacts' && <ImpactsSection workspace={workspace} />}
          {section === 'response' && <ResponseSection workspace={workspace} inputs={inputs} onUpdate={updateInputs} />}
          {section === 'what-if' && <WhatIfSection workspace={workspace} inputs={inputs} onUpdate={updateInputs} onReset={() => setInputs(adapter.getInitialInputs(scenarioId))} onScenarioChange={selectScenario} adapter={adapter} />}
          {section === 'system' && <SystemSection scenario={scenario} gateStatus={normalizeGateStatus(import.meta.env.VITE_GATE_G0_STATUS)} />}

          <footer className="tg-product__footer"><span>TWINGUARD · DEMO EXPERIENCE</span><span>All values are synthetic · no service calls</span><span>G0 {gateText(normalizeGateStatus(import.meta.env.VITE_GATE_G0_STATUS))}</span></footer>
        </main>
      </div>
    </div>
  );
}

export type GateStatus = 'ready' | 'not_ready' | 'unknown';
export function normalizeGateStatus(value: unknown): GateStatus { return value === 'ready' || value === 'not_ready' ? value : 'unknown'; }
export function gateText(value: GateStatus): string { return value === 'ready' ? 'READY' : value === 'not_ready' ? 'NOT READY' : 'STATUS UNKNOWN'; }

function DemoPill({ mode }: { mode: 'DEMO' | 'SIMULATED' }) { return <span className={`tg-product__pill tg-product__pill--${mode.toLowerCase()}`}><i aria-hidden="true">{mode === 'DEMO' ? 'D' : 'S'}</i>{mode}</span>; }
function SectionIcon({ section }: { section: ProductSection }) {
  const shared = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.65, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  return <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    {section === 'overview' && <g {...shared}><path d="M3.5 7.2 12 3l8.5 4.2v9.6L12 21l-8.5-4.2z"/><path d="m3.8 7.5 8.2 4 8.2-4M12 11.5V21M7.4 5.1v4.2"/></g>}
    {section === 'twin' && <g {...shared}><path d="m12 2.8 8.2 4.6v9.2L12 21.2l-8.2-4.6V7.4z"/><path d="m3.8 7.4 8.2 4.7 8.2-4.7M12 12.1v9"/><path d="m8 5.1 8.1 4.6"/></g>}
    {section === 'reservoirs' && <g {...shared}><path d="M4 6.5h16M5.2 6.5v10.8M18.8 6.5v10.8M4 17.3h16M3.5 20h17"/><path d="M7 10.2c1.2-1.1 2.5-1.1 3.7 0s2.5 1.1 3.7 0 2.2-1.1 3.3 0"/></g>}
    {section === 'impacts' && <g {...shared}><path d="M4 20V11M10 20V5M16 20v-7M22 20H2"/><circle cx="4" cy="8" r="1.4"/><circle cx="10" cy="3" r="1.4"/><circle cx="16" cy="10" r="1.4"/></g>}
    {section === 'response' && <g {...shared}><circle cx="5" cy="18" r="2"/><circle cx="19" cy="6" r="2"/><path d="M7 18h4.5a3 3 0 0 0 3-3v-3a3 3 0 0 1 3-3H19M14 4l3 2-3 2"/><path d="M3 5h5M5.5 2.5v5"/></g>}
    {section === 'what-if' && <g {...shared}><path d="M9 3h6M10 3v6.2L5.3 18a2 2 0 0 0 1.7 3h10a2 2 0 0 0 1.7-3L14 9.2V3"/><path d="M7.2 16h9.6M9.2 12h5.6"/><circle cx="15.7" cy="15" r=".6" fill="currentColor" stroke="none"/></g>}
    {section === 'system' && <g {...shared}><rect x="4" y="3" width="16" height="5" rx="1.5"/><rect x="4" y="10" width="16" height="5" rx="1.5"/><rect x="4" y="17" width="16" height="4" rx="1.5"/><path d="M7.2 5.5h.1M7.2 12.5h.1M7.2 19h.1"/></g>}
  </svg>;
}
function ScenarioContextBar({ scenario, frame, frameIndex, onSection }: { scenario: DemoScenario; frame: DemoFrame; frameIndex: number; onSection: (section: ProductSection) => void }) {
  return <section className="tg-product__context-bar" aria-label="Selected scenario context">
    <div className="tg-product__context-lead"><span className="tg-product__context-glyph" aria-hidden="true">◈</span><div><span className="tg-product__eyebrow">CURRENT SCENARIO</span><strong>{scenario.name}</strong><small>{scenario.provenance.runId} · {scenario.provenance.version}</small></div></div>
    <div className="tg-product__context-value"><span>SIMULATED STEP</span><strong>{frame.label}</strong><small>Step {frameIndex + 1} of {scenario.frames.length} · no calendar timestamp</small></div>
    <div className="tg-product__context-value"><span>SCENARIO SOURCE</span><strong><DemoPill mode={scenario.provenance.sourceMode} /></strong><small>{scenario.provenance.timeBasis}</small></div>
    <div className="tg-product__context-analysis"><span className="tg-product__context-analysis-icon" aria-hidden="true">↗</span><div><span className="tg-product__eyebrow">DECISION STABILITY</span><strong>Analysis pending</strong><small>A21 results are not connected to this demo.</small></div><button type="button" onClick={() => onSection('what-if')}>Explore scenarios <span aria-hidden="true">→</span></button></div>
  </section>;
}
function SectionCard({ title, eyebrow, children, className = '' }: { title: string; eyebrow?: string; children: React.ReactNode; className?: string }) {
  return <section className={`tg-product__card ${className}`}><div className="tg-product__card-heading">{eyebrow && <span className="tg-product__eyebrow">{eyebrow}</span>}<h2>{title}</h2></div>{children}</section>;
}

function ConceptCityScene({ frame, frameIndex, frameCount }: { frame: DemoFrame; frameIndex: number; frameCount: number }) {
  return <div className="tg-product__concept-scene" role="img" aria-label="Fictional flood-city concept artwork. Static illustration only; it is not a Chennai map, measured flood, or simulation output.">
    <img src={floodCityConcept} alt="" />
    <div className="tg-product__concept-scrim" aria-hidden="true" />
    <div className="tg-product__concept-topline"><span className="tg-product__concept-label"><i /> CITY TWIN CONCEPT ART</span><span className="tg-product__concept-label tg-product__concept-label--quiet">FICTIONAL SCENE · NOT GEOREFERENCED</span></div>
    <div className="tg-product__concept-caption"><div><span>SELECTED DEMO STEP</span><strong>{frame.label}</strong><small>Step {frameIndex + 1} of {frameCount} · this artwork is static</small></div><span className="tg-product__concept-water-tag">ILLUSTRATIVE WATER</span></div>
    <div className="tg-product__concept-disclaimer">Concept artwork · no measured depth, flood extent, building impact, or hydraulic result</div>
  </div>;
}

function OverviewSection({ scenario, frame, workspace, frameIndex, setFrameIndex, viewMode, setViewMode, onSection }: { scenario: DemoScenario; frame: DemoFrame; workspace: DemoWorkspace; frameIndex: number; setFrameIndex: (index: number) => void; viewMode: '3d' | '2d'; setViewMode: (mode: '3d' | '2d') => void; onSection: (section: ProductSection) => void }) {
  return <div className="tg-product__overview-layout">
    <aside className="tg-product__overview-snapshot" aria-label="Demo scenario snapshot">
      <div className="tg-product__snapshot-head"><div><span className="tg-product__eyebrow">SCENARIO SNAPSHOT</span><h2>City context</h2></div><DemoPill mode={scenario.provenance.sourceMode} /></div>
      <div className="tg-product__snapshot-brief"><strong>{scenario.name}</strong><p>{scenario.description}</p><span>{scenario.provenance.runId} · {scenario.provenance.version}</span></div>
      <StateBadge kind="unavailable" label="Live observations" detail="No rainfall, reservoir, or warning feed is connected." />
      <div className="tg-product__snapshot-metrics"><Metric label="Population exposure" value={workspace.adjustedImpact.populationExposure} unit="synthetic people" /><Metric label="Facilities" value={workspace.adjustedImpact.facilities} unit="fictional records" /><Metric label="Road segments" value={workspace.adjustedImpact.roadSegments} unit="illustrative graph" /></div>
      <p className="tg-product__limit-copy">Separate fixture counts; no combined risk score or geographic footprint.</p>
      <button type="button" className="tg-product__text-link" onClick={() => onSection('impacts')}>Open impact layers <span aria-hidden="true">→</span></button>
    </aside>

    <section className="tg-product__overview-map" aria-labelledby="overview-map-title">
      <div className="tg-product__map-heading"><div><span className="tg-product__eyebrow">SPATIAL WORKSPACE · DEMO</span><h2 id="overview-map-title">Flood city twin</h2></div><div className="tg-product__segmented" role="group" aria-label="Overview display mode"><button type="button" aria-pressed={viewMode === '3d'} onClick={() => setViewMode('3d')}>3D concept</button><button type="button" aria-pressed={viewMode === '2d'} onClick={() => setViewMode('2d')}>2D schematic</button></div></div>
      {viewMode === '3d' ? <ConceptCityScene frame={frame} frameIndex={frameIndex} frameCount={scenario.frames.length} /> : <Illustration frame={frame} mode="2d" />}
      <div className="tg-product__overview-timeline"><div className="tg-product__overview-time-copy"><DemoPill mode="SIMULATED" /><strong>{frame.label}</strong><span>Local fixture step · no calendar timestamp</span></div><label><span className="tg-product__visually-hidden">Select illustrative demo time step</span><input aria-label="Select illustrative demo time step" type="range" min="0" max={scenario.frames.length - 1} step="1" value={frameIndex} onChange={(event) => setFrameIndex(Number(event.target.value))} /></label><button type="button" className="tg-product__button tg-product__button--primary" onClick={() => onSection('twin')}>Open interactive twin <span aria-hidden="true">→</span></button></div>
    </section>

    <aside className="tg-product__overview-controls" aria-label="Demo controls and source readiness">
      <section className="tg-product__control-panel"><div className="tg-product__panel-title"><span className="tg-product__control-play" aria-hidden="true">▶</span><div><span className="tg-product__eyebrow">SIMULATION CONTROL</span><h2>Explore a demo step</h2></div></div>
        <div className="tg-product__mode-row"><span>Current source</span><strong><DemoPill mode={scenario.provenance.sourceMode} /></strong></div>
        <div className="tg-product__mode-row"><span>Live source</span><strong className="tg-product__unavailable-value">Not connected</strong></div>
        <label className="tg-product__field"><span>Selected scenario</span><strong className="tg-product__field-readout">{scenario.name}</strong><small>Change scenarios from the header selector.</small></label>
        <label className="tg-product__horizon-field"><span>Fixture timeline</span><input aria-label="Select demo fixture step" type="range" min="0" max={scenario.frames.length - 1} step="1" value={frameIndex} onChange={(event) => setFrameIndex(Number(event.target.value))} /><span className="tg-product__horizon-labels"><small>T+0</small><small>T+2</small><small>T+4</small><small>T+6</small></span></label>
        <div className="tg-product__control-actions"><button type="button" className="tg-product__button" onClick={() => setFrameIndex((frameIndex + scenario.frames.length - 1) % scenario.frames.length)}>Previous</button><button type="button" className="tg-product__button tg-product__button--primary" onClick={() => onSection('what-if')}>Open what-if lab <span aria-hidden="true">→</span></button></div>
        <p className="tg-product__limit-copy">The step control changes local demo fixtures only. It does not run a forecast or physical flood solver.</p>
      </section>
      <section className="tg-product__source-panel"><div className="tg-product__panel-title"><span className="tg-product__source-mark" aria-hidden="true">◉</span><div><span className="tg-product__eyebrow">DATA READINESS</span><h2>Source status</h2></div></div>
        <div className="tg-product__source-line"><i className="is-demo"/><span><strong>Demo fixtures</strong><small>Available · local only</small></span><b>ACTIVE</b></div>
        <div className="tg-product__source-line"><i className="is-pending"/><span><strong>Saved research outputs</strong><small>Separate evidence; not loaded in this screen</small></span><b>SEPARATE</b></div>
        <div className="tg-product__source-line"><i className="is-offline"/><span><strong>Live feeds</strong><small>Approved observation endpoint unavailable</small></span><b>OFFLINE</b></div>
        <p className="tg-product__limit-copy">No connectivity or source health is inferred from this static demo.</p>
      </section>
    </aside>

    <div className="tg-product__overview-bottom" aria-label="Demo workspace shortcuts">
      <button type="button" className="tg-product__overview-tile" onClick={() => onSection('reservoirs')}><span className="tg-product__tile-icon" aria-hidden="true"><SectionIcon section="reservoirs"/></span><span><small>RESERVOIR FIXTURES · DEMO</small><strong>{scenario.reservoirs.length} sample records</strong><em>Inspect values and unknown states</em></span><b aria-hidden="true">→</b></button>
      <button type="button" className="tg-product__overview-tile" onClick={() => onSection('response')}><span className="tg-product__tile-icon" aria-hidden="true"><SectionIcon section="response"/></span><span><small>ROUTE &amp; SHELTER · DEMO</small><strong>Hazard assessment unknown</strong><em>No route is marked safe</em></span><b aria-hidden="true">→</b></button>
      <button type="button" className="tg-product__overview-tile" onClick={() => onSection('what-if')}><span className="tg-product__tile-icon" aria-hidden="true"><SectionIcon section="what-if"/></span><span><small>WHAT-IF WORKSPACE</small><strong>Explore local assumptions</strong><em>Fictional inputs · no model run</em></span><b aria-hidden="true">→</b></button>
    </div>
  </div>;
}

function TwinSection({ scenario, frame, frameIndex, viewMode, setViewMode, playing, setPlaying, reducedMotion, setFrameIndex, layers, setLayers }: {
  scenario: DemoScenario; frame: DemoFrame; frameIndex: number; viewMode: '3d' | '2d'; setViewMode: (mode: '3d' | '2d') => void;
  playing: boolean; setPlaying: (playing: boolean) => void; reducedMotion: boolean; setFrameIndex: (index: number) => void;
  layers: { water: boolean; blocks: boolean; roads: boolean }; setLayers: (next: { water: boolean; blocks: boolean; roads: boolean }) => void;
}) {
  return <div className="tg-product__twin-layout">
    <SectionCard title="Illustrative flood scene" eyebrow="UI-ONLY WATER MOTION" className="tg-product__twin-main">
      <div className="tg-product__twin-toolbar"><div><DemoPill mode="SIMULATED" /><span>Visual level {frame.visualLevel} of 4 · no depth units</span></div><div className="tg-product__segmented" role="group" aria-label="Map display mode"><button type="button" aria-pressed={viewMode === '3d'} onClick={() => setViewMode('3d')}>3D view</button><button type="button" aria-pressed={viewMode === '2d'} onClick={() => setViewMode('2d')}>2D fallback</button></div></div>
      <Illustration frame={frame} mode={viewMode} layers={layers} />
      <div className="tg-product__animation-caption" role="status" aria-live="polite"><strong>{frame.label}</strong><span>Illustrative water graphic · not a saved raster, terrain, or hydraulic result</span></div>
      <div className="tg-product__timeline-controls">
        <button type="button" className="tg-product__button" onClick={() => { setPlaying(false); setFrameIndex(advanceDemoFrame(frameIndex, -1, scenario.frames.length)); }} disabled={frameIndex === 0}>Previous step</button>
        <button type="button" className="tg-product__button tg-product__button--primary" onClick={() => setPlaying(!playing)} aria-pressed={playing} disabled={reducedMotion}>{reducedMotion ? 'Playback paused for reduced motion' : playing ? 'Pause demo' : 'Play demo'}</button>
        <button type="button" className="tg-product__button" onClick={() => { setPlaying(false); setFrameIndex(advanceDemoFrame(frameIndex, 1, scenario.frames.length, true)); }}>Next step</button>
        <button type="button" className="tg-product__button tg-product__button--quiet" onClick={() => { setPlaying(false); setFrameIndex(0); }}>Reset</button>
      </div>
      <label className="tg-product__timeline"><span>DEMO TIME STEP</span><input aria-label="Select illustrative demo time step" type="range" min="0" max={scenario.frames.length - 1} step="1" value={frameIndex} onChange={(event) => { setPlaying(false); setFrameIndex(Number(event.target.value)); }} /><output>{frameIndex + 1} / {scenario.frames.length}</output></label>
      <div className="tg-product__step-labels" aria-hidden="true">{scenario.frames.map((item, i) => <span className={i === frameIndex ? 'is-current' : ''} key={item.id}>{item.label.split('·')[0].trim()}</span>)}</div>
      {reducedMotion && <p className="tg-product__reduced-note" role="status">Reduced motion is enabled. Automatic playback is paused; manual step controls remain available.</p>}
    </SectionCard>
    <aside className="tg-product__twin-rail">
      <SectionCard title="Display layers" eyebrow="ILLUSTRATION CONTROLS"><label className="tg-product__check"><input type="checkbox" checked={layers.water} onChange={(event) => setLayers({ ...layers, water: event.target.checked })} /> <span>Demo water shape</span><DemoPill mode="SIMULATED" /></label><label className="tg-product__check"><input type="checkbox" checked={layers.blocks} onChange={(event) => setLayers({ ...layers, blocks: event.target.checked })} /> <span>Illustrative blocks</span><DemoPill mode="DEMO" /></label><label className="tg-product__check"><input type="checkbox" checked={layers.roads} onChange={(event) => setLayers({ ...layers, roads: event.target.checked })} /> <span>Illustrative roads</span><DemoPill mode="DEMO" /></label><p className="tg-product__limit-copy">Geometry is a hand-authored interface illustration and has no Chennai coordinates.</p></SectionCard>
      <SectionCard title="Legend & states" eyebrow="NO MEASURED FLOOD SCALE"><LegendSwatch label="Demo water graphic" tone="water" /><LegendSwatch label="Demo dry area" tone="dry" /><LegendSwatch label="NoData / unknown coverage" tone="nodata" /><p className="tg-product__limit-copy">NoData is a missing-coverage state, never a dry classification. Visual level is unitless.</p></SectionCard>
      <SectionCard title="Saved context" eyebrow="SYNTHETIC CLOCK"><InfoLine label="Scenario" value={scenario.name} /><InfoLine label="Time" value={frame.label} /><InfoLine label="Source" value="Central UI fixture" /><InfoLine label="Run / version" value={`${scenario.provenance.runId} · ${scenario.provenance.version}`} /><InfoLine label="Uncertainty" value="Not estimated" /></SectionCard>
    </aside>
  </div>;
}

function Illustration({ frame, mode, compact = false, layers = { water: true, blocks: true, roads: true } }: { frame: DemoFrame; mode: '3d' | '2d'; compact?: boolean; layers?: { water: boolean; blocks: boolean; roads: boolean } }) {
  const uid = useId().replace(/:/g, '');
  const groundId = `tg-ground-${uid}`;
  const waterId = `tg-water-${uid}`;
  const waterGlowId = `tg-water-glow-${uid}`;
  const noDataId = `tg-nodata-${uid}`;
  const label = mode === '3d' ? 'Illustrative isometric city blocks, roads, and synthetic water shape' : 'Top-down illustrative city grid using the selected synthetic step';
  const buildings = [
    { x: 53, y: 86, w: 18, d: 12, h: 22, tone: '#b8cbd0' }, { x: 91, y: 72, w: 18, d: 12, h: 31, tone: '#8eafb9' },
    { x: 137, y: 56, w: 21, d: 12, h: 37, tone: '#d0c6ab' }, { x: 186, y: 58, w: 19, d: 12, h: 26, tone: '#8fb4c1' },
    { x: 237, y: 72, w: 23, d: 13, h: 42, tone: '#bfc8ba' }, { x: 292, y: 93, w: 20, d: 12, h: 28, tone: '#90b8bd' },
    { x: 104, y: 119, w: 20, d: 12, h: 19, tone: '#d1c5aa' }, { x: 192, y: 119, w: 22, d: 13, h: 32, tone: '#b3c9cc' },
    { x: 271, y: 137, w: 18, d: 12, h: 24, tone: '#c8c3ae' },
  ];
  return <div className={`tg-product__scene tg-product__scene--${mode}${compact ? ' is-compact' : ''}`} role="img" aria-label={`${label}. Schematic only: no geographic coordinates, measured depths, or hydraulic result.`}>
    {mode === '3d' ? <svg viewBox="0 0 420 280" aria-hidden="true" focusable="false" preserveAspectRatio="xMidYMid meet">
      <defs>
        <linearGradient id={groundId} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#263f4a"/><stop offset=".52" stopColor="#18343e"/><stop offset="1" stopColor="#122730"/></linearGradient>
        <linearGradient id={waterId} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#a1f0e1" stopOpacity=".86"/><stop offset=".38" stopColor="#45c8d3" stopOpacity=".9"/><stop offset="1" stopColor="#14769f" stopOpacity=".97"/></linearGradient>
        <filter id={waterGlowId} x="-20%" y="-25%" width="140%" height="160%"><feGaussianBlur stdDeviation="5" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        <pattern id={noDataId} width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="8" fill="#22343b"/><path d="M0 0V8" stroke="#71868b" strokeWidth="2"/></pattern>
        <clipPath id={`${waterId}-clip`}><path d={frame.waterPath3d}/></clipPath>
      </defs>
      <rect width="420" height="280" fill="#0b1b25"/>
      <circle cx="215" cy="132" r="164" fill="#163a44" opacity=".32"/>
      <path d="M25 77 210 14 395 79 210 147Z" fill={`url(#${groundId})`} stroke="#69878a" strokeWidth="1.3"/>
      <path d="M25 77v116l185 72V147Z" fill="#19313b" stroke="#42616a"/>
      <path d="M210 147v118l185-72V79Z" fill="#112630" stroke="#42616a"/>
      <path d="M39 82 210 23 381 83M52 94l158-54 157 55M65 107l145-50 144 52M78 120l132-45 132 48M91 133l119-41 119 44M34 108l176 67 177-67M31 139l178 68 178-70M28 170l181 67 181-71" fill="none" stroke="#9bb4b2" strokeOpacity=".17" strokeWidth="1"/>
      {layers.roads && <g fill="none" strokeLinecap="round">
        <path d="M45 96 210 154 367 97M42 126l167 64 168-65M39 157l169 66 169-67" stroke="#091820" strokeWidth="10" opacity=".9"/>
        <path d="M45 96 210 154 367 97M42 126l167 64 168-65M39 157l169 66 169-67" stroke="#91a9a4" strokeWidth="1.4" strokeDasharray="3 7" opacity=".8"/>
      </g>}
      {layers.blocks && <g>
        {buildings.map((building, index) => {
          const { x, y, w, d, h, tone } = building;
          return <g key={index}>
            <polygon points={`${x},${y-h} ${x+w},${y-h-4} ${x+w+d},${y-h} ${x+d},${y-h+4}`} fill={tone} stroke="#e2ece8" strokeOpacity=".48" strokeWidth=".7"/>
            <polygon points={`${x},${y-h} ${x+d},${y-h+4} ${x+d},${y+4} ${x},${y}`} fill="#56737a"/>
            <polygon points={`${x+w},${y-h-4} ${x+w+d},${y-h} ${x+w+d},${y} ${x+w},${y+4}`} fill="#314e59"/>
            <path d={`M${x+4} ${y-h+5}l${Math.max(4,w-7)} -1M${x+4} ${y-h+11}l${Math.max(4,w-7)} -1M${x+4} ${y-h+17}l${Math.max(4,w-7)} -1`} stroke="#f0f4e9" strokeOpacity=".46" strokeWidth="1.2"/>
          </g>;
        })}
        <g fill="#5b9b83" stroke="#9ac8ad" strokeOpacity=".5"><path d="m60 139 26-9 25 10-26 10z"/><path d="m282 119 24-8 24 9-24 9z"/><path d="m137 154 18-6 18 7-18 7z"/></g>
      </g>}
      {layers.water && <g filter={`url(#${waterGlowId})`}>
        <path d={frame.waterPath3d} fill={`url(#${waterId})`} stroke="#8ff2e8" strokeOpacity=".9" strokeWidth="1.6"/>
        <g clipPath={`url(#${waterId}-clip)`} fill="none" stroke="#d5fff3" strokeOpacity=".23" strokeWidth="1.2">
          <path d="M-10 231C45 212 86 234 137 224S236 203 281 218s83 13 149-5"/><path d="M-10 246C48 226 88 249 143 238S239 219 285 233s86 13 145-6"/><path d="M-10 262C52 242 92 264 147 253s96-18 140-4 88 12 143-7"/>
        </g>
      </g>}
      <path d="M326 23h65v34h-65z" fill={`url(#${noDataId})`} stroke="#9aadb0" strokeDasharray="3 3" opacity=".92"/>
      <g fill="#e8f4f3" fontFamily="Inter,Segoe UI,sans-serif" fontSize="8" fontWeight="700" letterSpacing=".8"><text x="29" y="252">SCHEMATIC CITY BLOCKS</text><text x="324" y="68">UNKNOWN COVERAGE</text></g>
      <g fill="#b4d8d4" fontFamily="Inter,Segoe UI,sans-serif" fontSize="7" fontWeight="700" letterSpacing="1"><text x="43" y="89">ZONE 01</text><text x="298" y="180">ZONE 02</text><text x="175" y="102">DEMO CHANNEL</text></g>
    </svg> : <svg viewBox="0 0 420 280" aria-hidden="true" focusable="false" preserveAspectRatio="xMidYMid meet">
      <defs><pattern id={noDataId} width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="8" fill="#182d37"/><path d="M0 0V8" stroke="#73888d" strokeWidth="2"/></pattern></defs>
      <rect width="420" height="280" fill="#0c1d27"/>
      <path d="M0 0H420V280H0z" fill="#102630"/>
      {layers.roads && <g stroke="#668188" strokeOpacity=".36" strokeWidth="1"><path d="M22 18V262M74 18V262M126 18V262M178 18V262M230 18V262M282 18V262M334 18V262M386 18V262M12 44H408M12 91H408M12 138H408M12 185H408M12 232H408"/></g>}
      {layers.roads && <g fill="none" stroke="#9db0aa" strokeOpacity=".75"><path d="M15 67H405M15 161H405M99 18V262M307 18V262" strokeWidth="4"/><path d="M15 67H405M15 161H405M99 18V262M307 18V262" stroke="#e1c58d" strokeWidth="1" strokeDasharray="5 7"/></g>}
      {layers.blocks && <g fill="#344d55" stroke="#799196" strokeOpacity=".5"><path d="M27 25h54v32H27zM112 25h75v32h-75zM219 25h72v32h-72zM319 25h78v32h-78zM27 77h54v52H27zM113 77h74v52h-74zM219 77h72v52h-72zM320 77h77v52h-77zM27 171h54v52H27zM112 171h75v52h-75zM219 171h72v52h-72zM320 171h77v52h-77zM27 238h75v25H27zM114 238h74v25h-74zM220 238h71v25h-71zM319 238h78v25h-78z"/></g>}
      {layers.water && <path d={frame.waterPath2d} fill="#42bfd0" fillOpacity=".72" stroke="#9bf0e3" strokeWidth="1.5"/>}
      <path d="M335 18h69v38h-69z" fill={`url(#${noDataId})`} stroke="#a2b4b5" strokeDasharray="3 3"/>
      <g fill="#e8f4f3" fontFamily="Inter,Segoe UI,sans-serif" fontSize="8" fontWeight="700" letterSpacing=".7"><text x="17" y="270">SYNTHETIC GRID · NO GEOGRAPHIC COORDINATES</text><text x="341" y="72">NO DATA</text></g>
    </svg>}
    <span className="tg-product__scene-stamp">{mode === '3d' ? 'SCHEMATIC 3D' : '2D PLAN VIEW'} · DEMO</span>
  </div>;
}

function ReservoirsSection({ scenario, selectedId, onSelect, frame }: { scenario: DemoScenario; selectedId: string; onSelect: (id: string) => void; frame: DemoFrame }) {
  const selected = scenario.reservoirs.find((item) => item.id === selectedId) ?? scenario.reservoirs[0];
  return <div className="tg-product__reservoir-workspace">
    <nav className="tg-product__reservoir-index" aria-label="Demo reservoir fixtures"><span className="tg-product__eyebrow">FIXTURE INVENTORY · SIMULATED</span>{scenario.reservoirs.map((item, index) => <button type="button" key={item.id} className={selectedId === item.id ? 'is-selected' : ''} aria-pressed={selectedId === item.id} onClick={() => onSelect(item.id)}><span className="tg-product__index-number">0{index + 1}</span><span><strong>{item.name}</strong><small>{item.storageMcft === null ? 'Storage unknown' : `${item.storageMcft} mcft · DEMO`}</small></span><span aria-hidden="true">›</span></button>)}<p>Fictional fixture names and readings. Not real reservoir observations.</p></nav>
    <div className="tg-product__reservoir-detail-column"><div className="tg-product__reservoir-detail-head"><div><span className="tg-product__eyebrow">SELECTED FIXTURE · NO TELEMETRY</span><h2>{selected.name}</h2><p>Storage, capacity, and release fields are local demo values. Source date and operating status are not established.</p></div><DemoPill mode="SIMULATED" /></div><ReservoirDetail reservoir={selected} frame={frame} /><section className="tg-product__reservoir-history" aria-labelledby="reservoir-history-title"><div className="tg-product__section-minihead"><div><span className="tg-product__eyebrow">SYNTHETIC STEP HISTORY</span><h2 id="reservoir-history-title">Demo timeline</h2></div><span className="tg-product__plain-tag">NOT AN ALERT HISTORY</span></div><div className="tg-product__timeline-list">{scenario.frames.map((item, index) => <div className={index <= scenario.frames.findIndex((x) => x.id === frame.id) ? 'is-passed' : ''} key={item.id}><i aria-hidden="true" /><span>{item.label}</span><strong>{index === 1 && selected.id !== 'demo-unknown' ? 'DEMO WATCH' : 'SIMULATED'}</strong></div>)}</div><p className="tg-product__limit-copy">The selected frame is a synthetic clock step. Alert names and thresholds are fictional; no emergency warning is issued.</p></section></div>
  </div>;
}

function ReservoirDetail({ reservoir, frame, compact = false }: { reservoir: DemoReservoir; frame: DemoFrame; compact?: boolean }) {
  const hasStorage = reservoir.storageMcft !== null;
  const hasCapacity = reservoir.capacityMcft !== null && reservoir.capacityMcft > 0;
  const fill = reservoir.storageMcft !== null && reservoir.capacityMcft !== null && reservoir.capacityMcft > 0
    ? Math.min(100, (reservoir.storageMcft / reservoir.capacityMcft) * 100) : 0;
  return (
    <div className={`tg-product__reservoir-detail${compact ? ' is-compact' : ''}`}>
      <div className="tg-product__reservoir-title"><strong>{reservoir.name}</strong><DemoPill mode="SIMULATED" /></div>
      <div className="tg-product__gauge" role="img" aria-label={hasStorage ? hasCapacity ? `Demo storage ${reservoir.storageMcft} mcft of ${reservoir.capacityMcft} mcft` : `Demo storage ${reservoir.storageMcft} mcft; capacity unknown, normalized gauge unavailable` : 'Storage unknown; capacity unknown'}>
        <div className={!hasCapacity ? 'is-unavailable' : ''}>{hasCapacity && <span style={{ width: `${fill}%` }} />}</div><strong>{hasStorage ? `${reservoir.storageMcft} mcft` : 'Unknown'}</strong>
      </div>
      <div className="tg-product__reservoir-meta">
        <InfoLine label="Capacity" value={reservoir.capacityMcft === null ? 'Unknown' : `${reservoir.capacityMcft} mcft · DEMO`} />
        <InfoLine label="Release" value={reservoir.releaseCusecs === null ? 'Unknown' : `${reservoir.releaseCusecs} cusecs · DEMO`} />
        <InfoLine label="Fixture time" value={frame.label} />
      </div>
      <div className="tg-product__sparkline" role="img" aria-label={reservoir.history.length ? `Synthetic storage history: ${reservoir.history.join(', ')} mcft` : 'History unavailable; no fixture values supplied'}>
        {reservoir.history.length ? reservoir.history.map((value, index) => <i key={`${index}-${value}`} style={{ height: `${Math.max(4, value / Math.max(...reservoir.history, 1) * 30)}px` }} />) : <span>History unavailable</span>}
      </div>
      <small className="tg-product__fine-print">DEMO values · no source date or operational status</small>
    </div>
  );
}

function ImpactsSection({ workspace }: { workspace: DemoWorkspace }) {
  const impact = workspace.adjustedImpact;
  return <div className="tg-product__impact-workspace">
    <section className="tg-product__impact-map" aria-labelledby="impact-map-title"><div className="tg-product__map-heading"><div><span className="tg-product__eyebrow">SYNTHETIC FOOTPRINT · NOT TO SCALE</span><h2 id="impact-map-title">Illustrative layer view</h2></div><DemoPill mode="SIMULATED" /></div><Illustration frame={workspace.adjustedFrame} mode="2d" /><div className="tg-product__impact-map-foot"><strong>Visual level {workspace.adjustedVisualLevel} / 4 · unitless demo</strong><span>Not an extent, depth, risk score, or geographic area.</span></div></section>
    <aside className="tg-product__impact-ledger"><div className="tg-product__section-minihead"><div><span className="tg-product__eyebrow">SEPARATE FIXTURE COUNTS</span><h2>Impact indicators</h2></div><DemoPill mode="DEMO" /></div><Metric label="Population exposure" value={impact.populationExposure} unit="synthetic people" /><Metric label="Facilities" value={impact.facilities} unit="fictional records" /><Metric label="Road segments" value={impact.roadSegments} unit="illustrative segments" /><div className="tg-product__impact-unknown"><StateBadge kind="unknown" label="Road hazard assessment" detail="Unknown for all demo route segments." /></div><p className="tg-product__limit-copy">No observed exposure or facility status. No combined vulnerability score, priority ranking, or operational recommendation.</p></aside>
    <div className="tg-product__disclaimer"><strong>Interpretation boundary</strong><span>{impact.note} Missing spatial coverage is not represented as dry or as zero impact.</span></div>
  </div>;
}

function ResponseSection({ workspace, inputs, onUpdate }: { workspace: DemoWorkspace; inputs: WhatIfInputs; onUpdate: (next: Partial<WhatIfInputs>) => void }) {
  const routes = workspace.adjustedRoutes;
  return <div className="tg-product__response-layout">
    <section className="tg-product__response-routes" aria-labelledby="response-routes-title"><div className="tg-product__section-minihead"><div><span className="tg-product__eyebrow">LOCAL SYNTHETIC GRAPH</span><h2 id="response-routes-title">Candidate route comparison</h2></div><DemoPill mode="DEMO" /></div><p className="tg-product__card-intro">Fictional alternatives only. Reachability does not establish flood access or safety.</p><div className="tg-product__route-illustration" role="img" aria-label="Schematic demo graph connecting a fictional origin and destination; no geographic locations or safe route"><span>DEMO ORIGIN</span><i /><i /><i /><span>DEMO DESTINATION</span></div><div className="tg-product__route-table"><table><caption className="tg-product__visually-hidden">Synthetic route comparison; hazard assessment is unknown for every route.</caption><thead><tr><th scope="col">Candidate</th><th scope="col">Demo time</th><th scope="col">Topological connectivity</th><th scope="col">Hazard assessment</th></tr></thead><tbody>{routes.map((route) => <tr key={route.id}><th scope="row">{route.name}<small>{route.mode} · {route.distanceKm} demo km</small></th><td>{route.minutes === 0 ? '0 min · DEMO' : `${route.minutes} min · DEMO`}</td><td>{route.topologicalReachability === 'connected' ? 'Connected (demo)' : 'Disconnected (demo)'}<small>{route.note}</small></td><td>Unknown</td></tr>)}</tbody></table></div>
      <div className="tg-product__evidence-model" aria-labelledby="evidence-model-title"><div className="tg-product__evidence-model-head"><div><span className="tg-product__eyebrow">UPCOMING A21 ANALYSIS · NOT CONNECTED</span><h3 id="evidence-model-title">Road evidence states</h3></div><span className="tg-product__pending-tag">PENDING</span></div><div className="tg-product__evidence-state-grid"><article><i className="tg-product__evidence-dot tg-product__evidence-dot--passable" /><div><strong>Assessed passable</strong><small>Model assessed the edge below its stated threshold.</small></div></article><article><i className="tg-product__evidence-dot tg-product__evidence-dot--blocked" /><div><strong>Assessed blocked</strong><small>Model assessed the edge at or above its stated threshold.</small></div></article><article><i className="tg-product__evidence-dot tg-product__evidence-dot--unknown" /><div><strong>Unknown · verify</strong><small>Coverage is missing or ambiguous. It is not treated as passable.</small></div></article></div><p className="tg-product__limit-copy">This is a conceptual legend for the planned analysis. The route rows above do not use these classifications yet.</p></div>
      <p className="tg-product__limit-copy">No real graph, flood assessment, geographic location, or route safety is provided.</p></section>
    <section className="tg-product__response-shelters" aria-labelledby="shelter-title"><div className="tg-product__section-minihead"><div><span className="tg-product__eyebrow">SYNTHETIC FIXTURE INVENTORY</span><h2 id="shelter-title">Shelter candidates</h2></div><span className="tg-product__plain-tag">UNVERIFIED</span></div><div className="tg-product__shelter-list">{workspace.scenario.shelters.map((shelter) => <article className={inputs.unavailableShelterId === shelter.id ? 'is-unavailable' : ''} key={shelter.id}><div><strong>{shelter.name}</strong><DemoPill mode="SIMULATED" /></div><p>{inputs.unavailableShelterId === shelter.id ? 'Marked unavailable in this what-if demo.' : `${shelter.demoSlots} demo slots · fictional capacity`}</p><small>{shelter.note}</small><label className="tg-product__check"><input type="checkbox" checked={inputs.unavailableShelterId === shelter.id} onChange={(event) => onUpdate(setDemoShelterAvailability(inputs, shelter.id, event.target.checked))} /><span>Toggle unavailable in demo</span></label></article>)}</div><StateBadge kind="unknown" label="Verified shelters" detail="No verified facility or operating records are included." /><p className="tg-product__limit-copy">Candidates are fictional. No shelter is represented as open or operational.</p></section>
  </div>;
}

function WhatIfSection({ workspace, inputs, onUpdate, onReset, onScenarioChange, adapter }: { workspace: DemoWorkspace; inputs: WhatIfInputs; onUpdate: (next: Partial<WhatIfInputs>) => void; onReset: () => void; onScenarioChange: (scenarioId: string) => void; adapter: ProductExperienceAdapter }) {
  const impact = workspace.adjustedImpact;
  return <div className="tg-product__whatif-layout">
    <SectionCard title="Adjust demo assumptions" eyebrow="LOCAL FIXTURE ARITHMETIC" className="tg-product__whatif-controls">
      <label className="tg-product__field"><span>Scenario assumption</span><select aria-label="Choose what-if demo scenario" value={workspace.scenario.id} onChange={(event) => onScenarioChange(event.target.value)}>{adapter.listScenarios().map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.name}</option>)}</select><small>Changing scenario swaps the local synthetic fixture only.</small></label>
      <label className="tg-product__range-field"><span><strong>Illustrative rainfall input</strong><output>{inputs.rainfallMm} mm · DEMO</output></span><input type="range" min="0" max="120" step="10" value={inputs.rainfallMm} onChange={(event) => onUpdate({ rainfallMm: Number(event.target.value) })} /><small>Synthetic slider; not a weather observation or forecast.</small></label>
      <label className="tg-product__field"><span>Demo reservoir assumption</span><select aria-label="Choose demo reservoir assumption" value={inputs.reservoirId} onChange={(event) => onUpdate({ reservoirId: event.target.value })}>{workspace.scenario.reservoirs.map((reservoir) => <option key={reservoir.id} value={reservoir.id}>{reservoir.name}</option>)}</select><small>Fictional selection only; does not identify a real reservoir.</small></label>
      <label className="tg-product__range-field"><span><strong>Illustrative reservoir release</strong><output>{inputs.reservoirReleaseCusecs} cusecs · DEMO</output></span><input type="range" min="0" max="600" step="30" value={inputs.reservoirReleaseCusecs} onChange={(event) => onUpdate({ reservoirReleaseCusecs: Number(event.target.value) })} /><small>Synthetic slider; does not model a real reservoir operation.</small></label>
      <label className="tg-product__field"><span>Shelter availability assumption</span><select aria-label="Choose demo unavailable shelter" value={inputs.unavailableShelterId ?? ''} onChange={(event) => onUpdate({ unavailableShelterId: event.target.value || null })}><option value="">No candidate marked unavailable</option>{workspace.scenario.shelters.map((shelter) => <option key={shelter.id} value={shelter.id}>{shelter.name} · mark unavailable</option>)}</select><small>Updates only the fictional candidate list in Emergency Response.</small></label>
      <button type="button" className="tg-product__button" onClick={onReset}>Reset demo assumptions</button>
      <p className="tg-product__callout" role="note"><strong>Demo calculations only</strong><span>Changing inputs updates the local illustration and simple fixture arithmetic. No backend model runs.</span></p>
    </SectionCard>
    <SectionCard title="Baseline vs modified" eyebrow="DEMO COMPARISON"><div className="tg-product__comparison"><ComparisonColumn title="BASELINE · DEMO" population={workspace.baseline.populationExposure} facilities={workspace.baseline.facilities} roads={workspace.baseline.roadSegments} visual={workspace.frame.visualLevel} /><span className="tg-product__comparison-arrow" aria-hidden="true">→</span><ComparisonColumn title="MODIFIED · SIMULATED" population={impact.populationExposure} facilities={impact.facilities} roads={impact.roadSegments} visual={workspace.adjustedVisualLevel} /></div><p className="tg-product__limit-copy">Values are generated by transparent local arithmetic on fictional fixtures. They are not predictions, risk levels, or validated counterfactual outcomes.</p></SectionCard>
    <SectionCard title="Decision stability" eyebrow="A21 · NOT CONNECTED" className="tg-product__span-two tg-product__stability-pending"><div className="tg-product__stability-layout"><span className="tg-product__stability-mark" aria-hidden="true">↔</span><div><h3>Will the preferred choice hold across scenarios?</h3><p>The planned analysis will compare route and shelter choices across saved simulation cases and identify conditions linked to changes. It has not produced results yet.</p><div className="tg-product__stability-points"><span>Route consistency <strong>Pending</strong></span><span>Shelter allocation consistency <strong>Pending</strong></span><span>Evidence to verify <strong>Pending</strong></span></div></div><span className="tg-product__pending-tag">WAITING FOR A21</span></div><p className="tg-product__limit-copy">No stability counts, likelihoods, or recommendations are shown. Scenario fractions, when available, will describe tested simulations only.</p></SectionCard>
    <SectionCard title="Current demo view" eyebrow="SAME SELECTED STEP" className="tg-product__span-two"><div className="tg-product__current-demo"><Illustration frame={workspace.adjustedFrame} mode="2d" compact /><div><DemoPill mode="SIMULATED" /><h3>{workspace.frame.label}</h3><p>Visual-only change from the synthetic input controls. Source, selected frame, and limitations remain visible.</p><InfoLine label="Input provenance" value="Central fixture + local UI arithmetic" /><InfoLine label="Time basis" value={workspace.scenario.provenance.timeBasis} /></div></div></SectionCard>
  </div>;
}

function ComparisonColumn({ title, population, facilities, roads, visual }: { title: string; population: number; facilities: number; roads: number; visual: number }) {
  return <div className="tg-product__comparison-column"><span>{title}</span><InfoLine label="Population demo count" value={String(population)} /><InfoLine label="Facility demo records" value={String(facilities)} /><InfoLine label="Road demo segments" value={String(roads)} /><InfoLine label="Visual level" value={`${visual} / 4 · unitless`} /></div>;
}

function SystemSection({ scenario, gateStatus }: { scenario: DemoScenario; gateStatus: GateStatus }) {
  const demoSource = demoScenarioMetadata({
    sourceIdentity: scenario.provenance.source,
    runId: scenario.provenance.runId,
    version: scenario.provenance.version,
    timeSemantics: scenario.provenance.timeBasis,
  });
  const liveSource = unavailableLiveMetadata('No source-owner-approved live feed is connected or verified.');
  return <div className="tg-product__system-layout">
    <section className="tg-product__system-source" aria-labelledby="system-source-title"><div className="tg-product__section-minihead"><div><span className="tg-product__eyebrow">PROVENANCE REGISTER</span><h2 id="system-source-title">Source and run context</h2></div><DemoPill mode={scenario.provenance.sourceMode} /></div><div className="tg-product__mode-card"><strong>Central local fixtures</strong><p>All seven sections read only from the typed demo adapter. No HTTP or service client is mounted in this experience.</p></div><SourceReadinessPanel demo={demoSource} live={liveSource} /><InfoLine label="Fixture source" value={scenario.provenance.source} /><InfoLine label="Freshness" value="Local static fixture · no refresh" /><InfoLine label="Run / version" value={`${scenario.provenance.runId} · ${scenario.provenance.version}`} /><InfoLine label="Time semantics" value={scenario.provenance.timeBasis} /><InfoLine label="Display clock" value={scenario.provenance.timestampLabel} /><InfoLine label="Units" value={scenario.provenance.units.join(' · ')} /><InfoLine label="Uncertainty" value={scenario.provenance.uncertainty} /></section>
    <div className="tg-product__system-side"><section className="tg-product__system-readiness" aria-labelledby="system-readiness-title"><div className="tg-product__section-minihead"><div><span className="tg-product__eyebrow">NO PROBING OR HEALTH REQUESTS</span><h2 id="system-readiness-title">Service readiness</h2></div></div><StateBadge kind="unavailable" label="Backend service" detail="Not configured or queried by this UI." /><StateBadge kind="unknown" label="Actual service health" detail="Unknown; a demo does not test service health." /><StateBadge kind={gateStatus === 'ready' ? 'value' : gateStatus === 'not_ready' ? 'unavailable' : 'unknown'} label="Build-time G0 snapshot" detail={`G0 ${gateText(gateStatus)} · does not imply services or demo data are live.`} /><p className="tg-product__limit-copy">The gate badge is a packaged snapshot. It does not establish readiness.</p></section>
      <section className="tg-product__system-vocabulary" aria-labelledby="system-vocabulary-title"><div className="tg-product__section-minihead"><div><span className="tg-product__eyebrow">NO COLLAPSING TO ZERO OR DRY</span><h2 id="system-vocabulary-title">Coverage states</h2></div></div><div className="tg-product__state-grid">{(Object.entries(DEMO_STATE_EXAMPLES) as [DemoStateKind, { kind: DemoStateKind; explanation: string; value?: number }][]).map(([kind, example]) => <StateBadge key={kind} kind={kind} label={kind === 'nodata' ? 'NoData' : kind[0].toUpperCase() + kind.slice(1)} detail={example.explanation} value={example.value} />)}</div></section></div>
    <section className="tg-product__system-limits" aria-labelledby="system-limits-title"><div className="tg-product__section-minihead"><div><span className="tg-product__eyebrow">INTERPRETATION BOUNDARY</span><h2 id="system-limits-title">Limitations</h2></div></div><InfoLine label="Physical meaning" value={scenario.provenance.limitation} /><InfoLine label="Historical semantics" value="Demo clock only; no historical timestamp or observation is asserted." /><InfoLine label="Operational use" value="Alerts, routes, shelters, readiness, and emergency guidance are illustrative only." /></section>
  </div>;
}

function Metric({ label, value, unit }: { label: string; value: number; unit: string }) { return <div className="tg-product__metric"><span>{label}</span><strong>{value.toLocaleString('en-US')}</strong><small>{unit} · DEMO</small></div>; }
function InfoLine({ label, value }: { label: string; value: string }) { return <div className="tg-product__info-line"><span>{label}</span><strong>{value}</strong></div>; }
function LegendSwatch({ label, tone }: { label: string; tone: 'water' | 'dry' | 'nodata' }) { return <div className="tg-product__legend-row"><i className={`tg-product__swatch tg-product__swatch--${tone}`} aria-hidden="true" /><span>{label}</span><small>{tone === 'nodata' ? 'unknown · not dry' : 'DEMO'}</small></div>; }
function StateBadge({ kind, label, detail, value }: { kind: DemoStateKind; label: string; detail: string; value?: number }) {
  const icon = kind === 'value' ? '●' : kind === 'zero' ? '0' : kind === 'dry' ? '○' : kind === 'nodata' ? '▧' : kind === 'unavailable' ? '×' : '?';
  const stateText = kind === 'value' ? 'Known demo value' : kind === 'zero' ? 'Known zero' : kind === 'dry' ? 'Explicit dry fixture' : kind === 'nodata' ? 'NoData' : kind === 'unavailable' ? 'Unavailable' : 'Unknown';
  return <div className={`tg-product__state tg-product__state--${kind}`}><span aria-hidden="true">{icon}</span><div><strong>{label} · {stateText}{kind === 'zero' ? ` (${value ?? 0})` : ''}</strong><small>{detail}</small></div></div>;
}
