"""C4 v3 runtime settings (environment variables; read on each call so tests can override them)."""
from __future__ import annotations

import os
from pathlib import Path

ENGINE_VERSION = "twinguard-v3-engine/1.0.0 (A06/A23 local-inertial solver, services.flood_engine)"
ENGINE_VERSION_A25 = "twinguard-v3-engine/1.1.0 (A25 services.flood_engine.scenario)"
BADGE = "DEMO / SIMULATION"
RUN_ID_PATTERN = r"^(sim|evt|whatif)-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}$"
FOCUS_AREAS = ("VELACHERY", "ADYAR", "T_NAGAR", "PORUR")
MAX_QUEUE = 4
FLOOD_THRESHOLD_M = 0.15
DEFAULT_BLOCK_THRESHOLD_M = 0.30
CHENNAI = {"lon": 80.2707, "lat": 13.0827}

LIMITATIONS = [
    "Coarse 600 m local-inertial pilot (A06/A23); no storm-drain network, surveyed channels or hydraulic validation.",
    "Event rainfall is archived IMERG/ERA5 (REPLAY) and forecast rainfall is Open-Meteo model output, not gauge observation.",
    "Reservoir release and tide what-ifs are assumption-based forcing proxies, not routed river hydraulics.",
    "Road states, shelter capacities, incidents and resource plans are derived demo indicators, not official guidance.",
    "Building and population exposure use the model cell containing each building or population cell.",
]
LIMITATIONS_A06 = LIMITATIONS  # 600 m A06/A23 pilot (fallback engine)


def limitations_for(engine: str, resolution: str, cell_size_m: float | None) -> list[str]:
    """Thesis limitation notes (<= 5) matching the engine and grid the run actually used (B13 finding)."""
    if engine != "a25":
        return list(LIMITATIONS_A06)
    size = int(cell_size_m) if cell_size_m else (30 if resolution == "focus" else a25_citywide_cell_m())
    scope = "focus-area" if resolution == "focus" else "citywide"
    return [
        f"A25 local-inertial model on a {size} m {scope} grid (Copernicus GLO-30 DEM); no storm-drain network or hydraulic validation.",
        "Event rainfall is archived IMERG/ERA5 (REPLAY) and forecast rainfall is Open-Meteo model output, not gauge observation.",
        "Reservoir releases enter at one river cell per reservoir and tide is a constant sea-level offset; not routed river hydraulics.",
        "Road states, shelter capacities, incidents and resource plans are derived demo indicators, not official guidance.",
        "Building and population exposure use the model cell containing each building; most building heights are estimated.",
    ]


def env_path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default))


def grid_static_dir(resolution: str = "citywide", focus_area: str | None = None) -> Path:
    """A25 grid when installed (citywide_120m / focus_30m_<AREA>), else the A06 600 m grid (citywide only)."""
    if a25_enabled():
        name = f"citywide_{a25_citywide_cell_m()}m" if resolution == "citywide" else f"focus_30m_{focus_area}"
        return a25_root() / name
    if resolution == "citywide":
        return env_path("TWINGUARD_LIVE_STATIC", "/app/data/features/live/a06_live_static_v1")
    return Path("/nonexistent/focus-resolution-not-installed")


def a25_root() -> Path:
    return env_path("TWINGUARD_V3_A25_STATIC", "/app/data/features/live/a25_static_v1")


def a25_enabled() -> bool:
    """Use Lane A's A25 engine (120 m citywide / 30 m focus) when its bundle is installed, unless pinned to A06."""
    if os.environ.get("TWINGUARD_V3_ENGINE", "auto") == "a06":
        return False
    if not (a25_root() / "manifest.json").exists():
        return False
    try:
        import services.flood_engine.scenario  # noqa: F401
    except ImportError:
        return False
    return True


def a25_members() -> int:
    return 3 if os.environ.get("TWINGUARD_V3_A25_MEMBERS", "1") == "3" else 1


def a25_citywide_cell_m() -> int:
    return 90 if os.environ.get("TWINGUARD_V3_A25_CITYWIDE_M", "120") == "90" else 120


def product_static_dir() -> Path:
    return env_path("TWINGUARD_V3_PRODUCT_STATIC", "/app/data/features/v3/product_static_v1")


def runs_dir() -> Path:
    return env_path("TWINGUARD_V3_RUNS", "/app/data/v3/runs")


def weather_min_interval_s() -> int:
    return max(600, int(float(os.environ.get("TWINGUARD_V3_WEATHER_MIN_INTERVAL_S", "600"))))


def run_min_interval_s() -> float:
    return float(os.environ.get("TWINGUARD_V3_RUN_MIN_INTERVAL_S", "2"))


def run_timeout_s() -> float:
    return float(os.environ.get("TWINGUARD_V3_RUN_TIMEOUT_S", "5400"))


def members_setting() -> str:
    return os.environ.get("TWINGUARD_V3_MEMBERS", "3")


def worker_mode() -> str:
    """TWINGUARD_V3_WORKER = persistent | per_run | auto (default: persistent when runs resolve to CUDA)."""
    value = os.environ.get("TWINGUARD_V3_WORKER", "auto").strip().lower()
    if value in ("persistent", "per_run"):
        return value
    from . import device
    try:
        return "persistent" if device.resolve(device.engine_supports_gpu())["used"] == "cuda" else "per_run"
    except Exception:  # noqa: BLE001
        return "per_run"


def inline_worker() -> bool:
    """Tests may run simulations in a thread instead of a child process."""
    return os.environ.get("TWINGUARD_V3_INLINE_WORKER", "0") == "1"
