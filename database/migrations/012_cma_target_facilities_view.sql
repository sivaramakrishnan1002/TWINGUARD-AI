CREATE OR REPLACE VIEW twinguard.v_cma_target_facilities AS
SELECT feature_id,
       source_osmid,
       source_type,
       category,
       name,
       nearest_road_distance_m,
       geom,
       in_cma
FROM twinguard.facilities
WHERE in_cma
  AND category IN (
      'hospital',
      'clinic',
      'school',
      'college',
      'shelter',
      'fire_station',
      'police'
  );

COMMENT ON VIEW twinguard.v_cma_target_facilities IS
    'CMA-intersecting facilities limited to hospital, clinic, school, college, shelter, fire_station and police categories.';
