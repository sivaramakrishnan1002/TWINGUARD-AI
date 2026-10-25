# Batch 2 GeoPDF diagnostic lineage

Raw inputs were read-only and no network access or package installation was used.

## Raw source PDFs

- `data/raw/historical_floods/2021/ChennaiCity-ChennaiCorporationTaluk-4.pdf` — SHA-256 `0dc698a81e38eb06bc0731a9cc3338572361353ec97470a4e4d21ec69bd26c71`
- `data/raw/historical_floods/2023/tncyclone50dsc07122023_0600hrs_map.pdf` — SHA-256 `6ffe3ee78b16cce93827c7159276f9073b19a0d80e6c54dc1125b54825f38d0a`
- `data/raw/historical_floods/2023/tnflood50dsc12182023_1800hrs_vap1.pdf` — SHA-256 `7716e2fa7a3b4169368da59a5fa4133d0d6b5b9f02a26647547c30e0e07bf500`

## Derived outputs

- `data/features/labels/map_batch2/nrsc_2023_dec07_preliminary_red_class_native_geopdf.tif` — 109,185 bytes; SHA-256 `aa0bafc374ec0c7d30d233b45e6acedf4a24d2a55d86d21cfa50ecc7f49d9627`
- `data/features/labels/map_batch2/nrsc_2023_dec07_preliminary_red_class.gpkg` — 5,832,704 bytes; SHA-256 `5f204651f2957144277f76906ac2a7c957ee21e7b928d854f6e12f01f6459165`
- `data/features/labels/map_batch2/nrsc_2023_dec07_diagnostic.json` — 1,592 bytes; SHA-256 `23553e993f3df3410fbae75342d285772226498deb846d81dd030b19ed247375`
- `docs/GEO_PDF_LABELS_BATCH2.md` — 2,234 bytes; SHA-256 `20b826115ac9942532a4216749260066ae5c4fa18dd3007c15f52325a7c32724`
- `docs/PHASE9C_OUT_OF_EVENT_2023.md` — 1,240 bytes; SHA-256 `6defe9d199422429ac81a7f50a6efd6a096a53e43ecaa7e7a45cb628a1e07a48`
- `docs/figures/nrsc_2023_dec07_geopdf_overlay.png` — 203,522 bytes; SHA-256 `9d70692fd6138b2bd65565afe9c1c86ac72b468b3a3920592b8f70480dd7880c`
- `pipelines/labels/pdf_map_batch2.py` — 13,042 bytes; SHA-256 `14371f1616ff1121bcb8794387b8dacb69915841d2feda373bae7625df91b007`
- `tests/labels/test_pdf_map_batch2.py` — 295 bytes; SHA-256 `8521b09015731aa5983504784f653a232df3d06030629a4c636ed9075f748994`

The extracted embedded images and viewport metadata are listed in `data/processed/pdf_maps/batch2/pdf_inspection.json`. 2023 raster/vector remain preliminary and unaccepted; no rows were loaded into the database.
