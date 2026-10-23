CREATE TABLE IF NOT EXISTS twinguard.road_nodes (
    node_id text PRIMARY KEY,
    source_osmid text,
    degree integer,
    component_id bigint,
    geom geometry(Point,32644) NOT NULL,
    source_id text NOT NULL, source_sha256 text NOT NULL, loader text NOT NULL,
    load_time timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS road_nodes_geom_gix ON twinguard.road_nodes USING gist (geom);
CREATE INDEX IF NOT EXISTS road_nodes_source_idx ON twinguard.road_nodes(source_id);

CREATE TABLE IF NOT EXISTS twinguard.grid_cells (
    cell_id text PRIMARY KEY,
    row_index integer NOT NULL, col_index integer NOT NULL,
    x double precision NOT NULL, y double precision NOT NULL,
    elevation_m double precision, slope_deg double precision, twi_d8_proxy double precision,
    flow_accumulation_cells_d8 double precision, worldpop_2021 double precision,
    population_is_nodata boolean NOT NULL,
    built_up_fraction double precision, water_fraction double precision,
    building_density_per_km2 double precision,
    distance_to_nearest_road_node_m double precision,
    distance_to_exact_named_waterway_m double precision, distance_to_coast_m double precision,
    coast_distance_available boolean,
    geom geometry(Point,32644) NOT NULL,
    source_id text NOT NULL, source_sha256 text NOT NULL, loader text NOT NULL,
    load_time timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS grid_cells_geom_gix ON twinguard.grid_cells USING gist (geom);
CREATE INDEX IF NOT EXISTS grid_cells_source_idx ON twinguard.grid_cells(source_id);

CREATE TABLE IF NOT EXISTS twinguard.building_footprints (
    feature_id bigserial PRIMARY KEY,
    source_osmid text, building text, name text,
    geom geometry(Geometry,32644) NOT NULL,
    source_id text NOT NULL, source_sha256 text NOT NULL, loader text NOT NULL,
    load_time timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS building_footprints_geom_gix ON twinguard.building_footprints USING gist (geom);

CREATE TABLE IF NOT EXISTS twinguard.observation_records (
    record_id bigserial PRIMARY KEY,
    record_key text NOT NULL UNIQUE,
    series text NOT NULL,
    observed_at timestamptz NOT NULL,
    variable text NOT NULL,
    value double precision,
    unit text,
    qc_flag text NOT NULL,
    station_or_point text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(Point,32644),
    source_id text NOT NULL, source_sha256 text NOT NULL, loader text NOT NULL,
    load_time timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS observation_records_series_time_idx ON twinguard.observation_records(series,variable,observed_at);
CREATE INDEX IF NOT EXISTS observation_records_geom_gix ON twinguard.observation_records USING gist (geom);

CREATE TABLE IF NOT EXISTS twinguard.flood_labels (
    label_id bigserial PRIMARY KEY,
    label_key text NOT NULL UNIQUE,
    label_name text NOT NULL,
    event_date date,
    label_type text NOT NULL CHECK (label_type IN ('UNOSAT','OBSERVED','MODELLED','COARSE CROSS-CHECK','DERIVED')),
    confidence_tier text NOT NULL CHECK (confidence_tier IN ('HIGH','MEDIUM','LOW','UNVALIDATED')),
    is_modelled boolean NOT NULL DEFAULT false,
    is_coarse boolean NOT NULL DEFAULT false,
    is_derived boolean NOT NULL DEFAULT false,
    source_properties jsonb NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(Geometry,32644),
    is_valid boolean,
    source_id text NOT NULL, source_sha256 text NOT NULL, loader text NOT NULL,
    load_time timestamptz NOT NULL DEFAULT now(),
    CHECK ((label_type <> 'MODELLED') OR is_modelled),
    CHECK ((label_type <> 'COARSE CROSS-CHECK') OR is_coarse),
    CHECK ((label_type <> 'DERIVED') OR is_derived)
);
CREATE INDEX IF NOT EXISTS flood_labels_geom_gix ON twinguard.flood_labels USING gist (geom);
CREATE INDEX IF NOT EXISTS flood_labels_date_idx ON twinguard.flood_labels(event_date);

CREATE TABLE IF NOT EXISTS twinguard.sentinel_scenes (
    scene_key text PRIMARY KEY,
    scene_date date NOT NULL,
    platform text,
    product_type text,
    relative_orbit integer,
    pass_direction text,
    polarization text,
    source_filename text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    footprint geometry(Polygon,4326),
    source_id text NOT NULL, source_sha256 text NOT NULL, loader text NOT NULL,
    load_time timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sentinel_scenes_footprint_gix ON twinguard.sentinel_scenes USING gist (footprint);

CREATE TABLE IF NOT EXISTS twinguard.data_manifest (
    manifest_row_id bigserial PRIMARY KEY,
    manifest_key text NOT NULL UNIQUE,
    row_data jsonb NOT NULL,
    source_id text NOT NULL, source_sha256 text NOT NULL, loader text NOT NULL,
    load_time timestamptz NOT NULL DEFAULT now()
);
