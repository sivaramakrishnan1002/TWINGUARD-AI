# A11 Priority-Zone Scope Change Proposal

**Status: Option B approved by the project owner on 2026-10-28; pending Lane A owner review of revised acceptance and output schema.** This records the scope decision but does not authorize implementation until Lane A confirms the revised task specification.

## Evidence reviewed

- `docs/batches/BATCH_2.md` defines A11 as combining hazard probability, exposure, access loss, and a documented vulnerability proxy with weight sensitivity.
- `docs/DATA_QUALITY_REPORT.md`, `docs/DATA_MANIFEST.csv`, `docs/DATA_LINEAGE.md`, and `docs/handbook/05_Data_Inventory.md` inventory the available sources and limitations.
- `docs/PHASE13_IMPACT_BATCH2_V4.md` documents WorldPop as a population/exposure estimate, with NoData and model-estimate limitations.
- `docs/SHELTER_ALLOCATION_BATCH2.md` documents OSM candidate shelters and assumed capacities; it does not define social or household vulnerability.
- `docs/MANUAL_TODO.md` records census comparison and other source verification as outstanding. No suitable census or social-vulnerability dataset is present in `data/raw/` or the manifest.

The repository therefore does not contain a vulnerability dataset whose source, reference date, licence, geographic coverage, and limitations support the A11 criterion. WorldPop R2025A is a 2021 alpha constrained population model (CC BY 4.0), useful for exposure; it is not a vulnerability measure. Facility/building/road data describe mapped assets or access, not the vulnerability of affected people. No proxy is inferred from these sources.

## Decision

The project owner selected **Option B — proxy-free descriptive scope**:

- Produce side-by-side, scenario-labelled hazard, population-exposure, and facility-access-loss layers/summaries.
- Preserve each layer's own units, provenance, coverage, uncertainty, assumptions, and NoData.
- Do not combine the layers into a composite score or ranking; do not call locations or populations “vulnerable”; do not label results as official priority zones.
- Any later weighting or ranking requires a separately approved method and evidence.

The project owner approval does not substitute for Lane A's review of the revised acceptance criteria, output/schema, tests, and limitations. A11 remains blocked until that review is recorded.

## Next step

Lane A owner: review and acknowledge the revised scope, acceptance, output paths/schema, tests, and limitations in the Lane A task process. The Integrator may then remove the remaining review prerequisite and set A11 ready after rechecking dependencies and output conflicts. Until then, A11 and dependent A13 remain blocked. No implementation or output changes are made by this scope-decision record.
