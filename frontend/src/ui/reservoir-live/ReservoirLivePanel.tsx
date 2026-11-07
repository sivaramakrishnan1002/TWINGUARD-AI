import { useRef, useState } from 'react';
import { CFM_DASHBOARD_URL, fetchReservoirHistory, type ReservoirPeriod, type ReservoirSeries, type ReservoirSnapshot } from './reservoirClient';

export type ReservoirPanelState =
  | { status: 'idle'; snapshot: null; message: string }
  | { status: 'loading'; snapshot: ReservoirSnapshot | null; message: string }
  | { status: 'available'; snapshot: ReservoirSnapshot; message: null }
  | { status: 'unavailable'; snapshot: null; message: string }
  | { status: 'refresh-failed'; snapshot: ReservoirSnapshot; message: string };

export function reservoirRequestFailed(previous: ReservoirSnapshot | null, reason: string): ReservoirPanelState {
  if (!previous) return { status: 'unavailable', snapshot: null, message: `Reservoir snapshot unavailable: ${reason}` };
  return { status: 'refresh-failed', snapshot: previous, message: `Refresh failed: ${reason} The previous snapshot is kept and is not presented as current.` };
}

const STATUS_LABEL: Record<ReservoirPanelState['status'], string> = {
  idle: 'NOT YET FETCHED',
  loading: 'FETCHING',
  available: 'LIVE · SNAPSHOT RECEIVED',
  unavailable: 'UNAVAILABLE',
  'refresh-failed': 'REFRESH FAILED',
};

/** B45: user-triggered CFM-DSS reservoir snapshot; never polls and never substitutes demo values. */
export function ReservoirLivePanel({ initialState }: { initialState?: ReservoirPanelState } = {}) {
  const [state, setState] = useState<ReservoirPanelState>(initialState ?? { status: 'idle', snapshot: null, message: 'Select “Fetch latest snapshot” to read the public CFM-DSS dashboard.' });
  const [period, setPeriod] = useState<ReservoirPeriod>(initialState?.snapshot?.period ?? 'daily');
  const busy = useRef(false);

  const refresh = async (nextPeriod: ReservoirPeriod = period) => {
    if (busy.current) return;
    busy.current = true;
    setPeriod(nextPeriod);
    const previous = state.snapshot && state.snapshot.period === nextPeriod ? state.snapshot : null;
    setState({ status: 'loading', snapshot: previous, message: 'Fetching the latest published dashboard snapshot…' });
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20_000);
    try {
      const snapshot = await fetchReservoirHistory(nextPeriod, fetch, controller.signal);
      setState({ status: 'available', snapshot, message: null });
    } catch (error) {
      const reason = controller.signal.aborted ? 'request timed out.' : error instanceof Error ? error.message : 'request failed.';
      setState(reservoirRequestFailed(previous, reason));
    } finally {
      window.clearTimeout(timeout);
      busy.current = false;
    }
  };

  const snapshot = state.snapshot;
  return <section className="tg-reservoir-live" aria-labelledby="tg-reservoir-live-title" data-reservoir-status={state.status}>
    <header className="tg-reservoir-live__header">
      <div><span className="tg-product__eyebrow">PUBLIC CFM-DSS DASHBOARD · LIVE FETCH</span><h2 id="tg-reservoir-live-title">Latest published dashboard snapshot</h2></div>
      <span className={`tg-reservoir-live__status tg-reservoir-live__status--${state.status}`} role="status">{STATUS_LABEL[state.status]}</span>
    </header>
    <p className="tg-reservoir-live__note">Source mode <strong>LIVE</strong> means fetched from the public dashboard on request. Freshness is <strong>unknown</strong>: publication cadence and measurement time are not published. Values are dashboard daily averages, not real-time telemetry, and include no inflow, outflow or release.</p>
    <div className="tg-reservoir-live__controls">
      <div className="tg-product__segmented" role="group" aria-label="Reservoir history period">
        <button type="button" aria-pressed={period === 'daily'} onClick={() => void refresh('daily')} disabled={state.status === 'loading'}>Daily · 15 days</button>
        <button type="button" aria-pressed={period === 'monthly'} onClick={() => void refresh('monthly')} disabled={state.status === 'loading'}>Monthly · 13 months</button>
      </div>
      <button type="button" className="tg-product__button tg-product__button--primary" onClick={() => void refresh()} disabled={state.status === 'loading'} aria-label="Fetch latest CFM-DSS reservoir snapshot">{state.status === 'loading' ? 'Fetching…' : snapshot ? 'Refresh snapshot' : 'Fetch latest snapshot'}</button>
    </div>
    {state.message && <p className="tg-reservoir-live__message" role={state.status === 'unavailable' ? 'alert' : 'status'}>{state.message}</p>}
    {snapshot && <>
      <div className="tg-reservoir-live__grid">
        {snapshot.series.map((series) => <ReservoirLiveCard key={series.reservoirId} series={series} period={snapshot.period} />)}
      </div>
      <dl className="tg-reservoir-live__provenance">
        <div><dt>Fetched (service receipt)</dt><dd>{snapshot.receivedAt}</dd></div>
        <div><dt>Observation instant</dt><dd>Unknown · date-only source</dd></div>
        <div><dt>Observation timezone</dt><dd>Unknown</dd></div>
        <div><dt>Response SHA-256</dt><dd><code>{snapshot.series[0]?.latest.responseSha256.slice(0, 16)}…</code></dd></div>
      </dl>
    </>}
    <footer className="tg-reservoir-live__footer">
      <a href={CFM_DASHBOARD_URL} target="_blank" rel="noreferrer">Source: Tamil Nadu CFM-DSS public dashboard (Lakes)</a>
      <small>Fetched only when you ask. Not an operational feed; do not use for flood or safety decisions.</small>
    </footer>
  </section>;
}

function ReservoirLiveCard({ series, period }: { series: ReservoirSeries; period: ReservoirPeriod }) {
  const levels = series.records.map((item) => item.waterLevelM);
  const min = Math.min(...levels);
  const max = Math.max(...levels);
  const span = max - min;
  const first = series.records[0];
  const change = series.latest.waterLevelM - first.waterLevelM;
  const points = series.records.map((item, index) => {
    const x = series.records.length === 1 ? 50 : (index / (series.records.length - 1)) * 100;
    const y = span === 0 ? 50 : 90 - ((item.waterLevelM - min) / span) * 80;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(' ');
  return <article className="tg-reservoir-live__card" aria-label={`${series.reservoirName}: water level ${series.latest.waterLevelM.toFixed(2)} metres, storage ${series.latest.averageStorageMcm.toFixed(2)} MCM on ${series.latest.sourceDate}`}>
    <header><strong>{series.reservoirName}</strong><span>{period === 'daily' ? 'Date' : 'Month'} {period === 'daily' ? series.latest.sourceDate : series.latest.sourceDate.slice(0, 7)}</span></header>
    <dl>
      <div><dt>Water level</dt><dd>{series.latest.waterLevelM.toFixed(2)} <small>m</small></dd></div>
      <div><dt>Avg storage</dt><dd>{series.latest.averageStorageMcm.toFixed(2)} <small>MCM</small></dd></div>
    </dl>
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={`${series.reservoirName} water level over ${series.records.length} ${period === 'daily' ? 'days' : 'months'}, ${min.toFixed(2)} to ${max.toFixed(2)} metres`}>
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
    </svg>
    <small className="tg-reservoir-live__change">{change >= 0 ? '+' : '−'}{Math.abs(change).toFixed(2)} m since {period === 'daily' ? first.sourceDate : first.sourceDate.slice(0, 7)}</small>
  </article>;
}
