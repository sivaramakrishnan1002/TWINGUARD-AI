CREATE SCHEMA IF NOT EXISTS twin;

CREATE TABLE IF NOT EXISTS twin.model_versions (
    version_key text PRIMARY KEY,
    component text NOT NULL,
    code_revision text,
    config_sha256 text,
    artifact_uri text,
    provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
    registered_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS twin.event_replays (
    replay_id bigserial PRIMARY KEY,
    event_key text NOT NULL UNIQUE,
    event_year smallint NOT NULL UNIQUE CHECK (event_year IN (2015, 2021, 2023)),
    local_window_start date NOT NULL,
    local_window_end date NOT NULL,
    local_time_zone text NOT NULL DEFAULT 'Asia/Kolkata',
    utc_window_start timestamptz NOT NULL,
    utc_window_end_exclusive timestamptz NOT NULL,
    replay_status text NOT NULL DEFAULT 'PLANNED'
        CHECK (replay_status IN ('PLANNED','READY','RUNNING','COMPLETE','FAILED')),
    window_source text NOT NULL,
    notes text NOT NULL DEFAULT '',
    provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (local_window_end >= local_window_start),
    CHECK (utc_window_end_exclusive > utc_window_start)
);

INSERT INTO twin.event_replays (
    event_key, event_year, local_window_start, local_window_end,
    utc_window_start, utc_window_end_exclusive, window_source, notes, provenance
) VALUES
    ('chennai_2015', 2015, DATE '2015-11-01', DATE '2015-12-15',
     TIMESTAMPTZ '2015-10-31 18:30:00+00', TIMESTAMPTZ '2015-12-15 18:30:00+00',
     'docs/TIME_ALIGNMENT.md and data/features/events/aligned_data_dictionary.json',
     'Inclusive local event-alignment window; UTC end is exclusive. Includes the 1-8 Dec peak period.',
     '{"window_kind":"aligned_event_window","native_data_replay_only":true}'::jsonb),
    ('chennai_2021', 2021, DATE '2021-11-01', DATE '2021-11-20',
     TIMESTAMPTZ '2021-10-31 18:30:00+00', TIMESTAMPTZ '2021-11-20 18:30:00+00',
     'docs/TIME_ALIGNMENT.md and data/features/events/aligned_data_dictionary.json',
     'Inclusive local event-alignment window; UTC end is exclusive.',
     '{"window_kind":"aligned_event_window","native_data_replay_only":true}'::jsonb),
    ('chennai_2023', 2023, DATE '2023-11-25', DATE '2023-12-15',
     TIMESTAMPTZ '2023-11-24 18:30:00+00', TIMESTAMPTZ '2023-12-15 18:30:00+00',
     'docs/TIME_ALIGNMENT.md and data/features/events/aligned_data_dictionary.json',
     'Inclusive local event-alignment window; UTC end is exclusive.',
     '{"window_kind":"aligned_event_window","native_data_replay_only":true}'::jsonb)
ON CONFLICT (event_key) DO NOTHING;

CREATE TABLE IF NOT EXISTS twin.scenarios (
    scenario_key text PRIMARY KEY,
    title text NOT NULL,
    description text NOT NULL DEFAULT '',
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    base_run_id bigint,
    scenario_status text NOT NULL DEFAULT 'DRAFT'
        CHECK (scenario_status IN ('DRAFT','READY','RUNNING','COMPLETE','FAILED')),
    created_by text,
    created_at timestamptz NOT NULL DEFAULT now(),
    provenance jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS twin.state_runs (
    run_id bigserial PRIMARY KEY,
    replay_id bigint REFERENCES twin.event_replays(replay_id),
    scenario_key text REFERENCES twin.scenarios(scenario_key),
    run_kind text NOT NULL CHECK (run_kind IN ('FORECAST','REPLAY','SCENARIO')),
    version_key text NOT NULL REFERENCES twin.model_versions(version_key),
    code_revision text,
    issued_at timestamptz NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to_exclusive timestamptz NOT NULL,
    step_interval interval NOT NULL CHECK (step_interval > interval '0'),
    input_provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
    qc_flags jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (valid_to_exclusive > valid_from),
    CHECK ((run_kind = 'REPLAY' AND replay_id IS NOT NULL)
        OR (run_kind = 'SCENARIO' AND scenario_key IS NOT NULL)
        OR run_kind = 'FORECAST')
);
ALTER TABLE twin.scenarios
    DROP CONSTRAINT IF EXISTS scenarios_base_run_id_fkey;
ALTER TABLE twin.scenarios
    ADD CONSTRAINT scenarios_base_run_id_fkey FOREIGN KEY (base_run_id)
    REFERENCES twin.state_runs(run_id) DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX IF NOT EXISTS state_runs_valid_idx ON twin.state_runs(valid_from, valid_to_exclusive);
CREATE INDEX IF NOT EXISTS state_runs_replay_idx ON twin.state_runs(replay_id, issued_at);

-- Grid zones are a view over the existing 30 m cell dimension. Per-cell
-- dynamic values remain in external raster/cube files, not extra DB rows.
CREATE OR REPLACE VIEW twin.grid_zones AS
SELECT cell_id AS zone_id, cell_id, row_index, col_index, x, y, geom
FROM twinguard.grid_cells;

CREATE TABLE IF NOT EXISTS twin.grid_state_artifacts (
    artifact_id bigserial PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES twin.state_runs(run_id) ON DELETE CASCADE,
    valid_at timestamptz NOT NULL,
    relative_path text NOT NULL,
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    media_type text NOT NULL,
    variable_manifest jsonb NOT NULL,
    coverage jsonb NOT NULL DEFAULT '{"scope":"CMA"}'::jsonb,
    nodata_policy text NOT NULL,
    qc_flags jsonb NOT NULL DEFAULT '{}'::jsonb,
    source_id text,
    source_sha256 text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, valid_at, relative_path)
);

CREATE TABLE IF NOT EXISTS twin.road_edge_state (
    run_id bigint NOT NULL REFERENCES twin.state_runs(run_id) ON DELETE CASCADE,
    valid_at timestamptz NOT NULL,
    edge_feature_id bigint NOT NULL REFERENCES twinguard.road_edges(feature_id),
    rainfall_mm double precision CHECK (rainfall_mm IS NULL OR rainfall_mm >= 0),
    predicted_depth_mean_m double precision,
    predicted_depth_p05_m double precision,
    predicted_depth_p95_m double precision,
    ensemble_id text,
    accessibility_probability double precision CHECK (accessibility_probability BETWEEN 0 AND 1),
    exposure_people double precision CHECK (exposure_people IS NULL OR exposure_people >= 0),
    capacity_vehicles_per_hour double precision CHECK (capacity_vehicles_per_hour IS NULL OR capacity_vehicles_per_hour >= 0),
    qc_flags jsonb NOT NULL DEFAULT '{}'::jsonb,
    provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (run_id, valid_at, edge_feature_id),
    CHECK (
        (predicted_depth_mean_m IS NULL AND predicted_depth_p05_m IS NULL AND predicted_depth_p95_m IS NULL AND ensemble_id IS NULL)
        OR (predicted_depth_mean_m IS NOT NULL AND predicted_depth_p05_m IS NOT NULL AND predicted_depth_p95_m IS NOT NULL
            AND predicted_depth_p05_m >= 0 AND predicted_depth_p05_m <= predicted_depth_mean_m
            AND predicted_depth_mean_m <= predicted_depth_p95_m AND ensemble_id IS NULL)
        OR (predicted_depth_mean_m IS NULL AND predicted_depth_p05_m IS NULL AND predicted_depth_p95_m IS NULL AND ensemble_id IS NOT NULL)
    )
);
CREATE INDEX IF NOT EXISTS road_edge_state_valid_idx ON twin.road_edge_state(valid_at);

CREATE TABLE IF NOT EXISTS twin.facility_state (
    run_id bigint NOT NULL REFERENCES twin.state_runs(run_id) ON DELETE CASCADE,
    valid_at timestamptz NOT NULL,
    facility_feature_id bigint NOT NULL REFERENCES twinguard.facilities(feature_id),
    rainfall_mm double precision CHECK (rainfall_mm IS NULL OR rainfall_mm >= 0),
    predicted_depth_mean_m double precision,
    predicted_depth_p05_m double precision,
    predicted_depth_p95_m double precision,
    ensemble_id text,
    accessibility_probability double precision CHECK (accessibility_probability BETWEEN 0 AND 1),
    exposure_people double precision CHECK (exposure_people IS NULL OR exposure_people >= 0),
    capacity_people double precision CHECK (capacity_people IS NULL OR capacity_people >= 0),
    source_observation_id bigint REFERENCES twinguard.observation_records(record_id),
    qc_flags jsonb NOT NULL DEFAULT '{}'::jsonb,
    provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (run_id, valid_at, facility_feature_id),
    CHECK (
        (predicted_depth_mean_m IS NULL AND predicted_depth_p05_m IS NULL AND predicted_depth_p95_m IS NULL AND ensemble_id IS NULL)
        OR (predicted_depth_mean_m IS NOT NULL AND predicted_depth_p05_m IS NOT NULL AND predicted_depth_p95_m IS NOT NULL
            AND predicted_depth_p05_m >= 0 AND predicted_depth_p05_m <= predicted_depth_mean_m
            AND predicted_depth_mean_m <= predicted_depth_p95_m AND ensemble_id IS NULL)
        OR (predicted_depth_mean_m IS NULL AND predicted_depth_p05_m IS NULL AND predicted_depth_p95_m IS NULL AND ensemble_id IS NOT NULL)
    )
);
CREATE INDEX IF NOT EXISTS facility_state_valid_idx ON twin.facility_state(valid_at);

CREATE TABLE IF NOT EXISTS twin.reservoirs (
    reservoir_key text PRIMARY KEY,
    display_name text NOT NULL,
    capacity_mcft double precision CHECK (capacity_mcft IS NULL OR capacity_mcft > 0),
    source_id text NOT NULL,
    source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
    registered_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO twin.reservoirs (reservoir_key, display_name, source_id, source_sha256, provenance)
SELECT lower(regexp_replace(station_or_point, '[^a-zA-Z0-9]+', '_', 'g')),
       CASE station_or_point
           WHEN 'CHEMBARAMBAKKAM' THEN 'Chembarambakkam'
           WHEN 'CHOLAVARAM' THEN 'Cholavaram'
           WHEN 'POONDI' THEN 'Poondi'
           WHEN 'REDHILLS' THEN 'Red Hills / Puzhal'
       END,
       source_id, source_sha256,
       '{"seeded_from":"existing reservoir daily observations","capacity_status":"unknown; not inferred","release_status":"not available in current input series"}'::jsonb
FROM (
    SELECT station_or_point, min(source_id) AS source_id, min(source_sha256) AS source_sha256
    FROM twinguard.observation_records
    WHERE series = 'reservoir daily'
      AND upper(station_or_point) IN ('CHEMBARAMBAKKAM','CHOLAVARAM','POONDI','REDHILLS')
    GROUP BY station_or_point
) src
ON CONFLICT (reservoir_key) DO NOTHING;

CREATE TABLE IF NOT EXISTS twin.reservoir_state (
    run_id bigint NOT NULL REFERENCES twin.state_runs(run_id) ON DELETE CASCADE,
    valid_at timestamptz NOT NULL,
    reservoir_key text NOT NULL REFERENCES twin.reservoirs(reservoir_key),
    rainfall_mm double precision CHECK (rainfall_mm IS NULL OR rainfall_mm >= 0),
    storage_mcft double precision CHECK (storage_mcft IS NULL OR storage_mcft >= 0),
    capacity_mcft double precision CHECK (capacity_mcft IS NULL OR capacity_mcft > 0),
    release_cusecs double precision CHECK (release_cusecs IS NULL OR release_cusecs >= 0),
    exposure_people double precision CHECK (exposure_people IS NULL OR exposure_people >= 0),
    accessibility_probability double precision CHECK (accessibility_probability BETWEEN 0 AND 1),
    source_observation_id bigint REFERENCES twinguard.observation_records(record_id),
    qc_flags jsonb NOT NULL DEFAULT '{}'::jsonb,
    provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (run_id, valid_at, reservoir_key)
);
CREATE INDEX IF NOT EXISTS reservoir_state_valid_idx ON twin.reservoir_state(valid_at);

CREATE TABLE IF NOT EXISTS twin.alerts (
    alert_id bigserial PRIMARY KEY,
    run_id bigint REFERENCES twin.state_runs(run_id),
    scenario_key text REFERENCES twin.scenarios(scenario_key),
    alert_type text NOT NULL,
    severity text NOT NULL CHECK (severity IN ('INFO','WATCH','WARNING','EMERGENCY')),
    issued_at timestamptz NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to_exclusive timestamptz NOT NULL,
    payload jsonb NOT NULL,
    provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
    CHECK (valid_to_exclusive > valid_from)
);

CREATE INDEX IF NOT EXISTS grid_state_artifacts_run_idx ON twin.grid_state_artifacts(run_id, valid_at);
