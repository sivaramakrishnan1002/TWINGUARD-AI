ALTER TABLE twinguard.dataset_catalog
    ADD COLUMN IF NOT EXISTS licence_note text NOT NULL DEFAULT 'Not yet recorded';

UPDATE twinguard.dataset_catalog
SET licence_note = CASE
    WHEN layer_key IN ('vehicle_road_edges', 'osm_facilities', 'osm_waterways')
      THEN 'OpenStreetMap-derived; ODbL attribution and share-alike obligations apply; see project records.'
    WHEN layer_key = 'study_area_older_cma'
      THEN 'Source terms not independently confirmed; see DATA_MANIFEST.csv.'
    ELSE 'Source terms/licence not independently confirmed; see source metadata.'
END
WHERE licence_note = 'Not yet recorded';
