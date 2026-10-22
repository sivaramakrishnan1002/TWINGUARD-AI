CREATE SCHEMA IF NOT EXISTS twinguard;

CREATE TABLE IF NOT EXISTS twinguard.schema_migrations (
    version text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now(),
    checksum_sha256 text NOT NULL
);

CREATE TABLE IF NOT EXISTS twinguard.dataset_catalog (
    layer_key text PRIMARY KEY,
    source_path text NOT NULL,
    source_layer text NOT NULL,
    source_sha256 text NOT NULL,
    source_crs text NOT NULL,
    target_srid integer NOT NULL CHECK (target_srid = 32644),
    loaded_row_count bigint NOT NULL CHECK (loaded_row_count >= 0),
    loaded_at timestamptz NOT NULL DEFAULT now(),
    caveat text NOT NULL,
    licence_note text NOT NULL
);

CREATE TABLE IF NOT EXISTS twinguard.study_area (
    feature_id bigserial PRIMARY KEY,
    name text NOT NULL,
    boundary_vintage text NOT NULL,
    geom geometry(MultiPolygon, 32644) NOT NULL
);

CREATE TABLE IF NOT EXISTS twinguard.road_edges (
    feature_id bigserial PRIMARY KEY,
    source_osmid text,
    node_a text,
    node_b text,
    highway text,
    length_m double precision,
    speed_kmh double precision,
    speed_assumed boolean,
    travel_time_min double precision,
    bridge text,
    tunnel text,
    elev_min_m double precision,
    elev_mean_m double precision,
    elev_max_m double precision,
    geom geometry(LineString, 32644) NOT NULL
);

CREATE TABLE IF NOT EXISTS twinguard.facilities (
    feature_id bigserial PRIMARY KEY,
    source_osmid text,
    source_type text,
    category text,
    name text,
    nearest_road_distance_m double precision,
    geom geometry(Point, 32644) NOT NULL
);

CREATE TABLE IF NOT EXISTS twinguard.waterways (
    feature_id bigserial PRIMARY KEY,
    source_osmid text,
    waterway text,
    name text,
    geom geometry(LineString, 32644) NOT NULL
);

CREATE TABLE IF NOT EXISTS twinguard.flood_references (
    feature_id bigserial PRIMARY KEY,
    source_layer text NOT NULL,
    event_date date NOT NULL,
    reference_role text NOT NULL CHECK (reference_role IN ('baseline_water', 'event_flood')),
    source_properties jsonb NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(Geometry, 32644) NOT NULL
);

CREATE INDEX IF NOT EXISTS study_area_geom_gix ON twinguard.study_area USING gist (geom);
CREATE INDEX IF NOT EXISTS road_edges_geom_gix ON twinguard.road_edges USING gist (geom);
CREATE INDEX IF NOT EXISTS facilities_geom_gix ON twinguard.facilities USING gist (geom);
CREATE INDEX IF NOT EXISTS waterways_geom_gix ON twinguard.waterways USING gist (geom);
CREATE INDEX IF NOT EXISTS flood_references_geom_gix ON twinguard.flood_references USING gist (geom);
CREATE INDEX IF NOT EXISTS flood_references_date_idx ON twinguard.flood_references (event_date);
