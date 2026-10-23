-- Remove only the incomplete one-row IMERG observation import made by the
-- initial version of load_stage5_complementary.py, then allow the corrected
-- idempotent loader to ingest the complete daily series.
DELETE FROM twinguard.observation_records
WHERE source_id = 'stage5_obs_imerg_daily';
DELETE FROM twinguard.dataset_catalog
WHERE layer_key = 'stage5_obs_imerg_daily';
