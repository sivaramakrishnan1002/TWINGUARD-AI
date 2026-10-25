-- Track B replay hooks; safe to apply repeatedly.
CREATE SCHEMA IF NOT EXISTS trackb;
CREATE TABLE IF NOT EXISTS trackb.alert_events (
    event_id text PRIMARY KEY,
    source text NOT NULL CHECK (source IN ('replay','live','simulated')),
    observed_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS twin.trackb_alert_links (
    event_key text PRIMARY KEY,
    alert_id bigint NOT NULL UNIQUE REFERENCES twin.alerts(alert_id) ON DELETE CASCADE,
    source text NOT NULL CHECK (source IN ('replay','live','simulated')),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS twin.trackb_recompute_markers (
    marker_key text PRIMARY KEY,
    reservoir_key text NOT NULL REFERENCES twin.reservoirs(reservoir_key),
    valid_at timestamptz NOT NULL,
    source text NOT NULL CHECK (source IN ('replay','live','simulated')),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    consumed_at timestamptz
);
CREATE INDEX IF NOT EXISTS trackb_recompute_pending_idx
    ON twin.trackb_recompute_markers(created_at) WHERE consumed_at IS NULL;
COMMENT ON TABLE twin.trackb_alert_links IS 'Idempotency/provenance link for Track B alert events in twin.alerts.';
COMMENT ON TABLE twin.trackb_recompute_markers IS 'Idempotent Track B marker for a later twin recompute job.';
