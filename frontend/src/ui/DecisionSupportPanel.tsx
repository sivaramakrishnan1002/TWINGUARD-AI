import { unavailableDecisionSupportAdapter } from './adapters/decisionSupport';

const impactMetrics = [
  { title: 'Population exposure', unit: 'people', detail: 'No run result' },
  { title: 'Affected facilities', unit: 'facilities', detail: 'No run result' },
  { title: 'Affected roads', unit: 'measure unavailable', detail: 'No road-impact mapping' },
];

const scenarios = [
  { key: 'closed-bridge', label: 'Bridge closure' },
  { key: 'earlier-evacuation', label: 'Earlier evacuation' },
  { key: 'shelter-unavailable', label: 'Shelter unavailable' },
] as const;

export function DecisionSupportPanel() {
  const unavailableReason = unavailableDecisionSupportAdapter.availability.status === 'unavailable'
    ? unavailableDecisionSupportAdapter.availability.reason
    : 'Decision-support source unavailable.';

  return (
    <section className="decision-support-panel" aria-labelledby="decision-support-title">
      <div className="decision-panel-heading">
        <div><span className="eyebrow">IMPACTS · ROUTES · SHELTERS</span><h2 id="decision-support-title">Decision support</h2></div>
        <span className="status-badge status-badge--unavailable">NO VALIDATED RESULTS</span>
      </div>

      <div className="decision-context-strip" aria-label="Decision result context">
        <span><strong>SOURCE</strong> None connected</span>
        <span><strong>TIME</strong> Unavailable</span>
        <span><strong>RUN / VERSION</strong> Unavailable</span>
        <span><strong>ASSUMPTIONS</strong> Not evaluated</span>
        <span><strong>UNCERTAINTY</strong> Unavailable</span>
      </div>

      <div className="decision-grid">
        <section className="decision-card impact-card" aria-labelledby="impact-title">
          <div className="decision-subheading"><div><span className="eyebrow">EXPOSURE SUMMARY</span><h3 id="impact-title">Potential impacts</h3></div><span className="source-chip">UNAVAILABLE</span></div>
          <div className="impact-metric-grid">
            {impactMetrics.map((metric) => (
              <div className="impact-metric" key={metric.title}>
                <span>{metric.title}</span>
                <strong>Unknown</strong>
                <small>{metric.unit} · {metric.detail}</small>
              </div>
            ))}
          </div>
          <div className="decision-empty-note" role="status">
            <strong>Impact results are not connected</strong>
            <p>{unavailableReason} Missing coverage remains unknown, not zero. No exposure counts or road impacts are inferred.</p>
          </div>
          <div className="decision-provenance"><strong>PROVENANCE &amp; LIMITS</strong><span>No source, valid time, run, thresholds, or uncertainty metadata. The impact contract requires depth and exposure provenance; no result is available.</span></div>
        </section>

        <section className="decision-card route-card" aria-labelledby="route-title">
          <div className="decision-subheading"><div><span className="eyebrow">ROUTE REQUEST</span><h3 id="route-title">Accessibility query</h3></div><span className="source-chip">REQUEST DISABLED</span></div>
          <div className="route-form" aria-describedby="route-unavailable-reason">
            <label className="decision-field">Origin<input type="text" disabled placeholder="Unavailable · no validated location source" /></label>
            <label className="decision-field">Destination<input type="text" disabled placeholder="Unavailable · no validated location source" /></label>
            <label className="decision-field">Departure time<input type="datetime-local" disabled aria-label="Departure time unavailable" /></label>
            <label className="decision-field">Travel mode<select disabled defaultValue=""><option value="">Choose mode · unavailable</option><option value="vehicle">Vehicle</option><option value="walking">Walking</option></select></label>
            <button type="button" className="decision-action" disabled>Request route · unavailable</button>
          </div>
          <div id="route-unavailable-reason" className="route-result-empty" role="status">
            <strong>No route result</strong>
            <p>Route geometry, travel time, accessibility probability, graph version, and uncertainty are unavailable. No line is drawn; no route is described as safe.</p>
          </div>
        </section>

        <section className="decision-card shelter-card" aria-labelledby="shelter-title">
          <div className="decision-subheading"><div><span className="eyebrow">SHELTER STATUS</span><h3 id="shelter-title">Shelters</h3></div><span className="source-chip">NO RECORDS</span></div>
          <div className="shelter-status-key" aria-label="Shelter status definitions">
            <span className="status-label status-label--placeholder">CANDIDATE</span><span>Requires verification</span>
            <span className="status-label status-label--unavailable">VERIFIED</span><span>No verified records connected</span>
          </div>
          <div className="shelter-empty" role="status">
            <strong>No shelter records available</strong>
            <p>Candidate and verified shelter lists are empty. Locations, operational status, capacity, and accessibility remain unknown.</p>
          </div>
          <div className="shelter-map-empty" role="img" aria-label="Shelter map unavailable; no verified shelter locations connected">
            <span aria-hidden="true">⌖</span><strong>Shelter map unavailable</strong><small>No locations or markers loaded</small>
          </div>
          <p className="decision-footnote">Capacity: unknown · No shelters are assumed open or operational.</p>
        </section>

        <section className="decision-card priority-card" aria-labelledby="priority-title">
          <div className="decision-subheading"><div><span className="eyebrow">EMERGENCY PLANNING</span><h3 id="priority-title">Priority zones</h3></div><span className="source-chip">UNAVAILABLE</span></div>
          <div className="priority-empty" role="status">
            <span className="priority-empty-symbol" aria-hidden="true">?</span>
            <strong>No priority zones connected</strong>
            <p>Zone geometry, ranking, valid time, and source run are unavailable. No area is highlighted or assigned a priority.</p>
          </div>
          <div className="decision-provenance"><strong>ZONE PROVENANCE</strong><span>Requires validated impact and shelter outputs with documented thresholds and uncertainty.</span></div>
        </section>

        <section className="decision-card counterfactual-card" aria-labelledby="counterfactual-title">
          <div className="decision-subheading"><div><span className="eyebrow">WHAT-IF ANALYSIS</span><h3 id="counterfactual-title">Counterfactual scenarios</h3></div><span className="source-chip">EVALUATION DISABLED</span></div>
          <p className="counterfactual-intro">Scenario labels only. No scenario can be submitted without a validated base run and evaluation service.</p>
          <div className="scenario-list">
            {scenarios.map((scenario) => (
              <label className="scenario-option" key={scenario.key}>
                <input type="checkbox" disabled aria-label={`${scenario.label} scenario unavailable`} />
                <span className="scenario-control" aria-hidden="true" />
                <span>{scenario.label}</span>
                <small>Unavailable</small>
              </label>
            ))}
          </div>
          <div className="scenario-result-empty" role="status">
            <strong>No counterfactual result</strong>
            <p>No outcome, travel-time change, avoided exposure, or priority shift is estimated.</p>
          </div>
        </section>
      </div>

      <div className="decision-source-key" aria-label="Evidence status definitions">
        <strong>EVIDENCE LABELS</strong>
        <span><b className="status-label status-label--replay">REPLAY</b> Historical input</span>
        <span><b className="status-label status-label--live">LIVE</b> Connected current source</span>
        <span><b className="status-label status-label--simulated">SIMULATED</b> Synthetic input</span>
        <span><b className="status-label status-label--derived">DERIVED</b> Computed result</span>
        <span><b className="status-label status-label--assumption">ASSUMPTION</b> Unverified input</span>
        <span><b className="status-label status-label--placeholder">PLACEHOLDER</b> UI state only</span>
        <small>None of these evidence modes is connected to the panels above.</small>
      </div>
    </section>
  );
}
