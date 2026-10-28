# A11 — proxy-free descriptive scenario outputs

**Status:** complete with caveats; derived research exports only.
**Output version:** `data/features/decision/priority_zones/batch2_v1/revision_2/`
**Run label:** `twinguard.a11_proxy_free_outputs` schema 1.0; generated 2026-10-28 06:34:26 UTC.
**Reproduction:** `.venv\Scripts\python.exe pipelines\decision\a11_proxy_free_outputs.py --output-dir data\features\decision\priority_zones\batch2_v1\revision_2`; verify with the same command plus `--verify-only`.

## What was produced

Three indicators are kept separate. No vulnerability proxy, composite score, weights, rank, rank stability, or official priority designation was created.

| Product | Files and records | Meaning and units |
|---|---|---|
| Hazard | `hazard_cells.parquet` (182,250 rows: 75 cases × 2,430 cells) and 75 five-band GeoTIFFs | A07's simulated mean depth and descriptive member p05/p95 in metres, A07 passability probability, its complement (`flood_screen_probability`, the member fraction at/above the default 0.30 m screen), and valid member count. NoData is outside the eligible model grid or unassessed, not dry. |
| Population exposure | `population_exposure_summary.parquet` (75 case rows) | A07's known exposed WorldPop model estimate in people, with source coverage and NoData counts retained separately. Every case is marked `PARTIAL`; 96,254 source 30 m population cells are NoData and population coverage is 0.8986005. This is exposure, not vulnerability or a census count. |
| Facility access loss | `facility_access_loss_summary.parquet` (225 rows: 75 cases × hospital, shelter, candidate_shelter) | A07's separate category counts, access-loss fraction and coverage; counts remain counts and fractions remain fractions. Per-category unassessed counts and ensemble spread are retained. |
| Capacity-allocation context | `capacity_allocation_context.parquet` (540 A10 cases) | A10's scenario/member/capacity-factor allocation outputs remain a separate table; not merged into access loss. Capacity factors 0.5, 1.0 and 2.0 are sensitivity assumptions. Schools and colleges are candidate shelters by assumption. |
| Provenance and validation | `run_manifest.json` | Grid, event/time keys, source hashes, output hashes and byte sizes, row counts, indicator semantics and caveats. |

All hazard exports use the existing model grid, 88 rows × 69 columns, EPSG:32644, 600 m pixels, transform `[600, 0, 390000, 0, -600, 1471620]`, and `-9999` NoData. The 75 cases cover three registered event windows (2015-12-02, 2021-11-13, 2023-12-04), five A05 scenarios (`perfect_foresight_imerg`, `persistence_previous_day`, `rain_error_q10`, `rain_error_q50`, `rain_error_q90`) and saved horizons 6, 12, 24, 48 and 72 hours. Valid times are copied from A07 in UTC; no intermediate timestamps were generated.

The A07 default 0.30 m exposure/access screen is an assumption, not a locally validated danger, closure or facility-access threshold. The passability complement is a share of the A07 ensemble below/above that screen, not calibrated probability of real-world flooding. A07's member percentiles are descriptive scenario/member spread, not calibrated confidence intervals.

## Coverage and interpretation

- A07 provides 2,430 eligible model cells per case. Each exported case has 2,430 cell rows; the 600 m grid does not provide street-scale detail.
- Population exposure is known-data exposure only. Its 96,254 WorldPop NoData cells remain explicitly flagged; a reported known-data value of zero does not mean complete zero exposure.
- A07 facility access is a coarse connected-component cascade, not direction-aware origin-destination routing, travel time, facility operations, or a safe-access determination. Coverage is incomplete for mapped targets; the per-row unassessed and coverage fields are retained. In these records category coverage ranges from 0.98996 for hospitals to 1.0 for mapped shelters; candidate shelters average 0.98268. Candidate shelters include schools/colleges and must not be mistaken for verified emergency shelters.
- A10's allocation is simulated greedy allocation using hypothetical capacities. It is not shelter operating capacity, confirmed use, or evacuation guidance; unknown population demand remains unknown.
- A05 hindcasts and scenario contrasts are not operational forecast skill. A06 is an assumption-based 600 m simulation without independent hydraulic validation. Downstream outputs inherit these limitations.
- Outputs are descriptive decision-support simulations only, not live predictions, validated hydraulic truth, vulnerable-population assessments, official priority zones, or emergency advice.

## Source provenance

SHA-256 values copied into the run manifest:

| Source | SHA-256 |
|---|---|
| A07 `cell_impact.parquet` (`batch2_v4_contract`) | `e352ef887867da07084f62eb622d69de8dc6909d4b24d1c190bd6f2ac295e5d0` |
| A07 `impact_results.jsonl` (`batch2_v4_contract`) | `7dbecdcfe12a9761a5fb58859a29f3c4c99171931413416ae3233c460d20d7c2` |
| A07 `run_summary.json` | `8d89cd84cfa822252be368309940e8e2cc2ffe9275f129061859b1f1141e9e0a` |
| A10 `allocation_cases.parquet` (`batch2_v3`) | `3c204884af00ea0fb713b9f72c04f36f21647c7aa9b5b710bc6c98f03220276d` |

## Checks

- Focused deterministic/schema and A10 decision tests: `.venv\Scripts\python.exe -m pytest -q tests\decision\test_a11_proxy_free_outputs.py tests\decision\test_shelter_allocation.py --import-mode=importlib` — **12 passed**.
- Applicable Lane A suite: `.venv\Scripts\python.exe -m pytest -q tests\decision tests\explainability tests\labels tests\phase8 tests\phase9 tests\phase9b tests\phase9c tests\phase10 tests\phase11 tests\phase12 tests\phase13 tests\routing tests\visualization3d --import-mode=importlib` — **127 passed**.
- Output verifier: `.venv\Scripts\python.exe pipelines\decision\a11_proxy_free_outputs.py --output-dir data\features\decision\priority_zones\batch2_v1\revision_2 --verify-only` — **ok**; confirms row counts, forbidden fields, probability/fraction ranges, source NoData semantics, SHA-256/size, GeoTIFF CRS/transform/bands/NoData.
- Raw audit: `.venv\Scripts\python.exe tools\audit_raw_logs.py` — `DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0`.
- GPU check: NVIDIA GeForce RTX 3050 Laptop GPU, driver 566.07; PyTorch 2.14.1+cu126 and CUDA available. GPU not used: this task packages precomputed values and serializes small rasters; there was no substantial numerical workload to accelerate.

An initial export exists at the root of `batch2_v1/` and is preserved unchanged. `revision_2/` is the validated export with explicit population NoData and coverage columns. The root export is superseded for use by this revision; its files were not overwritten or deleted.
