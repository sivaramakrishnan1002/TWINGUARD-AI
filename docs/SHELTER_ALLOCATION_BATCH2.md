# A10 — Shelter allocation (Batch 2)

## Result and interpretation

This is a **simulated research allocation**, not evacuation guidance or a claim about currently operating shelters. The final run is in `data/features/decision/shelters/batch2_v3/`. Earlier `batch2_v1/` and `batch2_v2/` runs are retained and have not been overwritten. v3 fixes a double-counting ambiguity found during review: total unserved demand equals unserved demand in components containing candidates plus demand in components with no usable candidate.

The allocation uses the 600 m, EPSG:32644 active simulation grid (2,430 cells), the 508,854-node / 1,071,656-directed-arc OSM graph and A08 states for 2015-12-02, 2021-11-13 and 2023-12-04. Each event uses the `perfect_foresight_imerg` scenario at 6, 24 and 72 hours, across all 20 A08 members and three capacity factors (0.5, 1 and 2), for 540 cases. Snapshot valid times are stored as UTC in the case table.

OSM candidates inside the active grid: 102 `shelter`, 559 `school`, and 134 `college` features. Treating schools and colleges as shelter candidates is an assumption. Default hypothetical capacities are 100 people per shelter, 250 per school and 500 per college; no actual capacity or operational status was verified. Candidate capacity totals are 108,475, 216,950 and 433,900 people at factors 0.5, 1 and 2.

## Sensitivity summary

Means over 180 event/time/member cases per capacity factor:

| Capacity factor | Assumed capacity | Mean known WorldPop demand | Mean served | Mean total unserved | Mean unreachable component demand |
|---:|---:|---:|---:|---:|---:|
| 0.5 | 108,475 | 4,836,739.34 | 68,546.65 | 4,768,192.69 | 1,733,133.92 |
| 1.0 | 216,950 | 4,836,739.34 | 136,975.33 | 4,699,764.01 | 1,733,133.92 |
| 2.0 | 433,900 | 4,836,739.34 | 273,757.83 | 4,562,981.51 | 1,733,133.92 |

For default factor 1, means across 20 members are:

| Event key | Horizon | Served | Total unserved | Unserved in components with candidates | No usable candidate in component |
|---|---:|---:|---:|---:|---:|
| 2015-12-02 | 6 h | 138,137.42 | 4,698,601.92 | 2,982,585.26 | 1,716,016.66 |
| 2015-12-02 | 24 h | 136,724.92 | 4,700,014.42 | 2,969,674.51 | 1,730,339.91 |
| 2015-12-02 | 72 h | 134,286.74 | 4,702,452.60 | 2,922,117.22 | 1,780,335.38 |
| 2021-11-13 | 6 h | 138,137.42 | 4,698,601.92 | 2,982,585.26 | 1,716,016.66 |
| 2021-11-13 | 24 h | 137,999.92 | 4,698,739.42 | 2,982,545.39 | 1,716,194.03 |
| 2021-11-13 | 72 h | 138,012.42 | 4,698,726.92 | 2,982,577.23 | 1,716,149.69 |
| 2023-12-04 | 6 h | 138,137.42 | 4,698,601.92 | 2,982,585.26 | 1,716,016.66 |
| 2023-12-04 | 24 h | 137,949.92 | 4,698,789.42 | 2,982,661.90 | 1,716,127.52 |
| 2023-12-04 | 72 h | 133,391.74 | 4,703,347.60 | 2,912,338.80 | 1,791,008.80 |

WorldPop contributes 4,836,739.34 people as a model estimate over this modeled domain. 853,001 source 30 m cells were mapped as known population and 96,254 as NoData. The seven demand cells with no known source population remain flagged as unknown in every case; they are not counted as zero demand.

## Method, checks, and limitations

Each candidate and each active 600 m population-grid centre is snapped to its nearest road node. Median/p95/maximum snap distances are 32.67/72.84/143.55 m for candidates and 32.78/222.40/679.64 m for demand centres. For each case, only A08 open or reduced arcs define weakly connected components; blocked, unknown, unassessed and bridge-unassessed arcs do not connect components. Demand is greedily assigned to candidate capacity within each weak component in increasing planar distance between snapped nodes. This is not direction-aware pathfinding or travel-time accessibility.

The capacity factors are sensitivity assumptions, not evidence about facility capacities. The algorithm does not verify shelter access, facilities' actual use as emergency shelters, population willingness or mobility, or within-cell population distribution. A05/A06/A08 inputs are hindcasts/simulation products. Results are not live routing, safe evacuation advice, operational capacity, or validated impact estimates.

The v3 verifier checks 540 cases, capacity limits, served + total unserved = known demand, reachable-unserved + unreachable-component demand = total unserved, detail-row reconciliation, simulation labels, and the NoData flag. Focused tests cover allocation/capacity, unserved versus unreachable demand, no-candidate behavior and NoData preservation. The broader applicable Lane A suite passed all 113 tests.

## Provenance and commands

Final v3 files (generated locally and not committed):

| File | Bytes | SHA-256 |
|---|---:|---|
| `allocation_cases.csv` | 236,426 | `80ccb92e8010695236a684cdeb0b0c95579cbdb2e2f2704e0cb8afa49dd89338` |
| `allocation_cases.parquet` | 22,491 | `3c204884af00ea0fb713b9f72c04f36f21647c7aa9b5b710bc6c98f03220276d` |
| `allocation_detail.parquet` | 445,353 | `7c9b5e263e6d0201933ae9e4033e345010178af03f1619b9fb66edf7f6925d97` |
| `candidate_facilities.parquet` | 42,331 | `7af8330922a5f0b8e14722f3dd426f1b0290104805e3ff59b7d861e0f1b58171` |
| `run_summary.json` | 2,456 | `ed0f2a2773d26282644b1f4ae7e93c4f16cdc37975bc9f3990644a9f2c75563c` |

The run summary records hashes for the OSM feature package, A08 run summary and directed arcs, static cell table, and A05 forecast summary. Run seed: `20261028`; v3 compute runtime: 228.003 s on CPU.

```powershell
.venv\Scripts\python.exe pipelines\decision\shelter_allocation.py
.venv\Scripts\python.exe pipelines\decision\shelter_allocation.py --verify-only
.venv\Scripts\python.exe -m pytest -q tests\decision\test_shelter_allocation.py --import-mode=importlib
.venv\Scripts\python.exe tools\audit_raw_logs.py
```

Focused tests: 3 passed. Output verifier: 540 cases, 293,374 allocation-detail rows; capacity, accounting reconciliation, simulation and NoData checks passed. Full applicable Lane A tests: 113 passed. Raw audit: `DATA_FILES=157; DATA_BYTES=30544672450; HASH_MATCH=157; NO_COMPARABLE_HASH=0; MISMATCH=0`. GPU was not used: `nvidia-smi` reported insufficient permissions and the installed PyTorch build reported CUDA unavailable. No packages or network were used.

State note: the task record registered `batch2_v1/`; that folder was preserved, and the final corrected run is `batch2_v3/`. The Integrator should reconcile the registered output path to the final version when updating the master task record.
