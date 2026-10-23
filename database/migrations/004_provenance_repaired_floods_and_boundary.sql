ALTER TABLE twinguard.dataset_catalog
    ADD COLUMN IF NOT EXISTS source_url text,
    ADD COLUMN IF NOT EXISTS retrieval_date date,
    ADD COLUMN IF NOT EXISTS source_vintage text;

UPDATE twinguard.dataset_catalog
SET source_url = 'https://github.com/datameet/Municipal_Spatial_Data',
    retrieval_date = NULL,
    source_vintage = 'Older CMA boundary selected by project; source vintage and retrieval date not verified.'
WHERE layer_key = 'study_area_older_cma';

ALTER TABLE twinguard.study_area
    ADD COLUMN IF NOT EXISTS source_id text,
    ADD COLUMN IF NOT EXISTS source_sha256 text,
    ADD COLUMN IF NOT EXISTS loader text,
    ADD COLUMN IF NOT EXISTS load_time timestamptz;
ALTER TABLE twinguard.road_edges
    ADD COLUMN IF NOT EXISTS source_id text,
    ADD COLUMN IF NOT EXISTS source_sha256 text,
    ADD COLUMN IF NOT EXISTS loader text,
    ADD COLUMN IF NOT EXISTS load_time timestamptz;
ALTER TABLE twinguard.facilities
    ADD COLUMN IF NOT EXISTS source_id text,
    ADD COLUMN IF NOT EXISTS source_sha256 text,
    ADD COLUMN IF NOT EXISTS loader text,
    ADD COLUMN IF NOT EXISTS load_time timestamptz;
ALTER TABLE twinguard.waterways
    ADD COLUMN IF NOT EXISTS source_id text,
    ADD COLUMN IF NOT EXISTS source_sha256 text,
    ADD COLUMN IF NOT EXISTS loader text,
    ADD COLUMN IF NOT EXISTS load_time timestamptz;
ALTER TABLE twinguard.flood_references
    ADD COLUMN IF NOT EXISTS source_id text,
    ADD COLUMN IF NOT EXISTS source_sha256 text,
    ADD COLUMN IF NOT EXISTS loader text,
    ADD COLUMN IF NOT EXISTS load_time timestamptz,
    ADD COLUMN IF NOT EXISTS geom_repaired geometry(MultiPolygon, 32644),
    ADD COLUMN IF NOT EXISTS is_valid boolean;

UPDATE twinguard.study_area s
SET source_id = c.layer_key, source_sha256 = c.source_sha256,
    loader = 'pipelines.stage6.load_gis_layers', load_time = c.loaded_at
FROM twinguard.dataset_catalog c WHERE c.layer_key = 'study_area_older_cma'
  AND s.source_id IS NULL;
UPDATE twinguard.road_edges r
SET source_id = c.layer_key, source_sha256 = c.source_sha256,
    loader = 'pipelines.stage6.load_gis_layers', load_time = c.loaded_at
FROM twinguard.dataset_catalog c WHERE c.layer_key = 'vehicle_road_edges'
  AND r.source_id IS NULL;
UPDATE twinguard.facilities f
SET source_id = c.layer_key, source_sha256 = c.source_sha256,
    loader = 'pipelines.stage6.load_gis_layers', load_time = c.loaded_at
FROM twinguard.dataset_catalog c WHERE c.layer_key = 'osm_facilities'
  AND f.source_id IS NULL;
UPDATE twinguard.waterways w
SET source_id = c.layer_key, source_sha256 = c.source_sha256,
    loader = 'pipelines.stage6.load_gis_layers', load_time = c.loaded_at
FROM twinguard.dataset_catalog c WHERE c.layer_key = 'osm_waterways'
  AND w.source_id IS NULL;
UPDATE twinguard.flood_references f
SET source_id = 'unosat_' || f.source_layer,
    source_sha256 = c.source_sha256,
    loader = 'pipelines.stage6.load_gis_layers', load_time = c.loaded_at
FROM twinguard.dataset_catalog c
WHERE c.layer_key = 'unosat_' || f.source_layer AND f.source_id IS NULL;

UPDATE twinguard.flood_references
SET geom_repaired = ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3))::geometry(MultiPolygon,32644),
    is_valid = ST_IsValid(ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3)))
WHERE geom_repaired IS NULL OR is_valid IS NULL;

CREATE INDEX IF NOT EXISTS flood_references_repaired_geom_gix
    ON twinguard.flood_references USING gist (geom_repaired);

CREATE OR REPLACE VIEW twinguard.v_flood_references AS
SELECT feature_id, source_layer, event_date, reference_role, source_properties,
       geom_repaired::geometry(Geometry,32644) AS geom, is_valid
FROM twinguard.flood_references;

CREATE OR REPLACE FUNCTION twinguard.mvt_flood_references(z integer, x integer, y integer)
RETURNS bytea LANGUAGE sql STABLE STRICT PARALLEL SAFE AS $$
WITH b AS (SELECT ST_TileEnvelope(z, x, y) AS box), q AS (
  SELECT f.feature_id, f.source_layer, f.event_date, f.reference_role,
         ST_AsMVTGeom(ST_Transform(f.geom_repaired, 3857), b.box, 4096, 64, true) AS geom
  FROM twinguard.flood_references f CROSS JOIN b
  WHERE z BETWEEN 0 AND 22 AND f.geom_repaired && ST_Transform(b.box, 32644)
)
SELECT ST_AsMVT(q, 'flood_references', 4096, 'geom') FROM q WHERE geom IS NOT NULL;
$$;
