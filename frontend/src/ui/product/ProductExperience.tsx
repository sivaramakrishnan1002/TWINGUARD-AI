import { useEffect, useMemo, useState } from 'react';
import type { DemoFrame, DemoReservoir, DemoScenario, DemoStateKind, DemoWorkspace, ProductExperienceAdapter, WhatIfInputs } from '../demo/types';
import { advanceDemoFrame, demoAdapter, defaultWhatIfInputs, setDemoShelterAvailability } from '../demo/adapter';
import { DEMO_STATE_EXAMPLES } from '../demo/fixtures';
import './product.css';

const sections = [
  { id: 'overview', label: 'Situation Overview', short: 'Overview', number: '01', icon: '◫' },
  { id: 'twin', label: '3D Flood Twin', short: 'Flood twin', number: '02', icon: '◇' },
  { id: 'reservoirs', label: 'Reservoirs & Alerts', short: 'Reservoirs', number: '03', icon: '▤' },
  { id: 'impacts', label: 'Impacts', short: 'Impacts', number: '04', icon: '⌁' },
  { id: 'response', label: 'Emergency Response', short: 'Response', number: '05', icon: '⇢' },
  { id: 'what-if', label: 'What-if Lab', short: 'What-if', number: '06', icon: '◌' },
  { id: 'system', label: 'Data & System', short: 'Data & System', number: '07', icon: '◎' },
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
      <aside className="tg-product__sidebar" aria-label="TwinGuard demo navigation">
        <a className="tg-product__brand" href="#tg-product-main" onClick={() => navigateTo('overview')} aria-label="TwinGuard demo overview">
          <span className="tg-product__brand-mark" aria-hidden="true"><i /><i /><i /></span>
          <span><strong>TwinGuard</strong><small>FLOOD MANAGEMENT WORKSPACE</small></span>
        </a>
        <div className="tg-product__workspace"><span>WORKSPACE</span><strong>Chennai · Demo environment</strong><small>Local interface simulation</small></div>
        <nav className="tg-product__nav" aria-label="Product sections">
          {sections.map((item) => <button type="button" key={item.id} className={section === item.id ? 'is-active' : ''} aria-current={section === item.id ? 'page' : undefined} onClick={() => navigateTo(item.id)}>
            <span className="tg-product__nav-icon" aria-hidden="true">{item.icon}</span><span className="tg-product__nav-text"><strong>{item.label}</strong><small>{item.number} · {item.short}</small></span>
          </button>)}
        </nav>
        <div className="tg-product__sidebar-note"><span className="tg-product__dot" aria-hidden="true" /><div><strong>DEMO MODE</strong><small>No live data or service calls</small></div></div>
        <div className="tg-product__sidebar-foot">TwinGuard product experience<br />Illustrative only · v1</div>
      </aside>

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

          {section === 'overview' && <OverviewSection scenario={scenario} frame={workspace.adjustedFrame} workspace={workspace} onSection={navigateTo} />}
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
function SectionCard({ title, eyebrow, children, className = '' }: { title: string; eyebrow?: string; children: React.ReactNode; className?: string }) {
  return <section className={`tg-product__card ${className}`}><div className="tg-product__card-heading">{eyebrow && <span className="tg-product__eyebrow">{eyebrow}</span>}<h2>{title}</h2></div>{children}</section>;
}

function OverviewSection({ scenario, frame, workspace, onSection }: { scenario: DemoScenario; frame: DemoFrame; workspace: DemoWorkspace; onSection: (section: ProductSection) => void }) {
  return <div className="tg-product__overview-grid">
    <SectionCard title="Scenario snapshot" eyebrow="CURRENT DEMO RUN" className="tg-product__overview-hero">
      <div className="tg-product__snapshot-meta"><DemoPill mode={scenario.provenance.sourceMode} /><span>{scenario.provenance.runId}</span><span>{scenario.provenance.version}</span></div>
      <p className="tg-product__scenario-description">{scenario.description}</p>
      <Illustration frame={frame} mode="3d" compact />
      <p className="tg-product__caption">{frame.label} · illustrative city geometry · no geographic map</p>
      <button type="button" className="tg-product__button tg-product__button--primary" onClick={() => onSection('twin')}>Open 3D Flood Twin <span aria-hidden="true">→</span></button>
    </SectionCard>
    <SectionCard title="Demo summary" eyebrow="SYNTHETIC SNAPSHOT" className="tg-product__summary-card">
      <Metric label="Population exposure" value={workspace.adjustedImpact.populationExposure} unit="people · demo" />
      <Metric label="Facilities" value={workspace.adjustedImpact.facilities} unit="records · demo" />
      <Metric label="Road segments" value={workspace.adjustedImpact.roadSegments} unit="segments · demo" />
      <div className="tg-product__mini-note">Separate illustrative quantities; no combined score or ranking.</div>
    </SectionCard>
    <SectionCard title="Reservoir overview" eyebrow="SIMULATED VALUES" className="tg-product__reservoir-summary">
      {scenario.reservoirs.slice(0, 2).map((reservoir) => <div className="tg-product__reservoir-line" key={reservoir.id}><span><strong>{reservoir.name}</strong><small>{reservoir.alertLabel}</small></span><strong>{reservoir.storageMcft ?? 'Unknown'}{reservoir.storageMcft === null ? '' : ' mcft'}</strong></div>)}
      <button type="button" className="tg-product__button" onClick={() => onSection('reservoirs')}>View reservoir demo <span aria-hidden="true">→</span></button>
    </SectionCard>
    <SectionCard title="Service readiness" eyebrow="REAL SERVICE STATUS" className="tg-product__readiness-card">
      <StateBadge kind="unavailable" label="Backend services" detail="Not called or checked by this demo UI." />
      <StateBadge kind="unknown" label="Operational readiness" detail="Not established by a local demo." />
      <p className="tg-product__limit-copy">Demo fixtures are not evidence of system health or emergency capability.</p>
    </SectionCard>
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
  const label = mode === '3d' ? 'Illustrative isometric demo city with animated-looking synthetic water shape' : 'Top-down illustrative demo footprint using the same selected synthetic time step';
  return <div className={`tg-product__scene tg-product__scene--${mode}${compact ? ' is-compact' : ''}`} role="img" aria-label={`${label}. Not geographic or measured.`}>
    {mode === '3d' ? <svg viewBox="0 0 420 280" aria-hidden="true" focusable="false">
      <defs><linearGradient id="tg-demo-ground" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#d8e6d8" /><stop offset="1" stopColor="#a9c5b4" /></linearGradient><linearGradient id="tg-demo-water" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#69c5d1" stopOpacity=".84" /><stop offset="1" stopColor="#348da7" stopOpacity=".95" /></linearGradient></defs>
      <path d="M25 78 210 16 394 83 208 151Z" fill="url(#tg-demo-ground)" stroke="#8da99a" strokeWidth="1.5" /><path d="M25 78v116l183 70V151Z" fill="#bdd1c4" stroke="#91a99a" /><path d="M208 151v113l186-72V83Z" fill="#aac2b3" stroke="#91a99a" />
      <path d="M44 84 208 29 376 87M57 98l150-50 150 54M71 115l137-46 136 50M85 131l123-41 120 46" fill="none" stroke="#fff" strokeOpacity=".48" strokeWidth="1" />
      {layers.roads && <path d="M53 102 208 157 355 101M56 133l150 57 147-58M59 165l148 57 144-60" fill="none" stroke="#f6f1df" strokeWidth="5" strokeOpacity=".85" />}
      <path d="M0 0" fill="none" />
      {layers.blocks && <>
      <path d="M42 77 82 64v27L42 106Z" fill="#728f7e" /><path d="M42 77v27l12 7V84Z" fill="#647d70" /><path d="M82 64v27l-28 19V84Z" fill="#526f65" />
      <path d="M99 63 132 52v24L99 87Z" fill="#c29566" /><path d="M99 63v24l11 7V67Z" fill="#a47b57" /><path d="M132 52v24l-22 18V67Z" fill="#826750" />
      <path d="M163 48 195 37v30l-32 12Z" fill="#748a9a" /><path d="M163 48v31l12 7V52Z" fill="#5d7486" /><path d="M195 37v30l-20 19V52Z" fill="#4d6374" />
      <path d="M229 61 270 47v30l-41 15Z" fill="#bd8a61" /><path d="M229 61v31l12 7V65Z" fill="#9d6f4d" /><path d="M270 47v30l-29 22V65Z" fill="#805f49" />
      <path d="M299 89 337 76v28l-38 14Z" fill="#6e8895" /><path d="M299 89v29l13 7V93Z" fill="#5d737e" /><path d="M337 76v28l-25 21V93Z" fill="#495f6b" />
      </>}
      {layers.water && <path d={frame.waterPath3d} fill="url(#tg-demo-water)" stroke="#287f9a" strokeWidth="1.5" />}
      {layers.blocks && <g fill="#547e62"><circle cx="91" cy="136" r="7" /><circle cx="113" cy="146" r="5" /><circle cx="288" cy="155" r="8" /><circle cx="316" cy="144" r="5" /><circle cx="235" cy="117" r="5" /></g>}
      <g fill="#2a5360" fontFamily="sans-serif" fontSize="9"><text x="27" y="258">ILLUSTRATIVE BLOCKS</text><text x="290" y="258">NO MAP COORDINATES</text></g>
    </svg> : <svg viewBox="0 0 420 280" aria-hidden="true" focusable="false">
      <defs><pattern id="tg-demo-nodata" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="8" fill="#eff1ed" /><path d="M0 0V8" stroke="#aeb8b3" strokeWidth="2" /></pattern></defs>
      <rect x="0" y="0" width="420" height="280" fill="#dce4df" /><rect x="12" y="11" width="49" height="16" rx="4" fill="#b8d3af" stroke="#72936f" /><text x="17" y="22" fill="#315834" fontFamily="sans-serif" fontSize="8">DEMO DRY</text>{layers.roads && <path d="M12 36H406M12 75H406M12 114H406M12 153H406M12 192H406M12 231H406M50 10V270M100 10V270M150 10V270M200 10V270M250 10V270M300 10V270M350 10V270" stroke="#fff" strokeWidth="8" />}
      {layers.blocks && <path d="M20 31 87 28 92 68 20 72ZM119 28 174 31 173 68 117 68ZM203 29 265 30 267 71 201 69ZM299 29 389 31 389 72 299 70ZM21 88 85 88 89 143 22 146ZM122 86 180 86 181 141 119 142ZM293 90 389 87 388 141 294 143ZM20 162 84 162 85 220 19 219ZM117 162 178 159 179 221 117 220ZM207 162 269 162 270 222 207 221ZM299 159 390 160 390 219 297 218Z" fill="#c8d8c0" stroke="#a9bba7" />}
      <path d="M342 18 406 18 406 54 373 54 362 42 342 42Z" fill="url(#tg-demo-nodata)" stroke="#899990" strokeDasharray="4 3" />
      {layers.water && <path d={frame.waterPath2d} fill="#58b5c6" fillOpacity=".83" stroke="#267f97" strokeWidth="2" />}
      <g fill="#264d57" fontFamily="sans-serif" fontSize="9"><text x="16" y="266">SYNTHETIC DEMO GRID · NOT A GEOGRAPHIC MAP</text></g>
    </svg>}
    <span className="tg-product__scene-stamp">{mode === '3d' ? '3D ILLUSTRATION' : '2D FALLBACK'} · DEMO</span>
  </div>;
}

function ReservoirsSection({ scenario, selectedId, onSelect, frame }: { scenario: DemoScenario; selectedId: string; onSelect: (id: string) => void; frame: DemoFrame }) {
  const selected = scenario.reservoirs.find((item) => item.id === selectedId) ?? scenario.reservoirs[0];
  return <div className="tg-product__two-column">
    <SectionCard title="Reservoir selector" eyebrow="SYNTHETIC INVENTORY"><label className="tg-product__field"><span>Choose demo reservoir</span><select value={selectedId} onChange={(event) => onSelect(event.target.value)}>{scenario.reservoirs.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><ReservoirDetail reservoir={selected} frame={frame} /></SectionCard>
    <SectionCard title="Demo alert timeline" eyebrow="NOT A LIVE ALERT"><p className="tg-product__card-intro">Synthetic label for the selected fixture. No emergency warning is issued.</p><div className="tg-product__alert-state"><DemoPill mode="SIMULATED" /><strong>{selected.alertLabel}</strong></div><div className="tg-product__timeline-list">{scenario.frames.map((item, index) => <div className={index <= scenario.frames.findIndex((x) => x.id === frame.id) ? 'is-passed' : ''} key={item.id}><i aria-hidden="true" /><span>{item.label}</span><strong>{index === 1 && selected.id !== 'demo-unknown' ? 'DEMO WATCH' : 'SIMULATED'}</strong></div>)}</div><p className="tg-product__limit-copy">Threshold context and history are fictional fixture content. Unknown source values remain unknown.</p></SectionCard>
    <SectionCard title="Reservoir comparison" eyebrow="DEMO SNAPSHOT" className="tg-product__span-two"><div className="tg-product__reservoir-grid">{scenario.reservoirs.map((item) => <ReservoirDetail key={item.id} reservoir={item} frame={frame} compact />)}</div></SectionCard>
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
  return <div className="tg-product__impact-grid">
    <SectionCard title="Hazard footprint" eyebrow="SIMULATED · UNITLESS DISPLAY"><Illustration frame={workspace.adjustedFrame} mode="2d" compact /><div className="tg-product__impact-readout"><strong>Demo visual level {workspace.adjustedVisualLevel} / 4</strong><span>Not an extent, depth, risk score, or geographic area.</span></div></SectionCard>
    <SectionCard title="Population exposure" eyebrow="DEMO COUNT"><Metric label="Synthetic people" value={impact.populationExposure} unit="demo count" /><p className="tg-product__limit-copy">Not a census estimate, observed impact, or validated exposure model.</p></SectionCard>
    <SectionCard title="Facilities" eyebrow="DEMO COUNT"><Metric label="Synthetic records" value={impact.facilities} unit="demo records" /><p className="tg-product__limit-copy">Fixture count only; facility identity and status are not verified.</p></SectionCard>
    <SectionCard title="Road access" eyebrow="SIMULATED NETWORK"><Metric label="Demo segments" value={impact.roadSegments} unit="demo segments" /><StateBadge kind="unknown" label="Hazard assessment" detail="Unknown for every route segment." /><p className="tg-product__limit-copy">Road connectivity and hazard exposure are separate concepts. No road closure or safe access is claimed.</p></SectionCard>
    <div className="tg-product__disclaimer tg-product__span-two"><strong>Separate demo indicators</strong><span>{impact.note} No combined vulnerability score, priority ranking, or operational recommendation is calculated.</span></div>
  </div>;
}

function ResponseSection({ workspace, inputs, onUpdate }: { workspace: DemoWorkspace; inputs: WhatIfInputs; onUpdate: (next: Partial<WhatIfInputs>) => void }) {
  const routes = workspace.adjustedRoutes;
  return <div className="tg-product__two-column">
    <SectionCard title="Route comparison" eyebrow="ILLUSTRATIVE DEMO GRAPH"><p className="tg-product__card-intro">Fictional route alternatives only. Topological reachability does not establish flood access or safety.</p><div className="tg-product__route-illustration" role="img" aria-label="Diagram of synthetic route A and route B connecting a demo origin to a destination; no geographic locations"><span>DEMO ORIGIN</span><i /><i /><i /><span>DEMO DESTINATION</span></div><div className="tg-product__route-table"><table><caption className="tg-product__visually-hidden">Synthetic route comparison; hazard assessment is unknown for every route.</caption><thead><tr><th scope="col">Candidate</th><th scope="col">Demo time</th><th scope="col">Topological connectivity</th><th scope="col">Hazard assessment</th></tr></thead><tbody>{routes.map((route) => <tr key={route.id}><th scope="row">{route.name}<small>{route.mode} · {route.distanceKm} demo km</small></th><td>{route.minutes === 0 ? '0 min · DEMO' : `${route.minutes} min · DEMO`}</td><td>{route.topologicalReachability === 'connected' ? 'Connected (demo)' : 'Disconnected (demo)'}<small>{route.note}</small></td><td>Unknown</td></tr>)}</tbody></table></div><p className="tg-product__limit-copy">Scenario sliders adjust only synthetic travel-time arithmetic. No real graph, flood assessment, location, or safe route is provided.</p></SectionCard>
    <SectionCard title="Shelter candidates" eyebrow="SYNTHETIC INVENTORY"><div className="tg-product__shelter-list">{workspace.scenario.shelters.map((shelter) => <article className={inputs.unavailableShelterId === shelter.id ? 'is-unavailable' : ''} key={shelter.id}><div><strong>{shelter.name}</strong><DemoPill mode="SIMULATED" /></div><p>{inputs.unavailableShelterId === shelter.id ? 'Marked unavailable in this what-if demo.' : `${shelter.demoSlots} demo slots · fictional capacity`}</p><small>{shelter.note}</small><label className="tg-product__check"><input type="checkbox" checked={inputs.unavailableShelterId === shelter.id} onChange={(event) => onUpdate(setDemoShelterAvailability(inputs, shelter.id, event.target.checked))} /><span>Toggle unavailable in demo</span></label></article>)}</div><StateBadge kind="unknown" label="Verified shelters" detail="No verified facility or operating records are part of this demo." /><p className="tg-product__limit-copy">No shelter is represented as open or operational. Candidate locations are fictional labels.</p></SectionCard>
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
    <SectionCard title="Current demo view" eyebrow="SAME SELECTED STEP" className="tg-product__span-two"><div className="tg-product__current-demo"><Illustration frame={workspace.adjustedFrame} mode="2d" compact /><div><DemoPill mode="SIMULATED" /><h3>{workspace.frame.label}</h3><p>Visual-only change from the synthetic input controls. Source, selected frame, and limitations remain visible.</p><InfoLine label="Input provenance" value="Central fixture + local UI arithmetic" /><InfoLine label="Time basis" value={workspace.scenario.provenance.timeBasis} /></div></div></SectionCard>
  </div>;
}

function ComparisonColumn({ title, population, facilities, roads, visual }: { title: string; population: number; facilities: number; roads: number; visual: number }) {
  return <div className="tg-product__comparison-column"><span>{title}</span><InfoLine label="Population demo count" value={String(population)} /><InfoLine label="Facility demo records" value={String(facilities)} /><InfoLine label="Road demo segments" value={String(roads)} /><InfoLine label="Visual level" value={`${visual} / 4 · unitless`} /></div>;
}

function SystemSection({ scenario, gateStatus }: { scenario: DemoScenario; gateStatus: GateStatus }) {
  return <div className="tg-product__system-grid">
    <SectionCard title="Data mode" eyebrow="SOURCE BOUNDARY"><div className="tg-product__mode-card"><DemoPill mode={scenario.provenance.sourceMode} /><strong>Central local fixtures</strong><p>All product sections read only from the typed demo adapter. No HTTP client is present in this product experience.</p></div><InfoLine label="Fixture source" value={scenario.provenance.source} /><InfoLine label="Data freshness" value="Local static fixture · no refresh" /><InfoLine label="Run / version" value={`${scenario.provenance.runId} · ${scenario.provenance.version}`} /><InfoLine label="Time semantics" value={scenario.provenance.timeBasis} /><InfoLine label="Display clock" value={scenario.provenance.timestampLabel} /><InfoLine label="Units" value={scenario.provenance.units.join(' · ')} /></SectionCard>
    <SectionCard title="Service readiness" eyebrow="NO PROBING OR HEALTH REQUESTS"><StateBadge kind="unavailable" label="Backend service" detail="Not configured or queried by this UI." /><StateBadge kind="unknown" label="Actual service health" detail="Unknown; a demo does not test service health." /><StateBadge kind={gateStatus === 'ready' ? 'value' : gateStatus === 'not_ready' ? 'unavailable' : 'unknown'} label="Build-time G0 snapshot" detail={`G0 ${gateText(gateStatus)} · does not imply services or demo data are live.`} /><p className="tg-product__limit-copy">The badge is a packaged snapshot only. This page makes no health request.</p></SectionCard>
    <SectionCard title="State vocabulary" eyebrow="NEVER COLLAPSED TO ZERO" className="tg-product__span-two"><div className="tg-product__state-grid">{(Object.entries(DEMO_STATE_EXAMPLES) as [DemoStateKind, { kind: DemoStateKind; explanation: string; value?: number }][]).map(([kind, example]) => <StateBadge key={kind} kind={kind} label={kind === 'nodata' ? 'NoData' : kind[0].toUpperCase() + kind.slice(1)} detail={example.explanation} value={example.value} />)}</div></SectionCard>
    <SectionCard title="Uncertainty & limitations" eyebrow="READ BEFORE INTERPRETING"><InfoLine label="Uncertainty" value={scenario.provenance.uncertainty} /><InfoLine label="No historical date" value="Demo clock is synthetic; not a historical timestamp." /><InfoLine label="Physical meaning" value={scenario.provenance.limitation} /><InfoLine label="Operations" value="No alerts, routes, shelters, readiness, or emergency guidance are real." /></SectionCard>
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
