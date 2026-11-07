import { useEffect, useRef, useState } from 'react';
import { fetchChennaiWeather, OPEN_METEO_ATTRIBUTION_URL, type OpenMeteoWeatherSnapshot } from './openMeteoClient';

type WeatherState =
  | { status: 'loading'; snapshot: null; message: string }
  | { status: 'available'; snapshot: OpenMeteoWeatherSnapshot; message: null }
  | { status: 'unavailable'; snapshot: null; message: string }
  | { status: 'refresh-failed'; snapshot: OpenMeteoWeatherSnapshot; message: string };

export function weatherRequestFailed(previous: OpenMeteoWeatherSnapshot | null, reason: string, timedOut = false): WeatherState {
  const message = timedOut
    ? 'Weather-model request timed out.'
    : `Weather-model request failed: ${reason}`;
  if (!previous) return { status: 'unavailable', snapshot: null, message };
  return {
    status: 'refresh-failed',
    snapshot: previous,
    message: `${message} The last successful response is retained and is not presented as current.`,
  };
}

const REFRESH_MS = 30 * 60 * 1000;

export function OpenMeteoWeatherCard() {
  const [state, setState] = useState<WeatherState>({ status: 'loading', snapshot: null, message: 'Loading external weather model…' });
  const [refreshing, setRefreshing] = useState(false);
  const refreshRef = useRef<() => void>(() => undefined);
  const stateSnapshotRef = useRef<OpenMeteoWeatherSnapshot | null>(null);

  useEffect(() => {
    let mounted = true;
    let inFlight = false;
    let controller: AbortController | null = null;
    const refresh = async () => {
      if (inFlight) return;
      inFlight = true;
      controller = new AbortController();
      setRefreshing(true);
      if (!stateSnapshotRef.current) setState({ status: 'loading', snapshot: null, message: 'Loading external weather model…' });
      const timeout = window.setTimeout(() => controller?.abort(), 10_000);
      try {
        const snapshot = await fetchChennaiWeather(fetch, () => new Date(), controller.signal);
        if (!mounted) return;
        stateSnapshotRef.current = snapshot;
        setState({ status: 'available', snapshot, message: null });
      } catch (error) {
        if (!mounted) return;
        if (error instanceof Error && error.name === 'AbortError' && controller?.signal.aborted) {
          setState(weatherRequestFailed(stateSnapshotRef.current, 'Request timed out.', true));
          return;
        }
        const message = error instanceof Error ? error.message : 'Weather provider request failed.';
        setState(weatherRequestFailed(stateSnapshotRef.current, message));
      } finally {
        window.clearTimeout(timeout);
        inFlight = false;
        if (mounted) setRefreshing(false);
      }
    };
    // The card mounts only while Overview is open, so network requests stop when the user leaves it.
    refreshRef.current = () => { void refresh(); };
    void refresh();
    const timer = window.setInterval(refresh, REFRESH_MS);
    return () => {
      mounted = false;
      window.clearInterval(timer);
      controller?.abort();
      refreshRef.current = () => undefined;
    };
  }, []);

  const snapshot = state.snapshot;
  const maximum = Math.max(0, ...((snapshot?.hourly ?? []).map((item) => item.precipitationMm ?? 0)));
  return <section className="tg-weather-card" aria-labelledby="tg-weather-title" data-weather-status={state.status}>
    <header className="tg-weather-card__header">
      <div><span className="tg-product__eyebrow">EXTERNAL WEATHER MODEL · CHENNAI</span><h2 id="tg-weather-title">Current weather context</h2></div>
      <span className={`tg-weather-card__status tg-weather-card__status--${state.status}`} role="status">{state.status === 'available' ? 'MODEL DATA RECEIVED' : state.status === 'refresh-failed' ? 'REFRESH FAILED' : state.status === 'loading' ? 'LOADING' : 'UNAVAILABLE'}</span>
    </header>
    <p className="tg-weather-card__interpretation">Numerical weather-model estimates—not rain-gauge observations. This feed does not drive flood, reservoir, alert, impact, route, or shelter results.</p>
    {!snapshot && <p className="tg-weather-card__message" role={state.status === 'unavailable' ? 'alert' : 'status'}>{state.message}</p>}
    {snapshot && <>
      {state.status === 'refresh-failed' && <p className="tg-weather-card__message" role="status">{state.message}</p>}
      <dl className="tg-weather-card__metrics">
        <WeatherMetric label={`Precipitation · previous ${Math.round(snapshot.current.intervalSeconds / 60)} min`} value={format(snapshot.current.precipitationMm, 1)} unit="mm · model estimate" />
        <WeatherMetric label="Rain · same interval" value={format(snapshot.current.rainMm, 1)} unit="mm · model estimate" />
        <WeatherMetric label="Air temperature" value={format(snapshot.current.temperatureC, 1)} unit="°C · model estimate" />
        <WeatherMetric label="Relative humidity" value={format(snapshot.current.relativeHumidityPercent, 0)} unit="% · model estimate" />
      </dl>
      <div className="tg-weather-card__forecast">
        <div className="tg-weather-card__forecast-head"><strong>Hourly precipitation outlook</strong><span>Next {snapshot.hourly.length} local hours · mm</span></div>
        <ol aria-label="Open-Meteo hourly precipitation forecast in millimetres">
          {snapshot.hourly.map((point) => <li key={point.validTimeLocal} aria-label={`${point.validTimeLocal.replace('T', ' ')} Asia/Kolkata: ${point.precipitationMm === null ? 'unknown' : `${point.precipitationMm} millimetres forecast`}`}>
            <span>{point.precipitationMm === null ? '—' : format(point.precipitationMm, 1)}</span>
            <i style={{ height: point.precipitationMm === null ? '2px' : `${maximum === 0 ? 2 : Math.max(2, (point.precipitationMm / maximum) * 42)}px` }} data-unknown={point.precipitationMm === null || undefined} />
            <small>{point.validTimeLocal.slice(11, 16)}</small>
          </li>)}
        </ol>
      </div>
      <div className="tg-weather-card__provenance">
        <span><strong>Model valid time</strong> {snapshot.current.validTimeLocal} Asia/Kolkata (not model issue time)</span>
        <span><strong>Fetched</strong> {snapshot.fetchedAt}</span>
        <span><strong>Provider grid point</strong> {snapshot.gridPoint.latitude.toFixed(4)}, {snapshot.gridPoint.longitude.toFixed(4)} · {format(snapshot.gridPoint.elevationM, 0)} m elevation</span>
      </div>
    </>}
    <footer className="tg-weather-card__footer">
      <a href={OPEN_METEO_ATTRIBUTION_URL} target="_blank" rel="noreferrer">Weather data from Open-Meteo · CC BY 4.0</a>
      <button type="button" className="tg-product__button" onClick={() => refreshRef.current()} disabled={refreshing} aria-label="Refresh Chennai weather model data">{refreshing ? 'Updating…' : 'Refresh'}</button>
    </footer>
    <small className="tg-weather-card__cadence">Refreshes at most every 30 minutes while this panel is open. Provider model updates are typically less frequent; a successful fetch does not mean a new model run.</small>
  </section>;
}

function WeatherMetric({ label, value, unit }: { label: string; value: string; unit: string }) {
  return <div><dt>{label}</dt><dd>{value}</dd><small>{unit}</small></div>;
}

function format(value: number | null, digits: number): string {
  return value === null ? 'Unknown' : value.toFixed(digits);
}

