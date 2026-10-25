-- Batch 1 T1: retain Stage 8 SAR candidates but prevent accidental use.
ALTER TABLE labels.derived_flood_polygons
    DROP CONSTRAINT IF EXISTS derived_flood_polygons_tier_check;
ALTER TABLE labels.derived_flood_polygons
    ADD CONSTRAINT derived_flood_polygons_tier_check
    CHECK (tier = ANY (ARRAY['A','B','C','D']::text[]));

ALTER TABLE labels.derived_flood_polygons
    ADD COLUMN IF NOT EXISTS review_status text;

UPDATE labels.derived_flood_polygons
SET tier = 'D', review_status = 'REJECTED_PENDING_REWORK'
WHERE event_date IN (DATE '2015-11-24', DATE '2015-12-06', DATE '2021-11-16');

ALTER TABLE labels.derived_flood_polygons
    ALTER COLUMN review_status SET DEFAULT 'REJECTED_PENDING_REWORK';
UPDATE labels.derived_flood_polygons
SET review_status = 'REJECTED_PENDING_REWORK'
WHERE review_status IS NULL;
ALTER TABLE labels.derived_flood_polygons
    ALTER COLUMN review_status SET NOT NULL;

CREATE OR REPLACE VIEW labels.v_usable_flood_labels AS
SELECT
    'official:' || fr.feature_id::text AS label_key,
    fr.event_date,
    fr.source_layer AS method,
    fr.reference_role,
    'A'::text AS tier,
    false AS is_derived,
    COALESCE(fr.is_valid, ST_IsValid(COALESCE(fr.geom_repaired, fr.geom))) AS is_valid,
    ST_Intersects(COALESCE(fr.geom_repaired, fr.geom), sa.geom) AS in_cma,
    COALESCE(fr.geom_repaired, fr.geom) AS geom,
    fr.source_id,
    fr.source_sha256,
    fr.loader,
    fr.load_time
FROM twinguard.flood_references AS fr
CROSS JOIN twinguard.study_area AS sa
WHERE fr.reference_role IN ('event_flood', 'baseline_water')
  AND COALESCE(fr.is_valid, ST_IsValid(COALESCE(fr.geom_repaired, fr.geom)))
  AND ST_Intersects(COALESCE(fr.geom_repaired, fr.geom), sa.geom)
UNION ALL
SELECT
    dp.label_key,
    dp.event_date,
    dp.method,
    'event_flood'::text AS reference_role,
    dp.tier,
    dp.is_derived,
    dp.is_valid,
    dp.in_cma,
    dp.geom,
    dp.source_id,
    dp.source_sha256,
    dp.loader,
    dp.load_time
FROM labels.derived_flood_polygons AS dp
WHERE dp.tier IN ('A','B','C')
  AND dp.review_status = 'ACCEPTED'
  AND dp.is_valid
  AND dp.in_cma;

COMMENT ON VIEW labels.v_usable_flood_labels IS
'Accepted tier A/B/C flood and baseline-water references only. Tier D/rejected candidates are excluded. Not field ground truth.';
