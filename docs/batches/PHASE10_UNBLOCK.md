# Lane A CR-003: label strategy V2 and Phase 10 unblock

**Owner:** Lane A. **Raw data:** read-only. **Network/downloads/installs:** none. **Commit scope:** Lane A paths only; never stage Track B files.

## Tasks and time boxes

### A03b — SAR diagnostic, label strategy, and map preparation

- **L1 (30 minutes compute; no IoU chasing):** For 24 Nov 2015 compare VV, VH and dB-change inside UNOSAT flood pixels with non-flood pixels matched by land cover and HAND bin. Report per-variable AUC and a small spatial-block decision stump. Shift the label 1–3 cells and report overlap; check image/label alignment using permanent water. Conclude whether simple scene rules separate the UNOSAT extent. An AUC ≥0.7 is a diagnostic only; it does not create an accepted label.
- **L2:** Write `docs/LABEL_STRATEGY_V2.md`: UNOSAT November 2015 is Tier A training label; SAR candidates remain Tier D and excluded from training and `labels.v_usable_flood_labels`. Rank validation sources as OpenCity points (unclear dates), Global Flood Database event 4309 (coarse, 10 Nov–4 Dec 2015), then future digitised official maps (Tier B/C according to georeferencing error); explain what each can and cannot validate.
- **L3 (120 minutes):** For the 2021 NRSC PDF, 2023 NDEM PDF and any December 2015 maps present, inspect GeoPDF metadata read-only, extract embedded images at native resolution to `data/processed/pdf_maps/`, inspect graticule ticks and legend colors, and report automatic georeferencing feasibility. Write `docs/GEOREFERENCING_GUIDE.md` with 8–10 candidate control points per present map, EPSG:4326 and EPSG:32644 coordinates from database/OSM, transform, acceptable RMS, polygonization, QA and expected digitising time. Create an empty `data/processed/labels_manual/digitised_labels.gpkg` template and a tested loader that validates geometry and writes Tier B at RMSE ≤ one grid cell, Tier C above, with `DERIVED-FROM-MAP` provenance. Missing December files stay pending. Do not digitise or invent map content.

### A03c — depth uncertainty scenarios

- **L5 (60 minutes):** Create new depth outputs for relative-error and ±4 m absolute-error scenarios. Numerically test with spatially correlated DEM error whether a common absolute offset cancels in the water-surface-minus-DEM method. Create class probabilities for <0.15, 0.15–0.3, 0.3–0.5, and >0.5 m. Keep NoData as NoData and include a coverage mask. These are calibration proxies, not routing inputs. Never overwrite the T6 depth outputs.

### A03 — Phase 10 without out-of-event validation

- **L4 (90 minutes):** Build a single-event, apparent risk map from Phase 9B and Phase 9C where present. Include calibrated classes with stated cut-points, uncertainty, and urban-unreliability layers; population (preserve NoData), facilities and road-length zonal statistics by class and 3 km block; PNG, GeoTIFF, vector tiles, and OpenCity point hit rate by risk percentile. Out-of-event validation must read “pending digitised labels.” Do not imply external validation.

## Completion gates

- Tests, raw audit, lineage and concise reports for each task.
- Update `docs/master/STATE.json`, `CHANGELOG.md`, `NEXT.md`, and `docs/DECISIONS_PENDING.md` under the master protocol; keep those Integrator-owned changes out of the Lane A commit.
- A04b Phase 9C is already complete with caveats; verify its current artifacts and do not repeat it.
