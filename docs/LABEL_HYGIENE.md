# Stage 8 label hygiene

Batch 1 T1 moved the four earlier Stage 8 SAR candidate variants (24 Nov 2015 has two candidate methods; 6 Dec 2015 and 16 Nov 2021 each have one) to tier D with status `REJECTED_PENDING_REWORK`. The 2023 Michaung PDF/map record remains tier D. Existing geometries and metrics are retained for audit; none of these candidate polygons is eligible for training, validation, routing or impact analysis.

The database view `labels.v_usable_flood_labels` exposes valid in-CMA official UNOSAT references as tier A and only explicitly accepted valid in-CMA derived rows at tiers B/C. It includes baseline-water references with `reference_role=baseline_water`; consumers must select `event_flood` when constructing event labels. It does not make a source field-validated ground truth.

The database currently contains 45,096 Stage 8 SAR candidate polygons: 17,547 dated 24 Nov 2015, 11,763 dated 6 Dec 2015, and 15,786 dated 16 Nov 2021. They are retained as tier D / `REJECTED_PENDING_REWORK`. The view currently exposes only the official UNOSAT references; no SAR-derived candidate has passed the revised method.

Migration: `database/migrations/014_stage8_label_hygiene.sql`. The local feature registry at `data/features/labels/label_registry.json` is updated in place; generated data and registries are not committed.
