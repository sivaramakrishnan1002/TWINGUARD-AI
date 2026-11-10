"""Shared helpers for C4 v3 tests: a small JSON-Schema validator over docs/api/ai-service.yaml and a synthetic fixture."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SPEC = json.loads((ROOT / "docs/api/ai-service.yaml").read_text(encoding="utf-8"))


def v3_section() -> dict:
    """C4 v3 operations: the proposed section plus any already promoted into top-level paths."""
    section = SPEC["x-c4-v3-product-api"]
    # planned/proposed ops are tested before they move (B49, B51)
    paths = {**section.get("planned_paths", {}), **section.get("proposed_paths", {}), **section["paths"]}
    for path, item in SPEC.get("paths", {}).items():
        if path.startswith("/v3/"):
            paths[path] = item
    return {"paths": paths, "schemas": section["components"]["schemas"]}


def _resolve(ref: str) -> dict:
    node = SPEC
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def validate(value, schema: dict, path: str = "$") -> list[str]:
    """Subset of JSON Schema 2020-12 used by the C4 v3 contract."""
    if "$ref" in schema:
        return validate(value, _resolve(schema["$ref"]), path)
    errors: list[str] = []
    if "oneOf" in schema:
        matches = [s for s in schema["oneOf"] if not validate(value, s, path)]
        if len(matches) != 1:
            errors.append(f"{path}: matches {len(matches)} oneOf branches")
        return errors
    if "anyOf" in schema:
        if not any(not validate(value, s, path) for s in schema["anyOf"]):
            errors.append(f"{path}: matches no anyOf branch")
        return errors
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: {value!r} != const {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in {schema['enum']}")
    kinds = schema.get("type")
    if kinds is not None:
        kinds = kinds if isinstance(kinds, list) else [kinds]
        ok = False
        for kind in kinds:
            if kind == "integer":
                ok |= isinstance(value, int) and not isinstance(value, bool)
            elif kind == "number":
                ok |= isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
            else:
                ok |= isinstance(value, TYPES[kind])
        if not ok:
            return errors + [f"{path}: {type(value).__name__} is not {kinds}"]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} > maximum {schema['maximum']}")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: {value!r} does not match {schema['pattern']}")
        if schema.get("format") == "date-time" and not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$", value):
            errors.append(f"{path}: {value!r} is not RFC 3339 UTC")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: more than {schema['maxItems']} items")
        if "items" in schema:
            for i, item in enumerate(value[:200]):
                errors += validate(item, schema["items"], f"{path}[{i}]")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required {key!r}")
        props = schema.get("properties", {})
        for key, item in value.items():
            if key in props:
                errors += validate(item, props[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected property {key!r}")
            elif isinstance(schema.get("additionalProperties"), dict):
                errors += validate(item, schema["additionalProperties"], f"{path}.{key}")
    return errors


def response_schema(path: str, method: str, status: int) -> dict:
    op = v3_section()["paths"][path][method.lower()]
    content = op["responses"][str(status)]["content"]["application/json"]
    return content["schema"]


def assert_contract(response, path: str, method: str = "get") -> dict:
    body = response.json()
    errors = validate(body, response_schema(path, method, response.status_code))
    assert not errors, errors[:10]
    return body


# --------------------------------------------------------------------------------------------- synthetic fixture
ROWS, COLS = 10, 12
LON0, LAT0, STEP = 80.20, 13.05, 0.0055


def build_fixture(root: Path) -> tuple[Path, Path]:
    """A 10x12 600 m grid with a central depression, a drain column on the east edge and a road lattice."""
    grid_dir, product_dir = root / "grid", root / "product"
    grid_dir.mkdir(parents=True)
    product_dir.mkdir(parents=True)
    r, c = np.mgrid[0:ROWS, 0:COLS]
    z = 6.0 + 0.15 * c - 2.5 * np.exp(-(((r - 5) ** 2) + ((c - 5) ** 2)) / 6.0)
    drain = c == COLS - 1
    active = ~drain
    lon = LON0 + c * STEP
    lat = LAT0 - r * STEP
    np.savez_compressed(
        grid_dir / "static.npz", z=z, active=active, drain=drain, mann=np.full(z.shape, 0.05), porosity=np.ones(z.shape),
        landcover=np.full(z.shape, 50, np.int16), population=np.full(z.shape, 1200.0),
        population_nodata_cells=np.zeros(z.shape, np.int32), road_length_m=np.full(z.shape, 1000.0), cell_lon=lon, cell_lat=lat)
    meta = {"schema": "twinguard.live_static.v1", "bundle_sha256": "f" * 64,
            "grid": {"rows": ROWS, "cols": COLS, "cell_size_m": 600, "crs": "EPSG:32644",
                     "transform": [600.0, 0.0, 390000.0, 0.0, -600.0, 1471620.0],
                     "corners_lonlat": [[LON0, LAT0], [LON0 + COLS * STEP, LAT0], [LON0 + COLS * STEP, LAT0 - ROWS * STEP], [LON0, LAT0 - ROWS * STEP]],
                     "bounds_lonlat": [LON0, LAT0 - ROWS * STEP, LON0 + COLS * STEP, LAT0]}}
    (grid_dir / "static_meta.json").write_text(json.dumps(meta), encoding="utf-8")

    node_id = lambda rr, cc: rr * COLS + cc  # noqa: E731 - one road node per cell centre
    node_lon, node_lat = lon.ravel().astype(float), lat.ravel().astype(float)
    segs = []
    for rr in range(ROWS):
        for cc in range(COLS - 1):
            segs.append((node_id(rr, cc), node_id(rr, cc + 1)))
    for rr in range(ROWS - 1):
        for cc in range(COLS - 1):
            segs.append((node_id(rr, cc), node_id(rr + 1, cc)))
    seg_a = np.array([s[0] for s in segs])
    seg_b = np.array([s[1] for s in segs])
    structure = np.zeros(len(segs), np.uint8)
    structure[0] = 2  # one bridge: always UNKNOWN
    coords_lon = np.column_stack([node_lon[seg_a], node_lon[seg_b]]).ravel().astype(np.float32)
    coords_lat = np.column_stack([node_lat[seg_a], node_lat[seg_b]]).ravel().astype(np.float32)
    length = np.full(len(segs), 600.0, np.float32)
    np.savez_compressed(
        product_dir / "roads.npz", node_lon=node_lon, node_lat=node_lat, node_x=np.zeros(len(node_lon)), node_y=np.zeros(len(node_lon)),
        seg_cell=seg_a.astype(np.int32), seg_structure=structure, seg_highway=np.zeros(len(segs), np.uint8), seg_length_m=length,
        seg_mid_lon=((node_lon[seg_a] + node_lon[seg_b]) / 2).astype(np.float32), seg_mid_lat=((node_lat[seg_a] + node_lat[seg_b]) / 2).astype(np.float32),
        seg_coord_offsets=np.arange(0, 2 * len(segs) + 1, 2, dtype=np.int64), seg_coord_lon=coords_lon, seg_coord_lat=coords_lat,
        arc_from=np.concatenate([seg_a, seg_b]).astype(np.int32), arc_to=np.concatenate([seg_b, seg_a]).astype(np.int32),
        arc_segment=np.concatenate([np.arange(len(segs)), np.arange(len(segs))]).astype(np.int32),
        arc_length_m=np.concatenate([length, length]), arc_speed_kmh=np.full(2 * len(segs), 30.0, np.float32),
        highway_names=np.array(["residential"]), structure_names=np.array(["ordinary", "tunnel_underpass_proxy", "bridge", "bridge_and_tunnel", "unassessed"]))
    n = ROWS * COLS
    ring_lon = np.repeat(node_lon, 5).astype(np.float32)
    ring_lat = np.repeat(node_lat, 5).astype(np.float32)
    np.savez_compressed(
        product_dir / "buildings.npz", fid=np.arange(1, n + 1), osmid=np.arange(n), lon=node_lon, lat=node_lat,
        cell=np.where(active.ravel(), np.arange(n), -1).astype(np.int32), levels=np.where(np.arange(n) % 2 == 0, 2.0, np.nan).astype(np.float32),
        ring_offsets=np.arange(0, 5 * n + 1, 5, dtype=np.int64), ring_lon=ring_lon, ring_lat=ring_lat)
    shelters = [
        {"shelter_id": "osm:1", "name": "High school", "category": "school", "lon": float(lon[1, 1]), "lat": float(lat[1, 1]),
         "cell": node_id(1, 1), "capacity_people": 250, "capacity_source": "assumed"},
        {"shelter_id": "osm:2", "name": "Valley college", "category": "college", "lon": float(lon[5, 5]), "lat": float(lat[5, 5]),
         "cell": node_id(5, 5), "capacity_people": 500, "capacity_source": "assumed"},
        {"shelter_id": "osm:3", "name": "East shelter", "category": "shelter", "lon": float(lon[8, 9]), "lat": float(lat[8, 9]),
         "cell": node_id(8, 9), "capacity_people": 100, "capacity_source": "assumed"},
    ]
    (product_dir / "shelters.json").write_text(json.dumps(shelters), encoding="utf-8")
    (product_dir / "manifest.json").write_text(json.dumps({"schema": "twinguard.v3_product_static.v1", "version": "fixture0001"}), encoding="utf-8")
    return grid_dir, product_dir


def custom_request(values=None, hours: int = 6) -> dict:
    return {"mode": "custom", "duration_hours": hours, "frame_interval_minutes": 30,
            "custom_rainfall": {"start_time_utc": "2026-11-07T00:00:00Z", "interval_minutes": 30,
                                "values_mm": values if values is not None else [20.0] * 6}}
