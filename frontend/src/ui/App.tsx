import { useState, type ReactNode } from 'react';
import { MapView } from './MapView';
import { ReservoirAlertsPanel } from './ReservoirAlertsPanel';
import { DecisionSupportPanel } from './DecisionSupportPanel';
import type { DocumentedEventWindow } from './types';
import { StatusBadge } from './components/StatusBadge';
import researchFigure from './assets/phase12_parameter_sensitivity_batch2.png';

const eventWindows: DocumentedEventWindow[] = [
  {
    id: 'chennai-2015-planned', label: 'Chennai 2015 · aligned-input window', shortLabel: 'Chennai 2015 · planned window',
    startDate: '01 Nov 2015', endDate: '15 Dec 2015', timeBasis: 'Inclusive local dates · Asia/Kolkata', status: 'PLANNED',
    source: 'docs/TWIN_MODEL.md · docs/TIME_ALIGNMENT.md',
    limitations: ['Planned historical-input period; not a verified flood-onset date.', 'No time-indexed UI feed or map layer is connected.'],
  },
  {
    id: 'chennai-2021-planned', label: 'Chennai 2021 · aligned-input window', shortLabel: 'Chennai 2021 · planned window',
    startDate: '01 Nov 2021', endDate: '20 Nov 2021', timeBasis: 'Inclusive local dates · Asia/Kolkata', status: 'PLANNED',
    source: 'docs/TWIN_MODEL.md · docs/TIME_ALIGNMENT.md',
    limitations: ['Planned historical-input period; not a verified flood-onset date.', 'No reservoir series or UI feed is connected for this window.'],
  },
  {
    id: 'chennai-2023-planned', label: 'Chennai 2023 · aligned-input window', shortLabel: 'Chennai 2023 · planned window',
    startDate: '25 Nov 2023', endDate: '15 Dec 2023', timeBasis: 'Inclusive local dates · Asia/Kolkata', status: 'PLANNED',
    source: 'docs/TWIN_MODEL.md · docs/TIME_ALIGNMENT.md',
    limitations: ['Planned historical-input period; not a verified flood-onset date.', 'No reservoir series or UI feed is connected for this window.'],
  },
  {
    id: 'trackb-2015-replay', label: 'Chennai 2015 · Track B alert-candidate replay', shortLabel: 'Track B 2015 · alert-candidate replay',
    startDate: '20 Nov 2015', endDate: '04 Dec 2015', timeBasis: 'Runbook date filters · message times carry source timezone', status: 'HISTORICAL_REPLAY',
    source: 'docs/trackb/RUNBOOK.md · docs/trackb/replay_2015_alerts.jsonl',
    limitations: ['Offline replay contains alert candidates, not validated flood outcomes.', 'Replay messages are not available through a UI endpoint.'],
  },
];

const navigation = [
  { id: 'overview', label: 'Situation overview', marker: '01', state: 'Available shell' },
  { id: 'map', label: 'Map & layers', marker: '02', state: 'Map source unavailable' },
  { id: 'reservoirs', label: 'Reservoirs & alerts', marker: '03', state: 'Track B unavailable' },
  { id: 'decisions', label: 'Impacts & decisions', marker: '04', state: 'Services unavailable' },
  { id: 'evidence', label: 'Research evidence', marker: '05', state: 'Static outputs' },
] as const;

type PageId = typeof navigation[number]['id'];

const unavailableFeeds = [
  ['Flood & terrain layers', 'No verified tile service'],
  ['Reservoir observations', 'Track B API not mounted'],
  ['Impact & routing', 'Service outputs unavailable'],
  ['Shelters & scenarios', 'No connected results'],
];

function App() {
  const [page, setPage] = useState<PageId>('overview');
  const [selectedWindowId, setSelectedWindowId] = useState('');
  const selectedWindow = eventWindows.find((window) => window.id === selectedWindowId);
  const pageInfo = navigation.find((item) => item.id === page) ?? navigation[0];

  return (
    <div className="application-frame">
      <a className="skip-link" href="#content-main">Skip to main content</a>
      <aside className="app-sidebar" aria-label="Application navigation">
        <a className="brand" href="#content-main" aria-label="TwinGuard situation overview">
          <span className="brand-mark" aria-hidden="true"><span /><span /></span>
          <span className="brand-copy"><strong>TwinGuard</strong><small>FLOOD INTELLIGENCE</small></span>
        </a>

        <div className="workspace-switcher">
          <span className="overline">WORKSPACE</span>
          <strong>Chennai metropolitan area</strong>
          <span>Research environment</span>
        </div>

        <nav className="primary-nav" aria-label="Main sections">
          <span className="overline nav-caption">WORKSPACE</span>
          {navigation.map((item) => (
            <button
              type="button"
              id={item.id === 'map' ? 'map-nav-button' : undefined}
              className={`nav-item${page === item.id ? ' is-active' : ''}`}
              key={item.id}
              aria-current={page === item.id ? 'page' : undefined}
              onClick={() => setPage(item.id)}
            >
              <span className="nav-marker" aria-hidden="true">{item.marker}</span>
              <span className="nav-copy"><strong>{item.label}</strong><small>{item.state}</small></span>
            </button>
          ))}
        </nav>

        <div className="sidebar-status">
          <span className="overline">SYSTEM MODE</span>
          <StatusBadge tone="warning" label="UNCONNECTED" />
          <p>No source is authorized for live display. G0 remains not ready.</p>
        </div>

        <div className="sidebar-footer"><span className="sidebar-version">UI FOUNDATION · 0.5</span><span>Evidence before action</span></div>
      </aside>

      <div className="application-main">
        <header className="topbar">
          <div className="breadcrumb"><span>TWINGUARD</span><i aria-hidden="true">/</i><strong>{pageInfo.label}</strong></div>
          <div className="topbar-right">
            <label className="event-context-control" htmlFor="event-window">
              <span>EVENT WINDOW</span>
              <select id="event-window" value={selectedWindowId} onChange={(event) => setSelectedWindowId(event.target.value)}>
                <option value="">No window selected</option>
                {eventWindows.map((window) => (
                  <option key={window.id} value={window.id}>
                    {window.status === 'PLANNED' ? 'PLANNED · ' : 'REPLAY · '}{window.label} ({window.startDate}–{window.endDate})
                  </option>
                ))}
              </select>
            </label>
            <div className="mode-indicator" aria-label="No live, replay, or simulated source is connected">
              <span className="mode-indicator-mark" aria-hidden="true">—</span>
              <span><strong>NO CONNECTED SOURCE</strong><small>G0 NOT READY</small></span>
            </div>
          </div>
        </header>

        <main id="content-main" className="content-area" tabIndex={-1}>
          {page === 'overview' && <OverviewPage selectedWindow={selectedWindow} onOpenEvidence={() => setPage('evidence')} onOpenMap={() => setPage('map')} />}
          {page === 'map' && <MapExplorerPage selectedWindow={selectedWindow} />}
          {page === 'reservoirs' && <ReservoirAlertsPanel selectedWindow={selectedWindow} />}
          {page === 'decisions' && <DecisionSupportPanel />}
          {page === 'evidence' && <EvidencePage />}
          <footer className="global-footer"><span>TWIN GUARD · CHENNAI</span><span>No live data connected · research interface only</span><span>G0 <b>NOT READY</b></span></footer>
        </main>
      </div>
    </div>
  );
}

function PageHeading({ kicker, title, description, trailing }: { kicker: string; title: string; description: string; trailing?: ReactNode }) {
  return (
    <div className="page-heading">
      <div><span className="overline">{kicker}</span><h1>{title}</h1><p>{description}</p></div>
      {trailing}
    </div>
  );
}

function OverviewPage({ selectedWindow, onOpenEvidence, onOpenMap }: { selectedWindow?: DocumentedEventWindow; onOpenEvidence: () => void; onOpenMap: () => void }) {
  return (
    <>
      <PageHeading
        kicker="SITUATION OVERVIEW"
        title="Chennai flood workspace"
        description="A research view of available evidence, source readiness, and spatial context."
        trailing={<StatusBadge tone="warning" label="NO LIVE FEED" />}
      />

      <section className="system-notice" aria-label="System data status">
        <span className="system-notice-symbol" aria-hidden="true">i</span>
        <div><strong>Operational data is unavailable</strong><p>This workspace has no connected live feed, time-indexed flood layer, or operational decision service. Nothing on this screen is a current flood warning.</p></div>
        <StatusBadge tone="neutral" label="RESEARCH ONLY" />
      </section>

      <div className="context-ribbon" aria-label="Selected time and run context">
        <div><span>SELECTED WINDOW</span><strong>{selectedWindow?.shortLabel ?? 'None selected'}</strong>{selectedWindow && <small>{selectedWindow.status === 'PLANNED' ? 'Planned input period' : 'Historical replay candidate window'}</small>}</div>
        <div><span>VALID TIME</span><strong>Unavailable</strong><small>No time-indexed data</small></div>
        <div><span>RUN / VERSION</span><strong>No run connected</strong><small>Provenance unavailable</small></div>
        <div><span>MAP SOURCES</span><strong>0 connected</strong><small>Neutral empty style</small></div>
      </div>

      <div className="overview-grid">
        <section className="overview-map-region" aria-labelledby="overview-map-heading">
          <div className="section-heading compact-heading"><div><span className="overline">SPATIAL CONTEXT</span><h2 id="overview-map-heading">Map workspace</h2></div><button type="button" className="text-action" onClick={onOpenMap}>Open map explorer <span aria-hidden="true">↗</span></button></div>
          <MapView compact />
          <div className="map-context-note"><span className="note-mark" aria-hidden="true">i</span><p>The map has no verified basemap, boundary, terrain, or flood layer. NoData remains unknown, not dry.</p></div>
        </section>

        <aside className="overview-rail" aria-label="Service and evidence status">
          <section className="rail-section">
            <div className="section-heading compact-heading"><div><span className="overline">SOURCE HEALTH</span><h2>Not connected</h2></div><span className="connection-indicator" aria-hidden="true">—</span></div>
            <ul className="feed-status-list">
              {unavailableFeeds.map(([name, detail]) => <li key={name}><span className="feed-status-icon" aria-hidden="true">—</span><span><strong>{name}</strong><small>{detail}</small></span><StatusBadge tone="neutral" label="OFFLINE" /></li>)}
            </ul>
          </section>

          <section className="rail-section research-teaser">
            <div className="section-heading compact-heading"><div><span className="overline">STATIC RESEARCH</span><h2>Evidence library</h2></div></div>
            <p>One saved sensitivity figure is available for review. It is not a live layer or an operational result.</p>
            <button type="button" className="secondary-action" onClick={onOpenEvidence}>Review research evidence <span aria-hidden="true">→</span></button>
          </section>

          <section className="rail-limitations">
            <span className="overline">EVIDENCE LIMIT</span>
            <p>Research products may be derived, assumption-based, coarse, or unvalidated outside their documented study. They do not provide emergency guidance.</p>
          </section>
        </aside>
      </div>
    </>
  );
}

const unavailableLayers = [
  ['Flood extent', 'No verified event layer'],
  ['Flood depth', 'No UI raster source'],
  ['Risk classification', 'Research only · not operational'],
  ['Uncertainty / coverage', 'Coverage mask unavailable'],
  ['Terrain elevation', 'No terrain tiles'],
  ['Roads & waterways', 'No HTTP tile service'],
];

function MapExplorerPage({ selectedWindow }: { selectedWindow?: DocumentedEventWindow }) {
  return (
    <>
      <PageHeading kicker="MAP & LAYERS" title="Spatial explorer" description="Map navigation is available; project layers and geographic tiles are not connected." trailing={<StatusBadge tone="neutral" label="EMPTY MAP STYLE" />} />
      <div className="map-explorer-grid">
        <aside className="map-layer-panel" aria-label="Map layer controls">
          <div className="section-heading compact-heading"><div><span className="overline">LAYER CATALOGUE</span><h2>Map layers</h2></div><span className="count-label">0 ACTIVE</span></div>
          <ul className="map-layer-list">{unavailableLayers.map(([name, reason]) => <li key={name}><span className="layer-state-icon" aria-hidden="true">□</span><span><strong>{name}</strong><small>{reason}</small></span><StatusBadge tone="neutral" label="UNAVAILABLE" /></li>)}</ul>
          <div className="legend-panel"><span className="overline">LEGEND &amp; COVERAGE</span><div className="legend-row"><i className="legend-swatch legend-swatch--nodata" /><strong>NoData</strong><span>Transparent · unknown, not dry</span></div><div className="legend-row"><i className="legend-swatch legend-swatch--empty" /><strong>Flood result</strong><span>No layer loaded</span></div><p>Missing coverage is never interpreted as zero or dry.</p></div>
        </aside>
        <div className="map-explorer-main">
          <MapView />
          <div className="map-time-context"><span className="overline">TIME CONTEXT</span><strong>{selectedWindow ? `${selectedWindow.shortLabel} · ${selectedWindow.startDate} — ${selectedWindow.endDate}` : 'No documented window selected'}</strong><span>No replay cursor · no data playback</span></div>
        </div>
        <aside className="map-provenance-panel" aria-label="Map source and provenance">
          <span className="overline">MAP PROVENANCE</span><h2>Awaiting a verified source</h2>
          <dl><div><dt>Basemap</dt><dd>Unavailable</dd></div><div><dt>Boundary</dt><dd>Provisional extent · not drawn</dd></div><div><dt>Terrain</dt><dd>No compatible tiles</dd></div><div><dt>Source / version</dt><dd>None connected</dd></div><div><dt>Attribution</dt><dd>Not available</dd></div></dl>
          <div className="map-source-note"><strong>Not a geographic result</strong><p>The blank canvas is a neutral MapLibre shell. It does not depict flood extent, dry land, or the study boundary.</p></div>
        </aside>
      </div>
    </>
  );
}

function EvidencePage() {
  return (
    <>
      <PageHeading kicker="REPORTS & PROVENANCE" title="Research evidence" description="Saved Lane A research outputs are shown as static evidence with their source and limitations." trailing={<StatusBadge tone="derived" label="STATIC OUTPUTS ONLY" />} />
      <section className="evidence-intro"><span className="evidence-intro-mark" aria-hidden="true">i</span><p>These figures are local snapshots of documented research. They do not refresh, respond to selected event windows, or represent connected map layers.</p></section>
      <article className="research-figure-card">
        <div className="research-figure-header"><div><span className="overline">A12 · DIAGNOSTIC FIGURE</span><h2>Simulation member sensitivity &amp; model explanation</h2></div><div className="evidence-label-pair"><StatusBadge tone="derived" label="DERIVED" /><StatusBadge tone="assumption" label="ASSUMPTION-BASED" /></div></div>
        <figure>
          <img src={researchFigure} alt="Static two-panel research chart. Left: simulated member peak area at or above 0.10 metres for 12 and 24 November 2015. Right: held-out grouped permutation effects for a single Phase 9C model fold." />
          <figcaption><span>STATIC FIGURE · NOT A MAP LAYER</span><span>Saved 27 Oct 2026 · source report: docs/EXPLAINABILITY_BATCH2.md</span></figcaption>
        </figure>
        <div className="research-metadata">
          <div><span>INPUT / PERIOD</span><strong>A06 simulation sensitivity · 12 &amp; 24 Nov 2015</strong></div>
          <div><span>MODEL SCOPE</span><strong>One Phase 9C outer fold · November 2015 radar-visible label</strong></div>
          <div><span>PROVENANCE</span><strong>docs/EXPLAINABILITY_BATCH2.md · docs/PHASE12_SIMULATION.md</strong></div>
        </div>
        <div className="research-limit"><strong>Limitations</strong><p>The A06 run is a coarse, assumption-based simulation; member spread is parameter sensitivity, not calibrated uncertainty. The Phase 9C explanation describes one model fold and is not independent-event validation. Neither panel is observed flood truth, a live forecast, or emergency guidance.</p></div>
      </article>
      <section className="evidence-availability">
        <div><span className="overline">CONNECTED SOURCES</span><h2>None</h2><p>No live service, flood tile, reservoir feed, route result, shelter inventory, or time-indexed playback is connected.</p></div>
        <div><span className="overline">MISSING COVERAGE</span><h2>Unknown</h2><p>NoData remains distinct from zero. Areas without coverage are not classified as dry.</p></div>
      </section>
    </>
  );
}

export default App;
