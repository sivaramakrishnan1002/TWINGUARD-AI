-- OpenCity's observed-point resources identify the 2015 flood year but do not
-- supply an exact observation day. Preserve the year in source provenance only.
UPDATE twinguard.flood_labels
SET event_date = NULL
WHERE label_type = 'OBSERVED'
  AND source_id IN (
    'opencity_814ca028-4c84-4bd0-aa67-6dbaeb9b6ba5',
    'opencity_93d2905a-a580-482d-96b0-4d9ccf5273ef'
  );
