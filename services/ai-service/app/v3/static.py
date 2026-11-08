"""Read-only static inputs for C4 v3: model grid, roads, buildings, shelters and saved events."""
from __future__ import annotations

import json
import math
import threading
from functools import cached_property
from pathlib import Path

import numpy as np

from . import config

EVENTS_FILE = Path(__file__).with_name("events.json")
_LOCK = threading.Lock()
_CACHE: dict[tuple, object] = {}


class StaticUnavailable(RuntimeError):
    pass


class Grid:
    """Model grid: the A06/A23 600 m pilot (static_meta.json) or an A25 bundle grid (meta.json + cell indices)."""

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        npz = self.directory / "static.npz"
        if (self.directory / "static_meta.json").exists():
            self.kind, meta = "a06", self.directory / "static_meta.json"
        else:
            self.kind, meta = "a25", self.directory / "meta.json"
        if not npz.exists() or not meta.exists():
            raise StaticUnavailable(f"model grid is not installed ({self.directory.name})")
        with np.load(npz, allow_pickle=False) as bundle:
            self.arrays = {key: bundle[key] for key in bundle.files}
        self.meta = json.loads(meta.read_text(encoding="utf-8"))
        self.active = self.arrays["active"].astype(bool)
        self.drain = self.arrays["drain"].astype(bool)
        self.shape = self.active.shape
        g = self.meta["grid"]
        self.cell_size_m = float(g["cell_size_m"])
        if self.kind == "a25":
            self.transform = [self.cell_size_m, 0.0, float(g["origin_x_m"]), 0.0, -self.cell_size_m, float(g["origin_y_m"])]
            self.bundle_sha256 = None
            self.version = self.meta.get("static_assets_version")
        else:
            self.transform = g["transform"]
            self.bundle_sha256 = self.meta.get("bundle_sha256")
            self.version = None
        self._shelter_cells = None

    def grid_spec(self) -> dict:
        if self.kind == "a25":
            return dict(self.meta["grid"])
        a, _, c, _, e, f = self.transform
        corners = self.meta["grid"].get("corners_lonlat")
        if corners:
            lons, lats = [p[0] for p in corners], [p[1] for p in corners]
            bbox = [min(lons), min(lats), max(lons), max(lats)]
        else:
            bbox = self.meta["grid"]["bounds_lonlat"]
        size = self.cell_size_m
        return {"crs": "EPSG:32644", "origin_x_m": float(c), "origin_y_m": float(f),
                "cell_size_m": int(size) if float(size).is_integer() else size,
                "rows": int(self.shape[0]), "cols": int(self.shape[1]), "bbox_wgs84": [round(v, 6) for v in bbox]}

    @property
    def bounds_lonlat(self) -> list[float]:
        g = self.meta["grid"]
        return g.get("bounds_lonlat") or g["bbox_wgs84"]

    # Cell lookups onto this grid (A25 ships its own; the A06 pilot uses the product bundle's 600 m mapping).
    def seg_cell(self, product: "Product") -> np.ndarray:
        return self.arrays["road_cell"] if "road_cell" in self.arrays else product.roads["seg_cell"]

    def building_cell(self, product: "Product") -> np.ndarray:
        return self.arrays["building_cell"] if "building_cell" in self.arrays else product.buildings["cell"]

    def shelter_cells(self, product: "Product") -> list[int]:
        if self._shelter_cells is None:
            if "shelter_cell" in self.arrays:
                with np.load(self.directory.parent / "shared" / "shelters.npz", allow_pickle=False) as z:
                    lookup = dict(zip((str(i) for i in z["shelter_id"]), self.arrays["shelter_cell"].tolist()))
                self._shelter_cells = [int(lookup[s["shelter_id"]]) if s["shelter_id"] in lookup
                                       else self.cells_near(s["lon"], s["lat"], strict=True) for s in product.shelters]
            else:
                self._shelter_cells = [int(s["cell"]) for s in product.shelters]
        return self._shelter_cells

    def ward_at(self, cells) -> list:
        """GCC ward_id (1-200) at grid cells, None where unknown/outside GCC or no ward grid is installed."""
        cells = np.atleast_1d(np.asarray(cells, dtype=np.int64))
        if "ward_id" not in self.arrays:
            return [None] * len(cells)
        flat = self.arrays["ward_id"].ravel()
        values = np.where(cells >= 0, flat[np.clip(cells, 0, None)], 0)
        return [int(v) if v > 0 else None for v in values]

    def cell_lonlat(self, cell: int) -> tuple[float, float]:
        r, c = divmod(int(cell), self.shape[1])
        return float(self.arrays["cell_lon"][r, c]), float(self.arrays["cell_lat"][r, c])

    def cells_near(self, lon: float, lat: float, strict: bool = False) -> int:
        d = (self.arrays["cell_lon"] - lon) ** 2 + (self.arrays["cell_lat"] - lat) ** 2
        cell = int(np.argmin(d))
        if strict and math.sqrt(float(d.ravel()[cell])) * 111320 > self.cell_size_m:
            return -1
        return cell


class Product:
    """Compact OSM/A08-derived bundle built by build_static.py."""

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        manifest = self.directory / "manifest.json"
        if not manifest.exists():
            raise StaticUnavailable("product static bundle is not installed")
        self.manifest = json.loads(manifest.read_text(encoding="utf-8"))
        self.version = self.manifest.get("version")

    @cached_property
    def roads(self) -> dict:
        with np.load(self.directory / "roads.npz", allow_pickle=False) as bundle:
            return {key: bundle[key] for key in bundle.files}

    @cached_property
    def buildings(self) -> dict:
        with np.load(self.directory / "buildings.npz", allow_pickle=False) as bundle:
            data = {key: bundle[key] for key in bundle.files}
        levels = data["levels"]
        has = np.isfinite(levels) & (levels > 0)
        data["height_m"] = np.where(has, levels * 3.0, 6.0).astype(np.float32)
        data["height_source"] = np.where(has, 1, 2).astype(np.uint8)  # 1 osm_levels, 2 estimated
        return data

    @cached_property
    def shelters(self) -> list[dict]:
        return json.loads((self.directory / "shelters.json").read_text(encoding="utf-8"))


def _cached(key: tuple, factory):
    with _LOCK:
        if key not in _CACHE:
            _CACHE[key] = factory()
        return _CACHE[key]


def _stamp(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return -1.0


def grid(resolution: str = "citywide", focus_area: str | None = None) -> Grid:
    directory = config.grid_static_dir(resolution, focus_area)
    return _cached(("grid", str(directory), _stamp(directory / "static.npz")), lambda: Grid(directory))


def product() -> Product:
    directory = config.product_static_dir()
    return _cached(("product", str(directory), _stamp(directory / "manifest.json")), lambda: Product(directory))


def grid_available(resolution: str = "citywide", focus_area: str | None = None) -> bool:
    try:
        grid(resolution, focus_area)
        return True
    except StaticUnavailable:
        return False


def product_available() -> bool:
    try:
        product()
        return True
    except StaticUnavailable:
        return False


def wards_available() -> bool:
    """GCC ward boundaries arrive with A25; until then ward operations answer 503."""
    try:
        return "ward_id" in grid().arrays and geojson_layer("wards") is not None
    except StaticUnavailable:
        return False


def geojson_layer(layer: str) -> dict | None:
    """wards.geojson / focus_areas.geojson shipped with an A25 grid bundle (None until installed)."""
    try:
        directory = grid().directory
    except StaticUnavailable:
        return None
    path = directory / f"{layer}.geojson"
    if not path.exists():
        path = directory.parent / "shared" / f"{layer}.geojson"  # A25 bundle layout
    if not path.exists():
        return None
    return _cached(("geojson", str(path), _stamp(path)), lambda: json.loads(path.read_text(encoding="utf-8")))


def ward_names(g: Grid) -> dict[int, tuple[str, str | None]]:
    collection = geojson_layer("wards") or {"features": []}
    names = {}
    for feature in collection["features"]:
        props = feature.get("properties") or {}
        if props.get("ward_id") is not None:
            names[int(props["ward_id"])] = (str(props.get("ward_name") or f"Ward {props['ward_id']}"), props.get("zone"))
    for ward_id in np.unique(g.arrays["ward_id"]):
        if int(ward_id) > 0 and int(ward_id) not in names:
            names[int(ward_id)] = (f"Ward {int(ward_id)}", None)
    return names


def events() -> list[dict]:
    """Saved event forcing of the active engine: A25's catalogue when installed, else the A06 set built here."""
    path = config.a25_root() / "shared" / "events.json" if config.a25_enabled() else EVENTS_FILE
    return _cached(("events", str(path), _stamp(path)), lambda: json.loads(path.read_text(encoding="utf-8"))["events"])


def clear_cache() -> None:
    with _LOCK:
        _CACHE.clear()
