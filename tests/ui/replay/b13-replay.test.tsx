import type { B13Envelope } from '../../../frontend/src/ui/replay/B13ReplayView';

type UiModule = {
  B13ReplayView: () => unknown;
  ReplayDetails: (props: { data: B13Envelope }) => unknown;
  b13ReplayPath: (eventId?: string) => string;
  validateReplayEnvelope: (value: unknown) => boolean;
  loadReplay: () => Promise<{ kind: string; message?: string; data?: B13Envelope }>;
};

type Assertions = {
  equal(actual: unknown, expected: unknown, message?: string): void;
  ok(value: unknown, message?: string): void;
  match(value: string, regexp: RegExp, message?: string): void;
};

export async function runB13ReplayUiChecks(
  ui: UiModule,
  assertions: Assertions,
  render: (component: unknown) => string,
  createElement: (type: unknown, props: Record<string, unknown>) => unknown,
): Promise<void> {
  const assert = assertions;
  const data: B13Envelope = {
    contract_version: 'C4-v2',
    source_observation: {
      event_id: 'replay:POONDI:date:2015-12-01', source: 'replay', source_mode: 'REPLAY',
      time_precision: 'date', source_date: '2015-12-01', observed_at: null, observation_timezone: 'unknown',
      received_at: '2026-10-31T10:00:00Z', reservoir_key: 'POONDI',
      raw_source_row: { Date: '01-12-2015', POONDI: '2745.00' }, storage_value: 2745, storage_unit: 'mcft',
      provenance: { archive_sha256: 'a'.repeat(64), member_sha256: 'b'.repeat(64), csv_physical_line: 4354, raw_storage_value: '2745.00', rainfall_unit_status: 'INFERRED; original unit unspecified' },
    },
    replay: { replay_run_id: `sha256:${'c'.repeat(64)}`, algorithm_id: 'trackb-rule-v1', configuration_sha256: 'd'.repeat(64), normalized_input_sha256: 'e'.repeat(64), context_inputs: [] },
    derived_output: { status: 'produced', alert: { level: 'Warning', confidence: 0.75, received_at: '2026-10-31T10:00:00Z', trigger_inputs: { rain_3d_mm: 86.7 } }, output_sha256: 'f'.repeat(64) },
    limitations: ['Historical time and timezone unknown.', 'Derived rule output only; research use.'],
  };
  assert.equal(ui.b13ReplayPath(), '/replay-alerts/replay%3APOONDI%3Adate%3A2015-12-01');
  assert.ok(ui.validateReplayEnvelope(data), 'date-only envelope should validate');
  assert.equal(ui.validateReplayEnvelope({ ...data, source_observation: { ...data.source_observation, observed_at: '2015-12-01T00:00:00Z' } }), false, 'synthetic instant must be rejected');

  const loading = render(createElement(ui.B13ReplayView, {}));
  assert.match(loading, /Loading the approved replay input/);
  const ready = render(createElement(ui.ReplayDetails, { data }));
  assert.match(ready, /Observation instant/);
  assert.match(ready, /Unknown · date-only source/);
  assert.match(ready, /2026-10-31T10:00:00Z/);
  assert.match(ready, /2745\.00/);
  assert.match(ready, /DERIVED REPLAY OUTPUT/);
  assert.match(ready, /INFERRED; original unit unspecified/);

  const noOutput = { ...data, derived_output: { status: 'not_produced' as const, alert: null, output_sha256: null } };
  const unavailableMarkup = render(createElement(ui.ReplayDetails, { data: noOutput }));
  assert.match(unavailableMarkup, /No derived alert was produced/);
  assert.match(unavailableMarkup, /does not mean dry, safe, or flood-free/);

  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async (input, init) => {
      assert.match(String(input), /127\.0\.0\.1:8080\/replay-alerts\/replay%3APOONDI/);
      assert.equal(init?.method, 'GET');
      assert.equal(init?.credentials, 'omit');
      return { ok: true, json: async () => data } as Response;
    };
    assert.equal((await ui.loadReplay()).kind, 'ready');
    globalThis.fetch = async () => ({ ok: false, status: 503, json: async () => ({ detail: 'temporarily unavailable' }) } as Response);
    assert.equal((await ui.loadReplay()).kind, 'error');
  } finally {
    globalThis.fetch = originalFetch;
  }
}
