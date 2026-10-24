CREATE SCHEMA IF NOT EXISTS labels;

CREATE TABLE IF NOT EXISTS labels.derived_flood_polygons (
    label_key text PRIMARY KEY,
    event_date date NOT NULL,
    method text NOT NULL,
    tier text NOT NULL CHECK (tier IN ('B', 'C')),
    is_derived boolean NOT NULL CHECK (is_derived),
    is_valid boolean NOT NULL,
    in_cma boolean NOT NULL,
    urban_unreliable boolean NOT NULL,
    flood_area_km2 double precision NOT NULL CHECK (flood_area_km2 >= 0),
    source_id text NOT NULL,
    source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    loader text NOT NULL,
    load_time timestamptz NOT NULL DEFAULT now(),
    geom geometry(MultiPolygon, 32644) NOT NULL
);

CREATE INDEX IF NOT EXISTS derived_flood_polygons_geom_gix
    ON labels.derived_flood_polygons USING gist (geom);
CREATE INDEX IF NOT EXISTS derived_flood_polygons_event_idx
    ON labels.derived_flood_polygons (event_date);

COMMENT ON TABLE labels.derived_flood_polygons IS
    'SAR-derived flood candidates; DERIVED, not ground truth. Original sources remain unchanged.';
