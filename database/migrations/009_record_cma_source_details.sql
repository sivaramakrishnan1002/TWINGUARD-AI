DO $$
BEGIN
    UPDATE twinguard.dataset_catalog
    SET source_layer = 'Chennai/CMA.geojson',
        source_url = 'https://github.com/datameet/Municipal_Spatial_Data',
        retrieval_date = DATE '2026-09-08',
        source_vintage = 'Datameet Municipal_Spatial_Data community dataset; repository file Chennai/CMA.geojson. Filesystem date suggests retrieval around 2026-09-08. Area 1,187.46 km2, consistent with the pre-2022 CMA of about 1,189 km2. Not an official CMDA product; authoritative status and exact source vintage remain unverified.',
        caveat = 'Community boundary from Datameet Municipal_Spatial_Data, Chennai/CMA.geojson; area 1,187.46 km2. Consistent with the pre-2022 CMA of about 1,189 km2. Not an official CMDA product; authoritative status and exact source vintage remain unverified. Existing boundary geometry retained unchanged.'
    WHERE layer_key = 'study_area_older_cma';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Expected boundary catalogue entry study_area_older_cma was not found';
    END IF;
END $$;
