"""Live flood recomputation: Open-Meteo gridded rainfall -> A06 ensemble -> versioned run outputs (CR-018).

Every run is DERIVED research output from model rainfall; nothing here is an observation, warning or safe-route claim.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import forcing as forcing_mod
from .solver import CELL_M, parameter_members, infiltration_rate, simulate

ENGINE_VERSION = "twinguard-live-engine/1.0.0"
THRESHOLDS_M = (0.15, 0.30, 0.50)
ACCESS_THRESHOLD_M = 0.30
OUTLOOK_LEVELS = (  # flooded area (>= 0.30 m, ensemble median of member peaks, km²) -> derived outlook level
    (50.0, "HIGH"), (10.0, "MODERATE"), (1.0, "LOW"), (0.0, "MINIMAL"),
)
LIMITATIONS = [
    "Rainfall is numerical weather-model output from Open-Meteo, not rain-gauge observation.",
    "A06 is a coarse 600 m local-inertial pilot with no storm-drain network, surveyed channels, tides or reservoir releases; it is not hydraulically validated.",
    "Ensemble spread combines weather models and Manning/infiltration multipliers; it is descriptive, not a calibrated confidence interval.",
    "The 24 past hours spin the model up from a dry start; earlier antecedent wetness is not represented.",
    "Outlook levels, exposure counts and facility flags are derived research indicators, not official flood warnings or safe-route guidance.",
]


class StaticGrid:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        with np.load(self.directory / "static.npz", allow_pickle=False) as bundle:
            self.arrays = {key: bundle[key] for key in bundle.files}
        self.meta = json.loads((self.directory / "static_meta.json").read_text(encoding="utf-8"))
        self.active = self.arrays["active"].astype(bool)
        self.drain = self.arrays["drain"].astype(bool)
        self.shape = self.active.shape

    @property
    def bounds(self) -> list[float]:
        return self.meta["grid"]["bounds_lonlat"]


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _dist(values) -> dict:
    a = np.asarray(values, dtype=np.float64)
    a = a[np.isfinite(a)]
    if not a.size:
        return {"mean": None, "p05": None, "p50": None, "p95": None, "members": 0}
    q = np.quantile(a, [0.05, 0.5, 0.95])
    return {"mean": float(a.mean()), "p05": float(q[0]), "p50": float(q[1]), "p95": float(q[2]), "members": int(a.size)}


def outlook_level(area_km2: float) -> str:
    for limit, level in OUTLOOK_LEVELS:
        if area_km2 >= limit:
            return level
    return "MINIMAL"


def compute_run(static: StaticGrid, snapshot: forcing_mod.ForcingSnapshot, members=None) -> tuple[dict, dict]:
    """Run the ensemble. Returns (result JSON, grids dict)."""
    a = static.arrays
    active, drain = static.active, static.drain
    members = members or parameter_members()
    past = forcing_mod.PAST_HOURS
    cell_km2 = (CELL_M / 1000) ** 2
    population = np.where(active, a["population"], np.nan)
    road_km = np.where(active, a["road_length_m"], 0.0) / 1000

    peaks, hourly_sum, member_rows, area_rows, volume_rows = [], None, [], [], []
    rain_rows = {}
    started = time.perf_counter()
    for model in snapshot.usable:
        rain = forcing_mod.map_to_grid(model, a["cell_lat"], a["cell_lon"], active | drain)
        rain_rows[model.model] = {
            "domain_mean_hourly_mm": [float(np.nanmean(r[active])) for r in rain[past:]],
            "domain_mean_past_total_mm": float(np.nanmean(rain[:past].sum(axis=0)[active])),
            "domain_mean_forecast_total_mm": float(np.nanmean(rain[past:].sum(axis=0)[active])),
            "max_cell_forecast_total_mm": float(np.nanmax(rain[past:].sum(axis=0)[active])),
        }
        for member in members:
            t0 = time.perf_counter()
            states, diag, steps = simulate(a["z"], active, drain, a["mann"] * member.manning_multiplier, a["porosity"],
                                           infiltration_rate(a["landcover"], member.infiltration_multiplier), rain, CELL_M, keep_from=past)
            if not np.isfinite(states).all() or states.min() < -1e-6:
                raise RuntimeError(f"invalid depths for {model.model} member {member.member_id}")
            if diag["rain_m3"] > 0 and diag["mass_balance_relative_error"] > 0.01:
                raise RuntimeError(f"mass balance >1% for {model.model} member {member.member_id}")
            states = np.where(active[None], states, 0.0)
            peaks.append(states.max(axis=0))
            hourly_sum = states.astype(np.float64) if hourly_sum is None else hourly_sum + states
            area_rows.append([float(np.count_nonzero(s[active] >= 0.15) * cell_km2) for s in states])
            volume_rows.append([float(np.sum(s[active] * a["porosity"][active]) * CELL_M * CELL_M) for s in states])
            member_rows.append({"weather_model": model.model, **asdict(member), "steps": steps,
                                "mass_balance_relative_error": diag["mass_balance_relative_error"],
                                "rain_m3": diag["rain_m3"], "runtime_seconds": round(time.perf_counter() - t0, 3)})
    if not peaks:
        raise RuntimeError("no ensemble members were run")
    peak = np.stack(peaks)
    n = len(peaks)
    hourly_mean = hourly_sum / n
    nan_out = lambda arr: np.where(active, arr, np.nan)  # noqa: E731 - NoData outside assessed cells, never dry
    grids = {
        "peak_mean": nan_out(peak.mean(axis=0)),
        "peak_p05": nan_out(np.percentile(peak, 5, axis=0)),
        "peak_p95": nan_out(np.percentile(peak, 95, axis=0)),
        "prob_peak_ge_0_30": nan_out((peak >= ACCESS_THRESHOLD_M).mean(axis=0)),
        "hourly_mean": np.where(active[None], hourly_mean, np.nan).astype(np.float32),
    }
    times = snapshot.usable[0].times_utc[past:]
    area = np.asarray(area_rows)
    volume = np.asarray(volume_rows)
    timeline = []
    for k, t in enumerate(times):
        timeline.append({
            "valid_time_utc": f"{t}:00Z" if len(t) == 16 else t,
            "rain_domain_mean_mm": {m: rain_rows[m]["domain_mean_hourly_mm"][k] for m in rain_rows},
            "flooded_area_ge_0_15_km2": _dist(area[:, k]),
            "stored_water_m3": _dist(volume[:, k]),
        })

    exposure = {}
    for threshold in THRESHOLDS_M:
        key = f"{threshold:.2f}"
        pops = [float(np.nansum(population[(p >= threshold) & active])) for p in peaks]
        areas = [float(np.count_nonzero(p[active] >= threshold) * cell_km2) for p in peaks]
        roads = [float(np.sum(road_km[(p >= threshold) & active])) for p in peaks]
        exposure[key] = {"population_people": _dist(pops), "flooded_area_km2": _dist(areas), "road_km": _dist(roads)}
    median_area = exposure[f"{ACCESS_THRESHOLD_M:.2f}"]["flooded_area_km2"]["p50"] or 0.0

    fcell = a["facility_cell"]
    rows, cols = np.unravel_index(fcell, static.shape)
    f_mean = grids["peak_mean"][rows, cols]
    f_p95 = grids["peak_p95"][rows, cols]
    f_prob = grids["prob_peak_ge_0_30"][rows, cols]
    groups = a["facility_group"]
    at_risk = np.flatnonzero((f_prob >= 0.5) | (f_mean >= ACCESS_THRESHOLD_M))
    order = at_risk[np.argsort(-f_prob[at_risk], kind="stable")]
    facilities = {
        "counts_by_group": {g: int((groups == g).sum()) for g in np.unique(groups)},
        "access_at_risk_by_group": {g: int((groups[at_risk] == g).sum()) for g in np.unique(groups)},
        "low_hazard_shelter_candidates": int(np.sum(np.isin(groups, ["shelter", "candidate_shelter"]) & (f_prob < 0.1) & (f_p95 < 0.15))),
        "access_at_risk": [
            {"name": str(a["facility_name"][i]) or "Unnamed", "group": str(groups[i]), "category": str(a["facility_category"][i]),
             "lon": float(a["facility_lon"][i]), "lat": float(a["facility_lat"][i]),
             "peak_depth_mean_m": float(f_mean[i]), "peak_depth_p95_m": float(f_p95[i]), "member_fraction_ge_0_30": float(f_prob[i])}
            for i in order[:200]
        ],
        "definition": "Cell peak depth >= 0.30 m (ensemble mean) or >= 50% of members; candidate shelters are OSM schools/colleges plus mapped shelters with < 10% members >= 0.30 m and p95 < 0.15 m. Not safe-shelter guidance.",
    }
    peak_time_idx = int(np.argmax([d["flooded_area_ge_0_15_km2"]["mean"] or 0 for d in timeline])) if timeline else 0
    result = {
        "schema": "twinguard.live_run.v1",
        "engine_version": ENGINE_VERSION,
        "status": "DERIVED_RESEARCH_OUTPUT",
        "source_mode": "LIVE",
        "computed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "forcing": forcing_mod.manifest(snapshot),
        "horizon": {"first_valid_time_utc": timeline[0]["valid_time_utc"] if timeline else None,
                    "last_valid_time_utc": timeline[-1]["valid_time_utc"] if timeline else None,
                    "hours": len(timeline), "spin_up_hours": past},
        "ensemble": {"members": n, "weather_models": [m.model for m in snapshot.usable], "parameter_members": len(members),
                     "max_mass_balance_relative_error": max(r["mass_balance_relative_error"] for r in member_rows),
                     "runtime_seconds": round(time.perf_counter() - started, 2)},
        "rainfall": rain_rows,
        "outlook": {"level": outlook_level(median_area), "basis_flooded_area_ge_0_30_km2_p50": median_area,
                    "peak_flooded_time_utc": timeline[peak_time_idx]["valid_time_utc"] if timeline else None,
                    "interpretation": "Derived research outlook from model rainfall; not an official warning."},
        "timeline": timeline,
        "exposure": exposure,
        "facilities": facilities,
        "grid": {"rows": static.shape[0], "cols": static.shape[1], "cell_size_m": CELL_M, "crs": static.meta["grid"]["crs"],
                 "corners_lonlat": static.meta["grid"]["corners_lonlat"], "nodata": "outside assessed CMA cells; not dry"},
        "members": member_rows,
        "static_bundle_sha256": static.meta["bundle_sha256"],
        "limitations": LIMITATIONS,
    }
    return result, grids


class RunStore:
    """Versioned run directories under ``root``; writes are atomic (temp dir + rename)."""

    def __init__(self, root: Path, keep: int = 48):
        self.root = Path(root)
        self.keep = keep
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def run_ids(self) -> list[str]:
        return sorted((p.name for p in self.root.iterdir() if p.is_dir() and p.name.startswith("live-") and (p / "result.json").exists()), reverse=True)

    def latest(self) -> dict | None:
        ids = self.run_ids()
        return self.load(ids[0]) if ids else None

    def load(self, run_id: str) -> dict | None:
        if not run_id.startswith("live-") or "/" in run_id or "\\" in run_id or ".." in run_id:
            return None
        path = self.root / run_id / "result.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def grid(self, run_id: str, name: str):
        if self.load(run_id) is None:
            return None
        with np.load(self.root / run_id / "grids.npz", allow_pickle=False) as bundle:
            return bundle[name] if name in bundle.files else None

    def save(self, result: dict, grids: dict, snapshot: forcing_mod.ForcingSnapshot) -> dict:
        with self._lock:
            forcing_sha = result["forcing"]["combined_forcing_sha256"]
            stamp = datetime.strptime(snapshot.fetched_at, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y%m%dT%H%M%SZ")
            run_id = f"live-{stamp}-{forcing_sha[:8]}"
            result["run_id"] = run_id
            tmp = self.root / f".tmp-{run_id}"
            if tmp.exists():
                shutil.rmtree(tmp)
            (tmp / "forcing").mkdir(parents=True)
            for model, body in snapshot.raw.items():
                (tmp / "forcing" / f"{model}.json").write_bytes(body)
            np.savez_compressed(tmp / "grids.npz", **{k: np.asarray(v, dtype=np.float32) for k, v in grids.items()})
            result["outputs"] = {"grids_npz_sha256": _sha_file(tmp / "grids.npz"),
                                 "raw_forcing_sha256": {m: _sha_bytes(b) for m, b in snapshot.raw.items()}}
            body = json.dumps(result, indent=1, allow_nan=False).encode("utf-8")
            (tmp / "result.json").write_bytes(body)
            os.replace(tmp, self.root / run_id)
            for old in self.run_ids()[self.keep:]:
                shutil.rmtree(self.root / old, ignore_errors=True)
            return result


class LiveEngine:
    def __init__(self, static_dir: Path, runs_dir: Path, fetcher=forcing_mod.fetch_snapshot, min_interval_s: float = 600):
        self.static = StaticGrid(static_dir)
        self.store = RunStore(runs_dir)
        self.fetcher = fetcher
        self.min_interval_s = min_interval_s
        self._run_lock = threading.Lock()
        self.state = {"running": False, "last_attempt_at": None, "last_error": None, "last_outcome": None}

    def run_once(self, force: bool = False) -> dict:
        """Fetch forcing and recompute. Identical forcing to the latest run is idempotent (no new run)."""
        if not self._run_lock.acquire(blocking=False):
            return {"outcome": "busy", "run": None}
        try:
            self.state.update(running=True, last_attempt_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), last_error=None)
            latest = self.store.latest()
            if latest and not force:
                age = time.time() - datetime.strptime(latest["forcing"]["fetched_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
                if age < self.min_interval_s:
                    self.state["last_outcome"] = "rate_limited"
                    return {"outcome": "rate_limited", "run": latest}
            snapshot = self.fetcher(self.static.bounds)
            sha = snapshot.combined_sha256()
            if latest and latest["forcing"]["combined_forcing_sha256"] == sha:
                self.state["last_outcome"] = "unchanged"
                return {"outcome": "unchanged", "run": latest}
            result, grids = compute_run(self.static, snapshot)
            saved = self.store.save(result, grids, snapshot)
            self.state["last_outcome"] = "created"
            return {"outcome": "created", "run": saved}
        except Exception as error:
            self.state.update(last_error=f"{type(error).__name__}: {str(error)[:200]}", last_outcome="failed")
            raise
        finally:
            self.state["running"] = False
            self._run_lock.release()
