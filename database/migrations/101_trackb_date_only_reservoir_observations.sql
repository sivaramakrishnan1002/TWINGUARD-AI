-- Additive Track B representation for source records that provide a calendar
-- date but no measurement instant. Existing timestamped tables and rows remain
-- unchanged. B20 applies this migration only to the verified isolated test DB.

CREATE TABLE IF NOT EXISTS twin.trackb_reservoir_daily_observations (
    run_id bigint NOT NULL REFERENCES twin.state_runs(run_id) ON DELETE CASCADE,
    source_date date NOT NULL,
    reservoir_key text NOT NULL REFERENCES twin.reservoirs(reservoir_key),
    event_id text NOT NULL UNIQUE,
    source text NOT NULL CHECK (source IN ('replay','live','simulated')),
    received_at timestamptz NOT NULL,
    observed_at timestamptz NULL CHECK (observed_at IS NULL),
    observation_timezone text NOT NULL DEFAULT 'unknown'
        CHECK (observation_timezone = 'unknown'),
    rainfall_mm double precision CHECK (rainfall_mm IS NULL OR rainfall_mm >= 0),
    storage_mcft double precision CHECK (storage_mcft IS NULL OR storage_mcft >= 0),
    capacity_mcft double precision CHECK (capacity_mcft IS NULL OR capacity_mcft > 0),
    release_cusecs double precision CHECK (release_cusecs IS NULL OR release_cusecs >= 0),
    observation_time_status text NOT NULL DEFAULT 'unknown'
        CHECK (observation_time_status = 'unknown'),
    qc_flags jsonb NOT NULL DEFAULT '[]'::jsonb,
    provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (run_id, source_date, reservoir_key)
);
CREATE INDEX IF NOT EXISTS trackb_reservoir_daily_date_idx
    ON twin.trackb_reservoir_daily_observations(source_date, reservoir_key);

CREATE TABLE IF NOT EXISTS twin.trackb_date_only_recompute_markers (
    marker_key text PRIMARY KEY,
    reservoir_key text NOT NULL REFERENCES twin.reservoirs(reservoir_key),
    source_date date NOT NULL,
    source text NOT NULL CHECK (source IN ('replay','live','simulated')),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    consumed_at timestamptz
);
CREATE INDEX IF NOT EXISTS trackb_date_only_recompute_pending_idx
    ON twin.trackb_date_only_recompute_markers(created_at)
    WHERE consumed_at IS NULL;

CREATE TABLE IF NOT EXISTS trackb.date_only_alert_events (
    event_id text PRIMARY KEY,
    source_date date NOT NULL,
    received_at timestamptz NOT NULL,
    source text NOT NULL CHECK (source IN ('replay','live','simulated')),
    payload jsonb NOT NULL,
    provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS trackb_date_only_alert_date_idx
    ON trackb.date_only_alert_events(source_date, event_id);

COMMENT ON TABLE twin.trackb_reservoir_daily_observations IS
    'Date-keyed Track B reservoir observations; no measurement instant or timezone is asserted.';
COMMENT ON TABLE twin.trackb_date_only_recompute_markers IS
    'Date-keyed Track B recompute work; source_date is the only observation-time key.';
COMMENT ON TABLE trackb.date_only_alert_events IS
    'Date-only Track B alerts without fabricated observed_at or exact validity interval.';
