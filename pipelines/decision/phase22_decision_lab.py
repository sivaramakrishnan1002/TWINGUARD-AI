"""A13 paired, simulation-only H2-H5 decision-lab summaries.

Run from the repository root with:
  .venv\\Scripts\\python.exe pipelines\\decision\\phase22_decision_lab.py

This reads only the registered final A05/A09/A10/A11/A12 artifacts and writes
new A13 versioned JSON outputs. No route search, allocation rerun, or raster
interpolation is performed.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pyarrow.parquet as pq
import rasterio


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "experiments/decision_lab/batch2_v1"
MASTER_TRANSFORM = rasterio.Affine(600.0, 0.0, 390000.0, 0.0, -600.0, 1471620.0)
SEED = 20261028
BOOTSTRAPS = 5000
PROHIBITED = {"vulnerability", "vulnerability_score", "composite_score", "weighted_priority", "priority_rank", "official_priority_zone"}
INPUTS = {
    "a05_summary": "data/features/forecast/batch2_v1/forecast_summary.json",
    "a09_routes": "data/features/routing/results/batch2_v1/revision_3/route_results.jsonl",
    "a09_summary": "data/features/routing/results/batch2_v1/revision_3/summary.json",
    "a10_cases": "data/features/decision/shelters/batch2_v3/allocation_cases.parquet",
    "a10_detail": "data/features/decision/shelters/batch2_v3/allocation_detail.parquet",
    "a10_candidates": "data/features/decision/shelters/batch2_v3/candidate_facilities.parquet",
    "a10_summary": "data/features/decision/shelters/batch2_v3/run_summary.json",
    "a11_manifest": "data/features/decision/priority_zones/batch2_v1/revision_2/run_manifest.json",
    "a12_sensitivity": "experiments/explainability/batch2_v1/results/explainability_sensitivity.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def case_key(row: dict[str, Any]) -> tuple[str, int, str, str]:
    return (str(row["scenario_key"]), int(row["requested_horizon_seconds"]), str(row["origin_id"]), str(row["destination_id"]))


def event_from_scenario(scenario_key: str) -> str:
    return scenario_key.split("/", 1)[0]


def bootstrap_cluster_mean(diffs_by_cluster: dict[str, list[float]], seed: int = SEED, n_boot: int = BOOTSTRAPS) -> dict[str, Any]:
    """Paired cluster bootstrap of within-cluster mean differences."""
    values = {k: float(np.mean(v)) for k, v in diffs_by_cluster.items() if v}
    if not values:
        return {"mean_difference": None, "ci95": [None, None], "cluster_count": 0, "replicates": n_boot, "seed": seed}
    keys = sorted(values)
    rng = np.random.default_rng(seed)
    sampled = rng.integers(0, len(keys), size=(n_boot, len(keys)))
    draws = np.asarray([[values[keys[i]] for i in row] for row in sampled], dtype=float).mean(axis=1)
    return {
        "mean_difference": float(np.mean(list(values.values()))),
        "ci95": [float(x) for x in np.quantile(draws, [0.025, 0.975])],
        "cluster_count": len(keys),
        "cluster_means": values,
        "replicates": n_boot,
        "seed": seed,
        "interpretation": "descriptive simulation sensitivity only; few event clusters, not population inference",
    }


def compare_values(rows: list[tuple[str, float | None, float | None]], direction: str) -> dict[str, Any]:
    """Compare A and B; lower/higher is better. Missing remains separate."""
    counts = Counter()
    diffs: dict[str, list[float]] = defaultdict(list)
    for cluster, a, b in rows:
        if a is None or b is None or not math.isfinite(a) or not math.isfinite(b):
            counts["missing"] += 1
            continue
        delta = a - b
        diffs[cluster].append(delta)
        better = delta < -1e-12 if direction == "lower" else delta > 1e-12
        worse = delta > 1e-12 if direction == "lower" else delta < -1e-12
        counts["wins" if better else "losses" if worse else "ties"] += 1
    total = len(rows)
    comparable = counts["wins"] + counts["ties"] + counts["losses"]
    return {
        "direction": f"{direction} is better for option A",
        "counts": {name: counts[name] for name in ("wins", "ties", "losses", "missing", "incomparable")},
        "matched_case_count": total,
        "comparable_case_count": comparable,
        "descriptive_case_fraction_A_better": counts["wins"] / comparable if comparable else None,
        "paired_A_minus_B": bootstrap_cluster_mean(diffs),
    }


def _read_valid_mask(tif_path: Path, expected_shape: tuple[int, int]) -> np.ndarray:
    with rasterio.open(tif_path) as ds:
        if ds.count != 1 or ds.shape != expected_shape or ds.crs is None or ds.crs.to_epsg() != 32644 or ds.res != (600.0, 600.0) or ds.transform != MASTER_TRANSFORM:
            raise ValueError(f"A05 validity-mask raster grid mismatch: {tif_path}")
        if ds.nodata is None:
            raise ValueError(f"A05 validity-mask raster has no NoData value: {tif_path}")
        return ds.read_masks(1) > 0


def validate_output_contract(h2: dict[str, Any], route: dict[str, Any], h5: dict[str, Any], provenance: dict[str, Any]) -> None:
    """Fail closed on forbidden aggregations and missingness/status regressions."""
    def visit(value: Any) -> None:
        if isinstance(value, dict):
            forbidden = PROHIBITED.intersection(str(k).lower() for k in value)
            if forbidden:
                raise ValueError(f"Prohibited A13 output field(s): {sorted(forbidden)}")
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    for payload in (h2, route, h5, provenance):
        visit(payload)
    if h2.get("case_count") != 75 or h2.get("status") != "SIMULATED_SYNTHETIC_HOLDOUT_DIAGNOSTIC_NOT_EMPIRICAL_CALIBRATION":
        raise ValueError("A13 H2 expected 75 explicitly simulated cases")
    if route.get("route_record_count") != 216 or set(route.get("comparisons", {})) != {"H3", "H4"}:
        raise ValueError("A13 route comparison input/output count mismatch")
    if provenance.get("a11_indicators_kept_separate", {}).get("indicator_categories") != ["hazard", "population_exposure", "facility_access_loss"]:
        raise ValueError("A11 indicator separation contract changed")
    if h5.get("departure_shift", {}).get("status") != "UNAVAILABLE_FROM_REGISTERED_ARTIFACTS":
        raise ValueError("Unexpected unsupported departure-shift outcome")


def compute_h2(summary: dict[str, Any]) -> dict[str, Any]:
    case_metrics = []
    input_files = []
    for event, event_obj in sorted(summary["events"].items()):
        for scenario, scenario_obj in sorted(event_obj["scenarios"].items()):
            directory = ROOT / scenario_obj["output_directory"]
            npz_path = directory / "depth_members_by_horizon_DERIVED.npz"
            if not npz_path.is_file():
                raise FileNotFoundError(npz_path)
            input_files.append(npz_path)
            with np.load(npz_path, allow_pickle=False) as npz:
                depth = npz["depth_m"]
                member_ids = npz["member_ids"].astype(int).tolist()
                horizons = npz["horizons_hours"].astype(int).tolist()
                if depth.shape[0] != 20 or depth.shape[-2:] != (88, 69) or member_ids != list(range(1, 21)):
                    raise ValueError(f"Unexpected registered A05 ensemble shape/member IDs: {npz_path}")
                if 12 not in member_ids or 20 not in member_ids:
                    raise ValueError(f"Required nominal and held-out member missing: {npz_path}")
                if int(npz["seed"].item()) != int(summary["seed"]):
                    raise ValueError(f"A05 NPZ seed disagrees with its summary: {npz_path}")
                member_parameters = {int(x["member_id"]): (float(x["manning_multiplier"]), float(x["infiltration_multiplier"])) for x in summary["parameter_members"]}
                if member_parameters.get(12) != (1.0, 1.0):
                    raise ValueError("A05 member 12 is not the nominal 1.0/1.0 parameter reference")
                for hi, horizon in enumerate(horizons):
                    mask_path = directory / f"depth_lead{horizon:02d}h_p50_DERIVED.tif"
                    input_files.append(mask_path)
                    valid_raster = _read_valid_mask(mask_path, depth.shape[-2:])
                    forecast = depth[:19, hi, :, :]
                    truth = depth[19, hi, :, :]
                    valid = valid_raster & np.isfinite(truth) & np.isfinite(forecast).all(axis=0)
                    if int(valid.sum()) != int(scenario_obj["horizons"][hi]["eligible_cells"]):
                        raise ValueError(f"A05 mask count disagrees with summary for {event}/{scenario}/{horizon}h")
                    if not valid.any():
                        raise ValueError(f"No valid A05 cells for {event}/{scenario}/{horizon}h")
                    median = np.median(forecast, axis=0)
                    nominal = depth[member_ids.index(12), hi, :, :]
                    lo, hi95 = np.quantile(forecast, [0.05, 0.95], axis=0)
                    errors = {
                        "deterministic_member12_mae_m": float(np.mean(np.abs(nominal[valid] - truth[valid]))),
                        "ensemble_median_mae_m": float(np.mean(np.abs(median[valid] - truth[valid]))),
                        "deterministic_member12_rmse_m": float(np.sqrt(np.mean((nominal[valid] - truth[valid]) ** 2))),
                        "ensemble_median_rmse_m": float(np.sqrt(np.mean((median[valid] - truth[valid]) ** 2))),
                        "ensemble_p05_p95_coverage_fraction": float(np.mean((truth[valid] >= lo[valid]) & (truth[valid] <= hi95[valid]))),
                        "ensemble_p05_p95_mean_width_m": float(np.mean(hi95[valid] - lo[valid])),
                    }
                    case_metrics.append({
                        "event_key": event, "scenario_key": scenario, "horizon_hours": horizon,
                        "valid_at_utc": (datetime.fromisoformat(event_obj["window_start_utc"].replace("Z", "+00:00")) + timedelta(hours=horizon)).isoformat().replace("+00:00", "Z"),
                        "valid_cell_count": int(valid.sum()), "grid_cell_count": int(valid.size),
                        "nodata_or_unavailable_cell_count": int(valid.size - valid.sum()),
                        "units": "depth in metres; errors/interval widths in metres",
                        "metrics": errors,
                    })
    metric_keys = list(case_metrics[0]["metrics"])
    aggregate = {k: float(np.mean([x["metrics"][k] for x in case_metrics])) for k in metric_keys}
    paired = []
    for item in case_metrics:
        m = item["metrics"]
        paired.append((item["event_key"], m["ensemble_median_mae_m"], m["deterministic_member12_mae_m"]))
    return {
        "status": "SIMULATED_SYNTHETIC_HOLDOUT_DIAGNOSTIC_NOT_EMPIRICAL_CALIBRATION",
        "grid": {"shape": [88, 69], "resolution_m": 600, "crs": summary["crs"], "eligible_model_cells_per_case": 2430},
        "truth": "held-out member 20 from the same A05/A06 parameter ensemble; not observed water",
        "deterministic_reference": "member 12 (Manning multiplier 1.0; infiltration multiplier 1.0)",
        "uncertainty_reference": "median and p05-p95 over forecast members 1-19",
        "no_data_rule": "mask from corresponding A05 p50 GeoTIFF; masked/outside-model cells excluded, never set to dry",
        "case_count": len(case_metrics), "cases": case_metrics,
        "macro_mean_across_cases": aggregate,
        "ensemble_median_minus_member12_mae": compare_values(paired, "lower"),
        "event_cluster_count": len({x["event_key"] for x in case_metrics}),
        "limitations": ["member 20 is a synthetic member from the same parameter ensemble, not independent observations", "interval coverage is only relative to this synthetic holdout", "only three event windows; bootstrap intervals are descriptive", "the 600 m grid and model-domain mask are preserved"],
        "used_files": sorted({str(p.relative_to(ROOT).as_posix()): sha256_file(p) for p in input_files}.items()),
    }


def _route_metric(row: dict[str, Any], metric: str) -> float | None:
    if metric == "route_failure_fraction":
        val = row.get("route_failure_probability")
    elif metric == "travel_time_seconds":
        val = row.get("travel_time_seconds")
    elif metric == "depth_distance_exposure_m2":
        val = (row.get("provenance") or {}).get("parameters", {}).get("expected_exposure_depth_distance_m2")
    elif metric == "assessed_edge_coverage_fraction":
        val = (row.get("edge_coverage") or {}).get("fraction_assessed")
    else:
        raise KeyError(metric)
    return float(val) if val is not None and math.isfinite(float(val)) else None


def compute_route_comparisons(routes: list[dict[str, Any]]) -> dict[str, Any]:
    by_key_method: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in routes:
        by_key_method[case_key(row)][row["method"]] = row
    outcomes: dict[str, Any] = {}
    for hypothesis, method_a, method_b in [
        ("H3", "uncertainty_aware", "current_flood_aware"),
        ("H4", "horizon_aware", "current_flood_aware"),
    ]:
        keys = sorted(k for k, methods in by_key_method.items() if method_a in methods and method_b in methods)
        outcomes_for_h = {}
        for metric in ("route_failure_fraction", "travel_time_seconds", "depth_distance_exposure_m2", "assessed_edge_coverage_fraction"):
            pairs = []
            for key in keys:
                a, b = by_key_method[key][method_a], by_key_method[key][method_b]
                # Missing paths are unknown/incomparable outcomes, not zero-cost successes.
                if metric in ("travel_time_seconds", "depth_distance_exposure_m2") and (a.get("status") != "ROUTE_FOUND" or b.get("status") != "ROUTE_FOUND"):
                    av = bv = None
                else:
                    av, bv = _route_metric(a, metric), _route_metric(b, metric)
                pairs.append((event_from_scenario(key[0]), av, bv))
            outcomes_for_h[metric] = compare_values(pairs, "lower" if metric != "assessed_edge_coverage_fraction" else "higher")
        status_counts = Counter((row.get("method"), row.get("status")) for row in routes if row.get("method") in (method_a, method_b))
        outcome = {
            "option_A": method_a, "option_B": method_b,
            "pair_key": ["scenario_key", "requested_horizon_seconds", "origin_id", "destination_id"],
            "matched_case_count": len(keys),
            "event_clusters": sorted({event_from_scenario(k[0]) for k in keys}),
            "status_counts_by_method": {m: {s: status_counts[(m, s)] for s in ("ROUTE_FOUND", "NO_TOPOLOGICAL_PATH", "INSUFFICIENT_HAZARD_COVERAGE")} for m in (method_a, method_b)},
            "route_found_summaries_by_method": {
                m: _route_found_summary([by_key_method[k][m] for k in keys]) for m in (method_a, method_b)
            },
            "outcomes": outcomes_for_h,
            "arrival_outcomes": {
                "definition": "arrival time only for paired ROUTE_FOUND cases; compare UTC arrival instants, no route or null arrival is missing",
                "paired_found_count": sum(1 for k in keys if by_key_method[k][method_a].get("status") == by_key_method[k][method_b].get("status") == "ROUTE_FOUND" and by_key_method[k][method_a].get("arrival_at_utc") and by_key_method[k][method_b].get("arrival_at_utc")),
                "arrival_time_delta_seconds_A_minus_B": compare_values([
                    (event_from_scenario(k[0]),
                     _time_delta_anchor(by_key_method[k][method_a].get("arrival_at_utc")),
                     _time_delta_anchor(by_key_method[k][method_b].get("arrival_at_utc")))
                    for k in keys
                    if by_key_method[k][method_a].get("status") == by_key_method[k][method_b].get("status") == "ROUTE_FOUND"
                ], "lower"),
            },
            "limitations": ["all outcomes are from simulated A09 route outputs", "routes are not real-world safety evidence", "route failures, travel time, exposure, and coverage are not collapsed into a score"],
        }
        outcomes[hypothesis] = outcome
    return {
        "status": "SIMULATED_DESCRIPTIVE_ROUTE_COMPARISONS_NOT_SAFETY_VALIDATION",
        "route_record_count": len(routes), "case_key_count": len(by_key_method),
        "run_id": "A09 revision_3", "scenario": "perfect_foresight_imerg", "units": {"distance": "m", "travel_time": "seconds", "depth_distance_exposure": "m2", "failure/accessibility": "ensemble fractions as stored by A09", "coverage": "assessed directed route edges / route edges"},
        "departure_semantics": "A09 saved departure_at_utc; paired methods use the same case key and saved time snapshot",
        "thresholds": "A09 registered assumptions: ordinary edge blocks at >=0.30 m, tunnel proxy at >=0.15 m, bridges unassessed; sensitivity 0.15/0.30/0.50 m",
        "comparisons": outcomes,
    }


def _route_found_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    found = [r for r in rows if r.get("status") == "ROUTE_FOUND"]
    def median(values: Iterable[float | None]) -> float | None:
        present = [float(x) for x in values if x is not None and math.isfinite(float(x))]
        return float(np.median(present)) if present else None
    return {
        "route_found_count": len(found),
        "median_travel_time_seconds": median(r.get("travel_time_seconds") for r in found),
        "median_route_failure_probability": median(r.get("route_failure_probability") for r in found),
        "median_expected_depth_distance_exposure_m2": median((r.get("provenance") or {}).get("parameters", {}).get("expected_exposure_depth_distance_m2") for r in found),
        "median_assessed_edge_coverage_fraction": median((r.get("edge_coverage") or {}).get("fraction_assessed") for r in found),
    }


def _time_delta_anchor(value: str | None) -> float | None:
    # Arrival times are compared pairwise after parsing UTC ISO timestamps.
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def compute_h5(routes: list[dict[str, Any]], detail_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]], a08_dir: Path) -> dict[str, Any]:
    bridge_use = Counter()
    for route in routes:
        if route.get("method") == "static":
            for edge in route.get("edges") or []:
                if edge.get("bridge") is True and edge.get("edge_id") is not None:
                    bridge_use[int(edge["edge_id"])] += 1
    bridge_id = None
    bridge_path_rows = []
    if bridge_use:
        max_uses = max(bridge_use.values())
        bridge_id = min(edge_id for edge_id, count in bridge_use.items() if count == max_uses)
        for route in routes:
            edge_ids = [int(e["edge_id"]) for e in route.get("edges") or [] if e.get("edge_id") is not None]
            if bridge_id in edge_ids:
                bridge_path_rows.append({"result_id": route["result_id"], "method": route["method"], "scenario_key": route["scenario_key"], "horizon_seconds": route["requested_horizon_seconds"], "saved_path_contains_closed_bridge": True})

    shelter_candidates = {int(c["osmid"]): c for c in candidate_rows if c.get("category") == "shelter"}
    shelter_ids = set(shelter_candidates)
    shelter_totals = Counter()
    for row in detail_rows:
        if int(row["candidate_osm_id"]) in shelter_ids:
            value = row.get("allocated_people_model_estimate")
            if value is not None:
                shelter_totals[int(row["candidate_osm_id"])] += float(value)
    shelter_id = None
    removed_by_group: dict[tuple[Any, ...], float] = defaultdict(float)
    if shelter_totals:
        max_alloc = max(shelter_totals.values())
        shelter_id = min(osmid for osmid, amount in shelter_totals.items() if amount == max_alloc)
        for row in detail_rows:
            if int(row["candidate_osm_id"]) == shelter_id and row.get("allocated_people_model_estimate") is not None:
                group = (row["event_key"], row["scenario_key"], int(row["horizon_hours"]), row["valid_at_utc"], int(row["member_id"]))
                removed_by_group[group] += float(row["allocated_people_model_estimate"])

    saved_snapshots = []
    for path in sorted(a08_dir.glob("*_snapshots.npz")):
        with np.load(path, allow_pickle=False) as archive:
            saved_snapshots.extend(str(x) for x in archive["valid_at_utc"].astype(str).tolist())
    exact_departure_shifts_present = False
    # A08 stores selected forecast horizons (6, 12, 24, 48, 72 h), not +/-1 h routes.
    departure = {
        "status": "UNAVAILABLE_FROM_REGISTERED_ARTIFACTS",
        "requested": ["departure one hour earlier", "departure one hour later"],
        "reason": "A09 contains saved routes at registered event/scenario/horizon cases; A08 snapshots are at 6, 12, 24, 48 and 72 hours. No exact +/-1-hour snapshot or rerouted result is present; no interpolation or new route search was performed.",
        "exact_shift_snapshot_available": exact_departure_shifts_present,
        "saved_snapshot_times_utc": sorted(set(saved_snapshots)),
    }
    return {
        "status": "PARTIALLY_SUPPORTED_COUNTERFACTUALS; ALL_SIMULATED",
        "departure_shift": departure,
        "bridge_closure": {
            "status": "SAVED_PATH_INVALIDATION_ONLY_NO_REROUTE",
            "selection_rule": "most frequent bridge-flagged edge in saved static A09 route paths; tie-break smallest stable edge_id",
            "edge_id": bridge_id,
            "saved_static_path_use_count": bridge_use.get(bridge_id, 0) if bridge_id is not None else 0,
            "saved_route_records_containing_edge": bridge_path_rows,
            "counterfactual_interpretation": "If this edge were unavailable, listed saved paths would be invalidated. No alternative route is inferred because the saved A09 artifacts do not include bridge-closure reruns.",
            "source_graph_status": "bridges are UNASSESSED_STRUCTURE in A08; closure is a hypothetical explicit scenario, not observed condition",
        },
        "shelter_unavailability": {
            "status": "ALLOCATION_WITHDRAWAL_WITHOUT_REALLOCATION",
            "selection_rule": "shelter category with greatest cumulative saved allocation; tie-break smallest numeric OSM ID",
            "candidate_osm_id": shelter_id,
            "candidate_record": shelter_candidates.get(shelter_id) if shelter_id is not None else None,
            "cumulative_allocated_people_model_estimate": shelter_totals.get(shelter_id, 0.0) if shelter_id is not None else 0.0,
            "removed_allocations_by_event_scenario_horizon_member": [
                {"event_key": k[0], "scenario_key": k[1], "horizon_hours": k[2], "valid_at_utc": k[3], "member_id": k[4], "withdrawn_allocation_people_model_estimate": v}
                for k, v in sorted(removed_by_group.items())
            ],
            "capacity_factor": "not available in allocation_detail rows; not inferred",
            "counterfactual_interpretation": "Withdraw this candidate's saved allocation only; other assignments are not rebalanced. The 100-person shelter capacity and all A10 capacities are assumptions, not verified availability.",
        },
        "limitations": ["No real bridge closure or shelter availability observations", "no rerouting or reallocation performed", "allocation values are model estimates under assumed capacities and coarse weak-component screening"],
    }


def main() -> None:
    started = time.perf_counter()
    plan_path = OUT / "analysis_plan.json"
    if not plan_path.is_file():
        raise FileNotFoundError(f"Predeclared analysis plan missing: {plan_path}")
    plan = load_json(plan_path)
    if plan.get("status") != "PREDECLARED_BEFORE_ANALYSIS" or plan.get("random_seed") != SEED:
        raise ValueError("A13 analysis plan status or seed mismatch")
    resolved = {name: ROOT / rel for name, rel in INPUTS.items()}
    missing = [str(p) for p in resolved.values() if not p.is_file()]
    if missing:
        raise FileNotFoundError("Required final A13 input missing: " + ", ".join(missing))
    input_hashes = {name: {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path), "size_bytes": path.stat().st_size} for name, path in resolved.items()}
    a05 = load_json(resolved["a05_summary"])
    a09_summary = load_json(resolved["a09_summary"])
    a10_summary = load_json(resolved["a10_summary"])
    a11 = load_json(resolved["a11_manifest"])
    a12 = load_json(resolved["a12_sensitivity"])
    route_rows = [json.loads(line) for line in resolved["a09_routes"].read_text(encoding="utf-8").splitlines() if line.strip()]
    detail_rows = pq.read_table(resolved["a10_detail"]).to_pylist()
    candidate_rows = pq.read_table(resolved["a10_candidates"]).to_pylist()
    h2 = compute_h2(a05)
    route = compute_route_comparisons(route_rows)
    h5 = compute_h5(route_rows, detail_rows, candidate_rows, ROOT / "data/features/routing/time_dependent_batch2")
    # Include the A10 capacity-factor cases separately; never aggregate them into an A11 score.
    h5["a10_capacity_factor_case_count"] = pq.read_metadata(resolved["a10_cases"]).num_rows
    h5["a10_capacity_factor_values"] = sorted(set(float(x) for x in a10_summary.get("capacity_factors", [])))
    provenance = {
        "status": "HASHED_FINAL_REGISTERED_INPUTS",
        "input_hashes": input_hashes,
        "a05_member_artifacts": h2.pop("used_files"),
        "a09_identity": {"run_id": a09_summary.get("generated_at_utc"), "seed": a09_summary.get("seed"), "hidden_truth_member_id": a09_summary.get("hidden_truth_member_id"), "forecast_member_ids": a09_summary.get("forecast_member_ids"), "event_keys": a09_summary.get("event_keys"), "horizons_hours": a09_summary.get("horizons_hours"), "scenario_key": a09_summary.get("scenario_key"), "graph_counts": a09_summary.get("graph_counts")},
        "a10_identity": {"generated_at_utc": a10_summary.get("generated_at_utc"), "seed": a10_summary.get("seed"), "grid": a10_summary.get("grid"), "capacity_assumptions_people": a10_summary.get("capacity_assumptions_people"), "capacity_factors": a10_summary.get("capacity_factors")},
        "a11_indicators_kept_separate": {"manifest_schema": a11.get("schema_id"), "status": a11.get("status"), "case_count": a11.get("case_count"), "indicator_categories": ["hazard", "population_exposure", "facility_access_loss"]},
        "a12_context_only": {"status": a12.get("status"), "model_claim": a12.get("model_claim"), "not_used_as_weight_or_score": True},
        "reproducibility": {"seed": SEED, "bootstrap_replicates": BOOTSTRAPS, "compute_device": "CPU NumPy/PyArrow; current A13 statistics are small, and copying these arrays to the available GPU would cost more than the calculations", "no_source_data_modified": True},
    }
    validate_output_contract(h2, route, h5, provenance)
    write_json(OUT / "h2_synthetic_holdout_metrics.json", h2)
    write_json(OUT / "h3_h4_route_comparisons.json", route)
    write_json(OUT / "h5_counterfactuals.json", h5)
    write_json(OUT / "input_provenance.json", provenance)
    output_paths = [OUT / x for x in ("analysis_plan.json", "h2_synthetic_holdout_metrics.json", "h3_h4_route_comparisons.json", "h5_counterfactuals.json", "input_provenance.json")]
    manifest = {
        "schema_id": "twinguard.a13_decision_lab_manifest", "schema_version": "1.0", "task_id": "A13", "version": "batch2_v1",
        "status": "SIMULATED_DESCRIPTIVE_RESEARCH_NOT_VALIDATED_NOT_OPERATIONAL",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": SEED, "bootstrap_replicates": BOOTSTRAPS,
        "source_mode": "SIMULATED", "input_hashes": input_hashes,
        "analysis_code_sha256": sha256_file(Path(__file__).resolve()),
        "analysis_plan_sha256": sha256_file(plan_path),
        "outputs": {p.name: {"sha256": sha256_file(p), "size_bytes": p.stat().st_size} for p in output_paths},
        "runtime_seconds": round(time.perf_counter() - started, 6),
    }
    write_json(OUT / "run_manifest.json", manifest)
    print(json.dumps({"status": "ok", "output_dir": OUT.relative_to(ROOT).as_posix(), "h2_cases": h2["case_count"], "a09_routes": route["route_record_count"], "a10_detail_rows": len(detail_rows), "runtime_seconds": manifest["runtime_seconds"]}))


if __name__ == "__main__":
    main()
