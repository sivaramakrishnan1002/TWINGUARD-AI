ALTER TABLE twinguard.flood_labels
    ADD COLUMN IF NOT EXISTS geom_repaired geometry(Geometry,32644),
    ADD COLUMN IF NOT EXISTS geometry_valid_after_repair boolean;

UPDATE twinguard.flood_labels
SET geom_repaired = CASE
      WHEN geom IS NULL THEN NULL
      WHEN GeometryType(geom) IN ('POLYGON','MULTIPOLYGON')
        THEN ST_Multi(ST_CollectionExtract(ST_MakeValid(geom),3))::geometry(Geometry,32644)
      ELSE ST_MakeValid(geom)
    END,
    geometry_valid_after_repair = CASE
      WHEN geom IS NULL THEN NULL
      WHEN GeometryType(geom) IN ('POLYGON','MULTIPOLYGON')
        THEN ST_IsValid(ST_Multi(ST_CollectionExtract(ST_MakeValid(geom),3)))
      ELSE ST_IsValid(ST_MakeValid(geom))
    END
WHERE geom IS NOT NULL AND (geom_repaired IS NULL OR geometry_valid_after_repair IS NULL);

CREATE INDEX IF NOT EXISTS flood_labels_repaired_geom_gix
    ON twinguard.flood_labels USING gist (geom_repaired);

CREATE OR REPLACE VIEW twinguard.v_flood_labels AS
SELECT label_id,label_key,label_name,event_date,label_type,confidence_tier,
       is_modelled,is_coarse,is_derived,source_properties,
       geom_repaired AS geom,geometry_valid_after_repair AS is_valid,
       source_id,source_sha256,loader,load_time
FROM twinguard.flood_labels;
