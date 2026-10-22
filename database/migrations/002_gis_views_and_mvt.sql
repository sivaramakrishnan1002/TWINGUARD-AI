CREATE OR REPLACE VIEW twinguard.v_study_area AS
SELECT feature_id, name, boundary_vintage, geom FROM twinguard.study_area;

CREATE OR REPLACE VIEW twinguard.v_roads AS
SELECT feature_id, source_osmid, highway, length_m, speed_kmh, speed_assumed,
       travel_time_min, bridge, tunnel, geom
FROM twinguard.road_edges;

CREATE OR REPLACE VIEW twinguard.v_facilities AS
SELECT feature_id, source_osmid, source_type, category, name,
       nearest_road_distance_m, geom
FROM twinguard.facilities;

CREATE OR REPLACE VIEW twinguard.v_waterways AS
SELECT feature_id, source_osmid, waterway, name, geom FROM twinguard.waterways;

CREATE OR REPLACE VIEW twinguard.v_flood_references AS
SELECT feature_id, source_layer, event_date, reference_role, source_properties, geom
FROM twinguard.flood_references;

CREATE OR REPLACE FUNCTION twinguard.mvt_study_area(z integer, x integer, y integer)
RETURNS bytea LANGUAGE sql STABLE STRICT PARALLEL SAFE AS $$
WITH b AS (SELECT ST_TileEnvelope(z, x, y) AS box), q AS (
  SELECT s.feature_id, s.name, s.boundary_vintage,
         ST_AsMVTGeom(ST_Transform(s.geom, 3857), b.box, 4096, 64, true) AS geom
  FROM twinguard.study_area s CROSS JOIN b
  WHERE z BETWEEN 0 AND 22 AND s.geom && ST_Transform(b.box, 32644)
)
SELECT ST_AsMVT(q, 'study_area', 4096, 'geom') FROM q WHERE geom IS NOT NULL;
$$;

CREATE OR REPLACE FUNCTION twinguard.mvt_roads(z integer, x integer, y integer)
RETURNS bytea LANGUAGE sql STABLE STRICT PARALLEL SAFE AS $$
WITH b AS (SELECT ST_TileEnvelope(z, x, y) AS box), q AS (
  SELECT r.feature_id, r.highway, r.length_m, r.speed_kmh, r.speed_assumed,
         r.bridge, r.tunnel,
         ST_AsMVTGeom(ST_Transform(r.geom, 3857), b.box, 4096, 64, true) AS geom
  FROM twinguard.road_edges r CROSS JOIN b
  WHERE z BETWEEN 0 AND 22 AND r.geom && ST_Transform(b.box, 32644)
)
SELECT ST_AsMVT(q, 'roads', 4096, 'geom') FROM q WHERE geom IS NOT NULL;
$$;

CREATE OR REPLACE FUNCTION twinguard.mvt_facilities(z integer, x integer, y integer)
RETURNS bytea LANGUAGE sql STABLE STRICT PARALLEL SAFE AS $$
WITH b AS (SELECT ST_TileEnvelope(z, x, y) AS box), q AS (
  SELECT f.feature_id, f.category, f.name,
         ST_AsMVTGeom(ST_Transform(f.geom, 3857), b.box, 4096, 64, true) AS geom
  FROM twinguard.facilities f CROSS JOIN b
  WHERE z BETWEEN 0 AND 22 AND f.geom && ST_Transform(b.box, 32644)
)
SELECT ST_AsMVT(q, 'facilities', 4096, 'geom') FROM q WHERE geom IS NOT NULL;
$$;

CREATE OR REPLACE FUNCTION twinguard.mvt_waterways(z integer, x integer, y integer)
RETURNS bytea LANGUAGE sql STABLE STRICT PARALLEL SAFE AS $$
WITH b AS (SELECT ST_TileEnvelope(z, x, y) AS box), q AS (
  SELECT w.feature_id, w.waterway, w.name,
         ST_AsMVTGeom(ST_Transform(w.geom, 3857), b.box, 4096, 64, true) AS geom
  FROM twinguard.waterways w CROSS JOIN b
  WHERE z BETWEEN 0 AND 22 AND w.geom && ST_Transform(b.box, 32644)
)
SELECT ST_AsMVT(q, 'waterways', 4096, 'geom') FROM q WHERE geom IS NOT NULL;
$$;

CREATE OR REPLACE FUNCTION twinguard.mvt_flood_references(z integer, x integer, y integer)
RETURNS bytea LANGUAGE sql STABLE STRICT PARALLEL SAFE AS $$
WITH b AS (SELECT ST_TileEnvelope(z, x, y) AS box), q AS (
  SELECT f.feature_id, f.source_layer, f.event_date, f.reference_role,
         ST_AsMVTGeom(ST_Transform(f.geom, 3857), b.box, 4096, 64, true) AS geom
  FROM twinguard.flood_references f CROSS JOIN b
  WHERE z BETWEEN 0 AND 22 AND f.geom && ST_Transform(b.box, 32644)
)
SELECT ST_AsMVT(q, 'flood_references', 4096, 'geom') FROM q WHERE geom IS NOT NULL;
$$;
