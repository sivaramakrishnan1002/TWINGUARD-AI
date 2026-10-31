import { useEffect, useState } from 'react';

export type B13Envelope = {
  contract_version: 'C4-v2';
  source_observation: {
    event_id: string;
    source: 'replay';
    source_mode: 'REPLAY';
    time_precision: 'date';
    source_date: string;
    observed_at: null;
    observation_timezone: 'unknown';
    received_at: string;
    reservoir_key: string;
    raw_source_row: Record<string, string>;
    storage_value: number;
    storage_unit: string;
    provenance: { archive_sha256: string; member_sha256: string; csv_physical_line: number; raw_storage_value: string; rainfall_unit_status: string };
  };
  replay: { replay_run_id: string; algorithm_id: string; configuration_sha256: string; normalized_input_sha256: string; context_inputs: Array<{ source_date: string; role: string }> };
  derived_output: { status: 'produced' | 'not_produced'; alert: null | { level: string; confidence: number; received_at: string; trigger_inputs: Record<string, number | null> }; output_sha256: string | null };
  limitations: string[];
};

export type ReplayUiState = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; data: B13Envelope };

export function b13ReplayPath(eventId = 'replay:POONDI:date:2015-12-01'): string {
  return `/replay-alerts/${encodeURIComponent(eventId)}`;
}

export function validateReplayEnvelope(value: unknown): value is B13Envelope {
  if (!value || typeof value !== 'object') return false;
  const data = value as Partial<B13Envelope>;
  const source = data.source_observation;
  const hashes = [source?.provenance?.archive_sha256, source?.provenance?.member_sha256, data.replay?.configuration_sha256, data.replay?.normalized_input_sha256];
  const output = data.derived_output;
  return data.contract_version === 'C4-v2'
    && source?.event_id === 'replay:POONDI:date:2015-12-01'
    && source.source_mode === 'REPLAY'
    && source.time_precision === 'date'
    && source.source_date === '2015-12-01'
    && source.observed_at === null
    && source.observation_timezone === 'unknown'
    && typeof source.received_at === 'string'
    && hashes.every((hash) => typeof hash === 'string' && /^[a-f0-9]{64}$/.test(hash))
    && /^sha256:[a-f0-9]{64}$/.test(data.replay?.replay_run_id ?? '')
    && ((output?.status === 'not_produced' && output.alert === null && output.output_sha256 === null)
      || (output?.status === 'produced' && Boolean(output.alert) && typeof output.output_sha256 === 'string' && /^[a-f0-9]{64}$/.test(output.output_sha256)))
    && Array.isArray(data.limitations) && data.limitations.length > 0;
}

export async function loadReplay(): Promise<ReplayUiState> {
  try {
    const response = await fetch(`http://127.0.0.1:8080${b13ReplayPath()}`, { method: 'GET', headers: { Accept: 'application/json' }, credentials: 'omit' });
    const body: unknown = await response.json();
    if (!response.ok) {
      const error = body as { detail?: unknown };
      return { kind: 'error', message: typeof error.detail === 'string' ? error.detail : `Replay lookup unavailable (${response.status}).` };
    }
    if (!validateReplayEnvelope(body)) return { kind: 'error', message: 'The replay response did not match the approved C4 v2 projection.' };
    return { kind: 'ready', data: body };
  } catch {
    return { kind: 'error', message: 'The test-scoped replay service is unavailable.' };
  }
}

export function B13ReplayView() {
  const [state, setState] = useState<ReplayUiState>({ kind: 'loading' });
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    setState({ kind: 'loading' });
    void loadReplay().then((next) => { if (active) setState(next); });
    return () => { active = false; };
  }, [reload]);

  return (
    <section aria-labelledby="b13-title" data-testid="b13-replay-view">
      <header>
        <p>HISTORICAL REPLAY · RESEARCH ONLY</p>
        <h1 id="b13-title">POONDI source observation</h1>
        <p>One immutable date-only archive input. Any rule result below is separately generated derived output.</p>
      </header>
      <button type="button" onClick={() => setReload((n) => n + 1)}>Reload approved replay</button>
      {state.kind === 'loading' && <p role="status">Loading the approved replay input…</p>}
      {state.kind === 'error' && <p role="alert">Replay unavailable: {state.message}</p>}
      {state.kind === 'ready' && <ReplayDetails data={state.data} />}
    </section>
  );
}

export function ReplayDetails({ data }: { data: B13Envelope }) {
  const source = data.source_observation;
  const output = data.derived_output;
  return (
    <div>
      <section aria-labelledby="b13-source-title">
        <h2 id="b13-source-title">Archived REPLAY input</h2>
        <dl>
          <dt>Selector</dt><dd>{source.event_id}</dd>
          <dt>Reservoir / source date</dt><dd>{source.reservoir_key} · {source.source_date}</dd>
          <dt>Observation instant</dt><dd>Unknown · date-only source</dd>
          <dt>Observation timezone</dt><dd>Unknown</dd>
          <dt>Replay receipt time</dt><dd>{source.received_at}</dd>
          <dt>Raw source row</dt><dd>Date={source.raw_source_row.Date}; POONDI={source.raw_source_row.POONDI}</dd>
          <dt>Storage value</dt><dd>{source.storage_value} {source.storage_unit}</dd>
          <dt>Archive SHA-256</dt><dd><code>{source.provenance.archive_sha256}</code></dd>
          <dt>CSV member SHA-256</dt><dd><code>{source.provenance.member_sha256}</code></dd>
          <dt>CSV row</dt><dd>Line {source.provenance.csv_physical_line}</dd>
        </dl>
      </section>
      <section aria-labelledby="b13-derived-title">
        <h2 id="b13-derived-title">Derived replay processing</h2>
        <p>Replay run: <code>{data.replay.replay_run_id}</code></p>
        <p>Normalized input SHA-256: <code>{data.replay.normalized_input_sha256}</code></p>
        <p>Configuration SHA-256: <code>{data.replay.configuration_sha256}</code></p>
        {output.status === 'not_produced' || !output.alert ? (
          <p role="status">No derived alert was produced. This does not mean dry, safe, or flood-free.</p>
        ) : (
          <article aria-label="Derived replay alert">
            <strong>DERIVED REPLAY OUTPUT · {output.alert.level}</strong>
            <p>This is generated storage-rule output, not a historically observed event or validated flood result.</p>
            <p>Output SHA-256: <code>{output.output_sha256}</code></p>
            <p>Actual processing receipt: {output.alert.received_at}</p>
            <p>Rainfall unit status: {source.provenance.rainfall_unit_status}</p>
          </article>
        )}
      </section>
      <section aria-labelledby="b13-limitations-title"><h2 id="b13-limitations-title">Limitations</h2><ul>{data.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul></section>
    </div>
  );
}
