import { useState } from 'react';
import type { DocumentedEventWindow } from './types';
import { unavailableTrackBAdapter } from './adapters/trackB';

const reservoirs = [
  { key: 'POONDI', label: 'Poondi' },
  { key: 'CHOLAVARAM', label: 'Cholavaram' },
  { key: 'REDHILLS', label: 'Red Hills / Puzhal' },
  { key: 'CHEMBARAMBAKKAM', label: 'Chembarambakkam' },
];

const alertLevels = [
  { label: 'Normal', className: 'normal' },
  { label: 'Watch', className: 'watch' },
  { label: 'Warning', className: 'warning' },
  { label: 'Critical', className: 'critical' },
];

interface ReservoirAlertsPanelProps {
  selectedWindow?: DocumentedEventWindow;
}

export function ReservoirAlertsPanel({ selectedWindow }: ReservoirAlertsPanelProps) {
  const [selectedReservoirKey, setSelectedReservoirKey] = useState(reservoirs[0].key);
  const selectedReservoir = reservoirs.find((reservoir) => reservoir.key === selectedReservoirKey) ?? reservoirs[0];
  const unavailableReason = unavailableTrackBAdapter.availability.status === 'unavailable'
    ? unavailableTrackBAdapter.availability.reason
    : 'Track B source status unavailable.';

  return (
    <section className="reservoir-alerts-panel" aria-labelledby="reservoir-alerts-title">
      <div className="reservoir-alerts-heading">
        <div>
          <span className="eyebrow">TRACK B · RESERVOIRS</span>
          <h2 id="reservoir-alerts-title">Reservoirs &amp; alerts</h2>
        </div>
        <span className="status-badge status-badge--unavailable">API UNAVAILABLE · NO DATA</span>
      </div>

      <div className="reservoir-alerts-grid">
        <section className="reservoir-card" aria-labelledby="reservoir-card-title">
          <div className="subpanel-heading">
            <div><span className="eyebrow">RESERVOIR STATUS</span><h3 id="reservoir-card-title">Storage overview</h3></div>
            <span className="source-chip">SOURCE NONE</span>
          </div>

          <label className="field-label reservoir-select-label" htmlFor="reservoir-select">SELECT RESERVOIR</label>
          <select id="reservoir-select" className="event-select" value={selectedReservoirKey} onChange={(event) => setSelectedReservoirKey(event.target.value)}>
            {reservoirs.map((reservoir) => <option key={reservoir.key} value={reservoir.key}>{reservoir.label}</option>)}
          </select>
          <p className="helper-text selected-reservoir-note">{selectedReservoir.label} · no current record returned</p>

          <div className="reservoir-gauge-block">
            <div className="gauge-heading"><span>STORAGE</span><strong>mcft · unit documented</strong></div>
            <div className="storage-gauge-empty" role="img" aria-label="Storage gauge unavailable; storage amount is unknown in mcft">
              <span className="gauge-empty-mark" aria-hidden="true">?</span>
              <strong>Storage unknown</strong>
              <span>No reading received</span>
            </div>
            <p className="gauge-caption">No numeric value or percentage is shown while the source is unavailable.</p>
          </div>

          <div className="reservoir-meta-grid">
            <div className="reservoir-meta"><span>OBSERVATION TIME</span><strong>Unknown · no API response</strong></div>
            <div className="reservoir-meta"><span>CAPACITY</span><strong>Unknown · not zero</strong></div>
            <div className="reservoir-meta"><span>RELEASE</span><strong>Unknown · cusecs unit documented</strong></div>
            <div className="reservoir-meta"><span>RUN / SOURCE MODE</span><strong>Unavailable · no run connected</strong></div>
          </div>

          <div className="reservoir-provenance">
            <strong>Source and capacity provenance</strong>
            <p>Selected: {selectedReservoir.label}. Track B documents daily source coverage for these four reservoirs from 01 Jan 2004 through 03 Dec 2020, in mcft. This is archive coverage, not the selected reservoir’s latest observation.</p>
            <p>Capacity denominators used in historical analysis are current-published assumptions; historical capacity is not verified. No capacity value is available to this UI.</p>
          </div>
        </section>

        <section className="alerts-card" aria-labelledby="alerts-card-title">
          <div className="subpanel-heading">
            <div><span className="eyebrow">ALERT STATUS</span><h3 id="alerts-card-title">Alert levels &amp; history</h3></div>
            <span className="source-chip">NO FEED</span>
          </div>

          <div className="empty-alert-state" role="status">
            <span className="empty-ring" aria-hidden="true">—</span>
            <strong>No alert state available</strong>
            <p>{unavailableReason} No level or alert history is inferred.</p>
          </div>

          <div className="alert-level-legend">
            <div className="section-title-row"><h4>Track B level labels</h4><span className="count-label">DEFINITIONS ONLY</span></div>
            <p>These are schema labels, not current alert states.</p>
            <div className="alert-level-list">
              {alertLevels.map((level) => (
                <div className={`alert-level-row alert-level-row--${level.className}`} key={level.label}>
                  <span className="alert-level-indicator" aria-hidden="true" />
                  <strong>{level.label}</strong>
                  <span>State unknown</span>
                </div>
              ))}
            </div>
          </div>

          <div className="alert-timeline">
            <div className="section-title-row"><h4>Alert timeline</h4><span className="count-label">NO HISTORY LOADED</span></div>
            <div className="alert-timeline-window">{selectedWindow ? `${selectedWindow.shortLabel} · ${selectedWindow.startDate} — ${selectedWindow.endDate}` : 'Select a documented window in Event Explorer'}</div>
            <div className="alert-timeline-track" role="img" aria-label="Alert timeline unavailable; no alert records are connected" />
            <p>No timeline marks are shown without returned alert records. Replay candidates are not live alerts or validated flood outcomes.</p>
          </div>
        </section>
      </div>

      <div className="trackb-source-key" aria-label="Track B source mode definitions">
        <span className="source-key-title">SOURCE MODE DEFINITIONS · NONE CURRENTLY CONNECTED</span>
        <span><b className="status-label status-label--replay">REPLAY</b> historical messages</span>
        <span><b className="status-label status-label--live">LIVE</b> current connected source</span>
        <span><b className="status-label status-label--simulated">SIMULATED</b> synthetic data</span>
      </div>
    </section>
  );
}
