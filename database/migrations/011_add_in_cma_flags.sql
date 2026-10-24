DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM twinguard.study_area WHERE ST_SRID(geom) <> 32644) THEN
        RAISE EXCEPTION 'CMA study_area geometry must be EPSG:32644';
    END IF;
END $$;

ALTER TABLE twinguard.road_edges ADD COLUMN IF NOT EXISTS in_cma boolean NOT NULL DEFAULT false;
ALTER TABLE twinguard.road_nodes ADD COLUMN IF NOT EXISTS in_cma boolean NOT NULL DEFAULT false;
ALTER TABLE twinguard.facilities ADD COLUMN IF NOT EXISTS in_cma boolean NOT NULL DEFAULT false;
ALTER TABLE twinguard.waterways ADD COLUMN IF NOT EXISTS in_cma boolean NOT NULL DEFAULT false;
ALTER TABLE twinguard.building_footprints ADD COLUMN IF NOT EXISTS in_cma boolean NOT NULL DEFAULT false;

UPDATE twinguard.road_edges AS t
SET in_cma = (t.geom && s.geom AND ST_Intersects(t.geom, s.geom))
FROM twinguard.study_area AS s;
UPDATE twinguard.road_nodes AS t
SET in_cma = (t.geom && s.geom AND ST_Intersects(t.geom, s.geom))
FROM twinguard.study_area AS s;
UPDATE twinguard.facilities AS t
SET in_cma = (t.geom && s.geom AND ST_Intersects(t.geom, s.geom))
FROM twinguard.study_area AS s;
UPDATE twinguard.waterways AS t
SET in_cma = (t.geom && s.geom AND ST_Intersects(t.geom, s.geom))
FROM twinguard.study_area AS s;
UPDATE twinguard.building_footprints AS t
SET in_cma = (t.geom && s.geom AND ST_Intersects(t.geom, s.geom))
FROM twinguard.study_area AS s;

CREATE INDEX IF NOT EXISTS road_edges_in_cma_idx ON twinguard.road_edges(in_cma);
CREATE INDEX IF NOT EXISTS road_nodes_in_cma_idx ON twinguard.road_nodes(in_cma);
CREATE INDEX IF NOT EXISTS facilities_in_cma_idx ON twinguard.facilities(in_cma);
CREATE INDEX IF NOT EXISTS waterways_in_cma_idx ON twinguard.waterways(in_cma);
CREATE INDEX IF NOT EXISTS building_footprints_in_cma_idx ON twinguard.building_footprints(in_cma);

CREATE OR REPLACE VIEW twinguard.v_roads AS
SELECT feature_id, source_osmid, highway, length_m, speed_kmh, speed_assumed,
       travel_time_min, bridge, tunnel, geom, in_cma
FROM twinguard.road_edges;

CREATE OR REPLACE VIEW twinguard.v_facilities AS
SELECT feature_id, source_osmid, source_type, category, name,
       nearest_road_distance_m, geom, in_cma
FROM twinguard.facilities;

CREATE OR REPLACE VIEW twinguard.v_waterways AS
SELECT feature_id, source_osmid, waterway, name, geom, in_cma
FROM twinguard.waterways;

CREATE OR REPLACE VIEW twinguard.v_buildings AS
SELECT feature_id, source_osmid, building, name, geom, in_cma
FROM twinguard.building_footprints;

CREATE OR REPLACE FUNCTION twinguard.mvt_roads(z integer, x integer, y integer)
RETURNS bytea LANGUAGE sql STABLE STRICT PARALLEL SAFE AS $$
WITH b AS (SELECT ST_TileEnvelope(z, x, y) AS box), q AS (
  SELECT r.feature_id, r.highway, r.length_m, r.speed_kmh, r.speed_assumed,
         r.bridge, r.tunnel, r.in_cma,
         ST_AsMVTGeom(ST_Transform(r.geom, 3857), b.box, 4096, 64, true) AS geom
  FROM twinguard.road_edges r CROSS JOIN b
  WHERE z BETWEEN 0 AND 22 AND r.geom && ST_Transform(b.box, 32644)
)
SELECT ST_AsMVT(q, 'roads', 4096, 'geom') FROM q WHERE geom IS NOT NULL;
$$;

CREATE OR REPLACE FUNCTION twinguard.mvt_facilities(z integer, x integer, y integer)
RETURNS bytea LANGUAGE sql STABLE STRICT PARALLEL SAFE AS $$
WITH b AS (SELECT ST_TileEnvelope(z, x, y) AS box), q AS (
  SELECT f.feature_id, f.category, f.name, f.in_cma,
         ST_AsMVTGeom(ST_Transform(f.geom, 3857), b.box, 4096, 64, true) AS geom
  FROM twinguard.facilities f CROSS JOIN b
  WHERE z BETWEEN 0 AND 22 AND f.geom && ST_Transform(b.box, 32644)
)
SELECT ST_AsMVT(q, 'facilities', 4096, 'geom') FROM q WHERE geom IS NOT NULL;
$$;

CREATE OR REPLACE FUNCTION twinguard.mvt_waterways(z integer, x integer, y integer)
RETURNS bytea LANGUAGE sql STABLE STRICT PARALLEL SAFE AS $$
WITH b AS (SELECT ST_TileEnvelope(z, x, y) AS box), q AS (
  SELECT w.feature_id, w.waterway, w.name, w.in_cma,
         ST_AsMVTGeom(ST_Transform(w.geom, 3857), b.box, 4096, 64, true) AS geom
  FROM twinguard.waterways w CROSS JOIN b
  WHERE z BETWEEN 0 AND 22 AND w.geom && ST_Transform(b.box, 32644)
)
SELECT ST_AsMVT(q, 'waterways', 4096, 'geom') FROM q WHERE geom IS NOT NULL;
$$;
