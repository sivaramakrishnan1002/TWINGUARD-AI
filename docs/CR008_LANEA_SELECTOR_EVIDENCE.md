# CR-008 Lane A artifact-selector evidence

**Purpose:** read-only confirmation of selector fields in the authoritative saved A07 and A09 outputs. This note does not approve or freeze API behavior, change any result, or revise C4/C7/C8.

## A07 impact records

Authoritative result file: `data/features/impact/batch2_v4_contract/impact_results.jsonl` (75 JSONL records; SHA-256 `7dbecdcfe12a9761a5fb58859a29f3c4c99171931413416ae3233c460d20d7c2`).

- `scenario_key` is present in every inspected record. It identifies the named A05 rainfall/hindcast scenario attached to this impact result, not a new A07 run. The five exact values are `perfect_foresight_imerg`, `rain_error_q10`, `rain_error_q50`, `rain_error_q90`, and `persistence_previous_day`.
- All records use `run_id=7004`; there are 15 distinct `valid_at_utc` values. Each `(run_id, valid_at_utc)` group contains exactly five records with five distinct `scenario_key` values. The full `(run_id, valid_at_utc, scenario_key)` key is unique for all 75 records. This makes `scenario_key` a sufficient disambiguator within the saved A07 run and valid-time groups.
- The records identify simulated, coarse 600 m EPSG:32644 impact summaries. Scenario selection resolves a saved hindcast/simulation result; it does not turn the result into an operational forecast or independently validated impact estimate.
- Each record carries `provenance` including `algorithm`, `algorithm_version`, `code_commit`, `grid` CRS/resolution, `parameters`, and `sources` with source IDs, versions, and SHA-256 hashes. The record also carries event UTC bounds, `generated_at_utc`, `run_version`, `source_mode`, uncertainty, coverage, and QC fields.

## A09 route records

Authoritative final route file: `data/features/routing/results/batch2_v1/revision_3/route_results.jsonl` (216 JSONL records; SHA-256 `ee4e33b45268ba869cfc0f3f48eee1c10ac2c5ae83837b1d82165c6ca6c2ea7f`). Its sibling `summary.json` has SHA-256 `3d0784a481aaaf451456e9e9f1bb1291461bb0a3680b6cc7019335d0501adc3b`.

- `result_id` is present and non-null in all 216 records; all 216 IDs are unique in revision 3. The saved identifiers follow the code template `A09-{event}-{horizon:02d}h-{method}-od{pair_index+1:02d}` in `pipelines/routing/phase15_routing.py`.
- In this saved revision the ID is stable as a lookup key for its row. Its construction is deterministic for a fixed event, horizon, method, and seeded OD-pair ordering (seed `20261027`, recorded in the sibling summary). It is **not a globally versioned content identifier**: the ID does not encode an artifact revision, run ID, or input hash, and the `odNN` component refers to the sampled pair's position. Consumers must scope lookup to the registered revision 3 file/run context; a future regenerated output could reuse an ID for a changed row if the same tuple/order were reused.
- Per-record identity/provenance fields include `scenario_key`, UTC departure and arrival, `requested_horizon_seconds`, method, travel mode, origin/destination IDs, and `result_id`. The `provenance` object identifies algorithm/version, generating code commit, generation time, and parameters (including seed, forecast-member IDs and hidden simulated-member ID). `graph` identifies graph ID/hash/version, CRS, edge source and build information. `hazard_run` records the simulated hindcast version, nullable run ID, issue/valid window, depth source ID/hash, and ensemble ID.
- All 216 route records have `run_id=null`, and all nested `hazard_run.run_id` values are null. The revision 3 `summary.json` and `comparison_metrics.csv` contain no run-ID mapping or mapping field; the authoritative A09 output directory contains no evidenced mapping from these route records to an integer route run. I found no mapping and did not infer one from filenames or timestamps.

## API exposure limits

- A07 has a direct saved-result selector candidate: the exact tuple `(run_id, valid_at_utc, scenario_key)`. The current frozen request shape lacks the scenario selector, so its current keys can match five A07 records. The route-result ID evidence supports only exact lookup within the registered revision 3 artifact; it does not provide the integer `run_id` required by the current route-computation request.
- Therefore A09 `result_id` can support a separately approved read-only saved-result lookup, but does not justify enabling or fabricating a `POST /route` run mapping. A07 scenario selection likewise requires the appropriate separately approved request semantics. Preserve unavailable/501 behavior until the authorized contract/API process resolves those selectors.
- A09 is explicitly simulated and has incomplete assessed-edge coverage; missing or structurally unassessed edge data remain unknown. A topological route is not evidence of flood accessibility, safety, live routing, or validated real-world performance. A07/A09 records also retain draft result-schema versions and the frozen-contract/API mismatch described in CR-008.

## Read-only checks performed

Commands/check logic (project venv; no output or contract writes):

1. `.venv\Scripts\python.exe tools\master\verify_state.py` — exit 0; no state-integrity failure reported.
2. `.venv\Scripts\python.exe tools\master\next_task.py --lane A` — no ready Lane A task was offered. CR-008 asks Lane A for evidence confirmation but is not itself a registered claimable task; no task status was edited or claimed.
3. Python JSONL checks read both authoritative result files and checked schemas, row counts, IDs, nulls, scenario cardinalities, per-group uniqueness, source mode and file SHA-256 values stated above. Result: A07 75/75 unique selector tuples and five scenarios per each of 15 run/time groups; A09 216/216 unique non-null result IDs and 216/216 null `run_id` values.
4. Read-only inspection of A09 `summary.json`, `comparison_metrics.csv`, and the result-generation code confirmed no run mapping and the `result_id` construction/provenance fields. No tests or processing pipeline were run because this confirmation is limited to saved-output schema/evidence.

No outputs, contracts, OpenAPI files, B08 implementation, or master-state files were changed.
