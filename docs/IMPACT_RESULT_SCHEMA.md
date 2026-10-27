# Impact result schema — Lane A G0 repair proposal

**Status:** implementable Lane A proposal, not a frozen contract, not a database migration, and not a claim that A07 results exist. Version label `impact-result-v0.1-draft` is local to this proposal; the shared C7 registry/version remains unchanged until integrator review.

## Record and time model

The wire format is UTF-8 JSON. One result document represents one `run_id × event_key × scenario_key × valid_at_utc` aggregate across one named ensemble (or one deterministic member). A document can contain several named result metrics. A persisted implementation can store one document per row in JSONB with primary key `(run_id,event_key,scenario_key,valid_at_utc)`; member-level diagnostics, if retained, are separate rows keyed by `ensemble_member_id` and are not mixed into the summary record.

All `*_utc` timestamp fields are RFC 3339 date-times with an explicit UTC offset and are serialized normalized with `Z`. `event_start_utc` and `event_end_utc` describe the requested/source event window, not independently verified flood onset. `valid_at_utc` is the hazard state's instant. `aggregation_interval` is half-open `[start_utc,end_utc)` and describes the data interval summarized. `generated_at_utc` is processing time. An uncertain or date-only event window remains date-only/unknown in provenance; do not invent a clock time.

## Field contract

| Field | Type / units | Meaning and null rule |
|---|---|---|
| `schema_id`, `schema_version` | strings | Fixed identifiers for this draft. |
| `result_id`, `run_id`, `run_version` | string, integer, string | Stable result identity and the exact simulation/forecast run reference. |
| `source_mode` | enum `OBSERVED`, `DERIVED`, `SIMULATED`, `ASSUMPTION`, `REPLAY` | Must accurately characterize this result. Phase 12/11 results use `SIMULATED`; this does not mean live conditions. |
| `event` | object | `event_key`, nullable offset-aware `event_start_utc` and `event_end_utc`, and required `time_basis="UTC"`. Null window endpoints mean source timing is unknown, not zero duration. |
| `valid_at_utc`, `aggregation_interval`, `generated_at_utc` | date-time/object/date-time | State instant, half-open aggregation period, and processing instant, respectively. |
| `thresholds` | object | Required `road_block_depth_m` (default `0.30` is an assumption, sensitivity values `0.15–0.50` m) and configured `population_exposure_depth_m` / `facility_exposure_depth_m`. Thresholds are metres of predicted depth, not observations. If exposure thresholds are not configured, those metric summaries are unavailable/null. |
| `metrics.population_exposed_people` | distribution object or null | Estimated people represented by the selected WorldPop grid cells meeting the configured depth criterion. Units are people; fractional values are allowed because raster estimates and ensemble expectations may be fractional. Never label as census count. |
| `metrics.affected_facilities_count` | distribution object or null | Count of mapped facilities meeting the explicitly named facility exposure criterion; unit facilities. It is not an operational availability count. |
| `metrics.affected_road_length_m` | distribution object or null | Sum of affected graph-edge length; unit metres. Only measured over reported edge coverage. |
| `metrics.facility_access_loss_fraction` | distribution object or null | Fraction of target facilities whose graph access criterion fails; dimensionless `[0,1]`. Denominator is the reported assessed facility count. |
| `facility_access_by_category` | array | One record per `hospital`, `shelter`, and `candidate_shelter` (candidate status must remain distinct): integer `facility_count`, `reachable_count`, `unreachable_count`, `unassessed_count`, nullable `access_loss_fraction`, and `coverage_fraction`. Counts are network accessibility only; they do not mean the facility is open, staffed, safe, or has known capacity. This is the per-service cascade summary requested by A07. It does not assign people to facilities; that is a later shelter-allocation task. |
| Each distribution | `{status,unit,mean,p05,p50,p95}` | `status` is `AVAILABLE`, `PARTIAL`, or `UNAVAILABLE`; numeric values are nullable. `p05/p50/p95` describe empirical ensemble-member distribution only when at least two valid members exist; they are not calibrated coverage intervals. `mean` is the member mean. A null summary is not zero. |
| `coverage` | object | Separate population, facility, and road coverage records: integer `assessed_count`, integer `eligible_count`, integer `nodata_count`, nullable `fraction_assessed`. Fraction is null for a zero denominator. Never count NoData as dry, unexposed, unaffected, or passable. |
| `uncertainty` | object | Required `method`, `ensemble_id` (nullable if deterministic), `member_count`, and `interpretation`. Distinguish ensemble spread from calibrated uncertainty. |
| `provenance` | object | Required source references for hazard/depth, population, facilities, and road graph as applicable; each reference has `source_id`, `source_sha256` (64 lowercase hex when known, else null), `version`, and `role`. Also include `algorithm`, `algorithm_version`, `code_commit`, `parameters`, and grid `{crs,resolution_m}`. Unknown provenance stays null and adds a QC flag. |
| `qc_flags` | array of strings | Explicit reasons for partial coverage, unknown source metadata, assumptions, invalid/missing hazard depth, or unsupported event timing. Empty only when none apply. |

## Example

This is a shape example only; null values deliberately indicate unavailable metrics, not zero results.

```json
{
  "schema_id": "twinguard.impact_result",
  "schema_version": "0.1-draft",
  "result_id": "example-not-a-real-result",
  "run_id": 0,
  "run_version": "example",
  "source_mode": "SIMULATED",
  "event": {"event_key": "example", "event_start_utc": null, "event_end_utc": null, "time_basis": "UTC"},
  "valid_at_utc": "2026-01-01T00:00:00Z",
  "aggregation_interval": {"start_utc": "2026-01-01T00:00:00Z", "end_utc": "2026-01-01T01:00:00Z", "convention": "[start,end)"},
  "generated_at_utc": "2026-01-01T01:05:00Z",
  "scenario_key": "example-scenario",
  "thresholds": {"road_block_depth_m": 0.3, "road_threshold_is_assumption": true, "population_exposure_depth_m": null, "facility_exposure_depth_m": null},
  "metrics": {
    "population_exposed_people": null,
    "affected_facilities_count": null,
    "affected_road_length_m": null,
    "facility_access_loss_fraction": null
  },
  "facility_access_by_category": [],
  "coverage": {
    "population": {"assessed_count": 0, "eligible_count": 0, "nodata_count": 0, "fraction_assessed": null},
    "facilities": {"assessed_count": 0, "eligible_count": 0, "nodata_count": 0, "fraction_assessed": null},
    "roads": {"assessed_count": 0, "eligible_count": 0, "nodata_count": 0, "fraction_assessed": null}
  },
  "uncertainty": {"method": "NOT_AVAILABLE", "ensemble_id": null, "member_count": 0, "interpretation": "No computed result; null is not zero."},
  "provenance": {
    "algorithm": "not_run", "algorithm_version": null, "code_commit": null,
    "hazard_source": {"source_id": null, "source_sha256": null, "version": null, "role": "depth"},
    "population_source": {"source_id": null, "source_sha256": null, "version": null, "role": "exposure"},
    "facility_source": {"source_id": null, "source_sha256": null, "version": null, "role": "assets"},
    "road_graph_source": {"source_id": null, "source_sha256": null, "version": null, "role": "network"},
    "parameters": {}, "grid": {"crs": "EPSG:32644", "resolution_m": 30}
  },
  "qc_flags": ["EXAMPLE_ONLY", "RESULT_NOT_COMPUTED", "THRESHOLDS_UNCONFIGURED"]
}
```

## NoData, coverage, and interpretation

The population raster's NoData mask is exposure missingness, not zero people and not a hazard eligibility mask. Report population-cell coverage and leave the population exposure summary null if no valid cells were assessed; for partial coverage, report only the valid-area estimate together with `PARTIAL`, exact counts/fraction and a QC flag. Never extrapolate over NoData. Facility and road metrics similarly require an explicit eligible denominator and report missing depth/edge coverage. A numeric zero is allowed only when the corresponding valid coverage exists and the calculation actually returns zero.

All ensemble percentiles are descriptive scenario/member summaries unless a separate calibration/coverage assessment proves otherwise. `DERIVED`, `SIMULATED`, and `ASSUMPTION` results must remain labeled as such; neither impact nor route output is safety guidance or observed impact truth.

## API/UI projection comparison

- `docs/api/ai-service.yaml` currently requires scalar `exposure_people` and `affected_facilities`, allows an open-ended `provenance`, and has no coverage, units, interval, uncertainty summary, or NoData/null semantics. Proposal: make numeric summaries nullable; project population, facility and road distributions explicitly; add `valid_at_utc`, aggregation interval, `coverage`, typed provenance and `qc_flags`. Retain snake_case on the wire.
- `frontend/src/ui/types.ts` expects camelCase `exposurePeople`, `affectedFacilities`, `affectedRoads`, `affectedRoadsUnit`, `validAt`, `runId`, provenance and uncertainty. UI adapter should map the typed wire fields to these names and render missing metrics as “Unknown”; it must not coerce null to zero. `DecisionSupportPanel.tsx` currently says coverage unknown is not zero and has no result connected, consistent with this proposal.
- `docs/api/backend.yaml` currently has no impact result response. Adding a backend projection is integrator/API ownership; do not change it in this Lane A repair.

No implementation, database write, output row, or runtime/API compatibility is claimed by this proposal. A07 remains blocked until the selector and task state authorize it.
