"""A25 high-resolution engine: solver physics, scenario runs, C4 v3 product shapes and documented rules."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.flood_engine import hires, products, scenario  # noqa: E402

NY, NX, CELL = 12, 14, 120.0
OX, OY = 400000.0, 1450000.0


def _terrain(ny, nx, cell, ox, oy):
    rows, cols = np.indices((ny, nx))
    x = ox + (cols + 0.5) * cell
    y = oy - (rows + 0.5) * cell
    z = 8.0 - (x - OX) / (NX * CELL) * 8.0
    z -= 2.0 * np.exp(-(((x - (OX + 6 * CELL)) / 300) ** 2 + ((y - (OY - 6 * CELL)) / 300) ** 2))
    return z.astype(np.float32), x, y


def _lonlat(x, y):
    return (80.0 + (x - OX) / 108000.0).astype(np.float32), (13.0 + (y - OY) / 110000.0).astype(np.float32)


def _grid_files(d: Path, ny, nx, cell, ox, oy, focus, buildings_xy, roads_mid, shelters_xy):
    d.mkdir(parents=True, exist_ok=True)
    z, x, y = _terrain(ny, nx, cell, ox, oy)
    active = np.ones((ny, nx), bool)
    boundary = np.zeros((ny, nx), bool)
    if focus:
        boundary[0, :] = boundary[-1, :] = boundary[:, 0] = boundary[:, -1] = True
    else:
        boundary[:, -2:] = True
        z[:, -2:] = -1.0
    active &= ~boundary
    lon, lat = _lonlat(x, y)

    def idx(px, py):
        c = np.floor((px - ox) / cell).astype(int)
        r = np.floor((oy - py) / cell).astype(int)
        ok = (r >= 0) & (r < ny) & (c >= 0) & (c < nx)
        i = np.where(ok, r * nx + c, -1)
        i[ok] = np.where(active.ravel()[i[ok]], i[ok], -1)
        return i.astype(np.int32)

    ward = np.where(np.indices((ny, nx))[1] < nx // 2, 1, 2).astype(np.int16)
    arrays = {"z": z, "active": active, "boundary": boundary, "drain": boundary, "mann": np.full((ny, nx), 0.05, np.float32),
              "porosity": np.full((ny, nx), 0.9, np.float32), "infiltration_mm_h": np.full((ny, nx), 0.5, np.float32),
              "landcover": np.full((ny, nx), 50, np.int16), "population": np.where(active, 50.0, np.nan).astype(np.float32),
              "ward_id": np.where(active, ward, 0).astype(np.int16), "cell_lon": lon, "cell_lat": lat,
              "building_cell": idx(*buildings_xy), "road_cell": idx(*roads_mid), "shelter_cell": idx(*shelters_xy)}
    np.savez_compressed(d / "static.npz", **arrays)
    grid = {"crs": "EPSG:32644", "origin_x_m": ox, "origin_y_m": oy, "cell_size_m": int(cell), "rows": ny, "cols": nx,
            "bbox_wgs84": [float(lon.min()), float(lat.min()), float(lon.max()), float(lat.max())]}
    meta = {"grid": grid, "bundle_sha256": "0" * 64, "active_cells": int(active.sum()),
            "inflow_cells": {} if focus else {"CHEMBARAMBAKKAM": {"row": 6, "col": 1, "river": "Adyar River"}}}
    (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


@pytest.fixture(scope="module")
def static_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("a25_static")
    sh = root / "shared"
    sh.mkdir()
    rng = np.random.default_rng(3)
    bx = OX + rng.uniform(0, (NX - 2) * CELL, 60)
    by = OY - rng.uniform(0, NY * CELL, 60)
    blon, blat = _lonlat(bx, by)
    rings = np.stack([np.stack([blon + dx, blat + dy], 1) for dx, dy in ((0, 0), (1e-4, 0), (1e-4, 1e-4), (0, 0))], 1).reshape(-1, 2)
    np.savez_compressed(sh / "buildings.npz", osmid=np.arange(1000, 1060), x=bx, y=by, lon=blon, lat=blat,
                        height_m=np.full(60, 6.4, np.float32), height_source=np.full(60, 2, np.int8), area_m2=np.full(60, 100, np.float32),
                        ward_id=np.where(bx < OX + NX * CELL / 2, 1, 2).astype(np.int16), kind=np.array(["yes"] * 60),
                        ring_offsets=np.arange(0, 61 * 4, 4), ring_lonlat=rings.astype(np.float32))
    # a road grid of horizontal segments between node chains
    seg_x, seg_y, na, nb, lines = [], [], [], [], []
    node = 0
    nodes_xy = []
    for r in range(1, NY - 1, 2):
        for c in range(0, NX - 3):
            x0, x1 = OX + (c + 0.5) * CELL, OX + (c + 1.5) * CELL
            yy = OY - (r + 0.5) * CELL
            seg_x.append((x0 + x1) / 2)
            seg_y.append(yy)
            na.append(r * 100 + c)
            nb.append(r * 100 + c + 1)
            lines.append([_lonlat(np.array([x0]), np.array([yy])), _lonlat(np.array([x1]), np.array([yy]))])
    for r in range(1, NY - 1, 2):  # vertical connectors to make one network
        if r + 2 < NY - 1:
            seg_x.append(OX + 0.5 * CELL)
            seg_y.append(OY - (r + 1.5) * CELL)
            na.append(r * 100)
            nb.append((r + 2) * 100)
            lines.append([_lonlat(np.array([OX + .5 * CELL]), np.array([OY - (r + .5) * CELL])), _lonlat(np.array([OX + .5 * CELL]), np.array([OY - (r + 2.5) * CELL]))])
    seg_x, seg_y = np.array(seg_x), np.array(seg_y)
    ids = sorted(set(na) | set(nb))
    nid = np.array(ids, np.int64)
    nxy = np.array([(OX + ((i % 100) + 0.5) * CELL, OY - ((i // 100) + 0.5) * CELL) for i in ids])
    ll = np.array([[float(p[0][0]), float(p[1][0])] for seg in lines for p in seg], np.float32)
    structure = np.zeros(len(seg_x), bool)
    structure[3] = True
    np.savez_compressed(sh / "roads.npz", osmid=np.arange(len(seg_x)), highway=np.array(["primary"] * len(seg_x)), name=np.array([""] * len(seg_x)),
                        structure=structure, length_m=np.full(len(seg_x), CELL, np.float32), mid_x=seg_x, mid_y=seg_y,
                        ward_id=np.where(seg_x < OX + NX * CELL / 2, 1, 2).astype(np.int16),
                        line_offsets=np.arange(0, 2 * len(seg_x) + 1, 2), line_lonlat=ll)
    np.savez_compressed(sh / "road_topology.npz", node_a=np.array(na), node_b=np.array(nb), node_id=nid, node_x=nxy[:, 0], node_y=nxy[:, 1])
    sx = np.array([OX + 1.5 * CELL, OX + 9.5 * CELL])
    sy = np.array([OY - 1.5 * CELL, OY - 6.5 * CELL])
    slon, slat = _lonlat(sx, sy)
    np.savez_compressed(sh / "shelters.npz", shelter_id=np.array(["osm:1", "osm:2"]), name=np.array(["High School", "Low Hall"]),
                        category=np.array(["school", "community_hall"]), capacity_people=np.array([250, 150], np.int32),
                        x=sx, y=sy, lon=slon, lat=slat, ward_id=np.array([1, 2], np.int16))
    wards = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"ward_id": 1, "ward_name": "Ward 1", "zone": "I Test"}, "geometry": {"type": "Polygon", "coordinates": [[[80, 12.9], [80.01, 12.9], [80.01, 13], [80, 12.9]]]}},
        {"type": "Feature", "properties": {"ward_id": 2, "ward_name": "Ward 2", "zone": "I Test"}, "geometry": {"type": "Polygon", "coordinates": [[[80.01, 12.9], [80.02, 12.9], [80.02, 13], [80.01, 12.9]]]}}]}
    (sh / "wards.geojson").write_text(json.dumps(wards), encoding="utf-8")
    (sh / "focus_areas.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    ev = {"event_key": "2015-12-01", "label": "Test event", "start_utc": "2015-11-30T00:00:00Z", "end_utc": "2015-12-03T00:00:00Z",
          "rainfall_source": "test", "source_mode": "REPLAY", "interval_minutes": 60, "values_mm": [0, 40, 80, 60, 20] + [0] * 67}
    (sh / "events.json").write_text(json.dumps({"events": [ev]}), encoding="utf-8")
    _grid_files(root / "citywide_120m", NY, NX, CELL, OX, OY, False, (bx, by), (seg_x, seg_y), (sx, sy))
    _grid_files(root / "focus_30m_VELACHERY", 24, 24, 30.0, OX + 3 * CELL, OY - 3 * CELL, True, (bx, by), (seg_x, seg_y), (sx, sy))
    return root


def _grid(boundary_cols=2):
    z, _, _ = _terrain(NY, NX, CELL, OX, OY)
    bnd = np.zeros((NY, NX), bool)
    bnd[:, -boundary_cols:] = True
    z[bnd] = -1.0
    return hires.HiresGrid(z, ~bnd, bnd, np.full((NY, NX), 0.05), np.full((NY, NX), 0.8), np.full((NY, NX), 0.5), CELL)


def test_hires_mass_balance_with_sea_boundary_releases_and_tide():
    g = _grid()
    base = hires.run(g, [30.0, 60.0, 10.0], 3600, 6 * 3600, 1800)
    assert base.diagnostics["mass_balance_relative_error"] < 1e-3
    assert base.diagnostics["boundary_net_out_m3"] > 0  # water drains to the sea
    assert base.frames_cm.shape == (13, NY, NX) and (base.frames_cm[:, :, -1] == hires.NODATA_CM).all()
    assert np.isnan(base.peak_m[:, -1]).all() and np.nanmin(base.peak_m) >= 0
    rel = hires.run(g, [30.0, 60.0, 10.0], 3600, 6 * 3600, 1800, inflows=[(6, 1, 50.0)])
    assert rel.diagnostics["inflow_m3"] == pytest.approx(50.0 * 6 * 3600)
    assert rel.diagnostics["mass_balance_relative_error"] < 1e-3
    assert np.nansum(rel.peak_m) > np.nansum(base.peak_m)
    tide = hires.run(g, [0.0], 3600, 3 * 3600, 1800, stage_m=1.5)
    assert np.nanmin(tide.peak_m[:, -3]) > 0.05  # coastal land below the tide stage floods from the sea (z ~ 1.43 m)
    assert np.nanmax(tide.peak_m[:, 0]) == 0.0


def test_hires_is_thread_count_independent():
    g = _grid()
    a = hires.run(g, [50.0, 50.0], 3600, 3 * 3600, 1800, threads=1)
    b = hires.run(g, [50.0, 50.0], 3600, 3 * 3600, 1800, threads=3)
    np.testing.assert_array_equal(a.frames_cm, b.frames_cm)


def test_documented_rules():
    d = np.array([np.nan, 0.0, 0.05, 0.2, 0.7, 1.4])
    assert [scenario.DEPTH_CLASSES[i] for i in scenario.depth_class(d)] == ["unknown", "dry", "lt_0_15", "0_15_to_0_5", "0_5_to_1_0", "gt_1_0"]
    assert scenario.risk_level(1.2, 0.12) == "severe" and scenario.risk_level(0.2, 0.30) == "severe"
    assert scenario.risk_level(0.6, 0.06) == "high" and scenario.risk_level(0.2, 0.0) == "moderate" and scenario.risk_level(0.05, 0.0) == "low"
    assert scenario.risk_level(0.05, 0.04) == "low" and scenario.risk_level(0.05, 0.05) == "moderate"
    frame = np.array([[0, 10], [30, hires.NODATA_CM]], np.uint16)
    state, depth = scenario.road_states(frame, np.array([0, 1, 2, 3, -1, 1], np.int32), np.array([0, 0, 0, 0, 0, 1], bool))
    assert state.tolist() == [0, 0, 1, 2, 2, 2]  # 0.30 m is blocked; NoData, unmapped and structures are UNKNOWN
    assert np.isnan(depth[3]) and np.isnan(depth[5])
    sf = scenario.speed_factor(np.array([0.0, 0.1, 0.29, 0.3]))
    assert sf[0] == pytest.approx(1.0) and 0 < sf[2] < sf[1] < 1 and sf[3] == 0
    from pipelines.a25_hires.build_static import estimate_height
    assert estimate_height("apartments", 300) == 12.0 and estimate_height("yes", 40) == 3.5 and estimate_height("yes", 5000) == 16.0


def test_event_run_outputs_match_c4_v3(static_root, tmp_path):
    runs = tmp_path / "runs"
    doc = scenario.run_scenario(static_root, runs, mode="event", event_key="2015-12-01", duration_hours=6, frame_interval_minutes=30, members=3)
    assert doc["run_id"].startswith("evt-") and doc["state"] == "completed" and doc["source_mode"] == "SIMULATED"
    assert len(doc["frames"]) == 13 and doc["frames"][1]["valid_time_utc"] == "2015-11-30T00:30:00Z" and doc["frames"][1]["elapsed_minutes"] == 30
    assert set(doc["grid"]) >= {"crs", "origin_x_m", "origin_y_m", "cell_size_m", "rows", "cols", "bbox_wgs84"}
    assert len(doc["limitations"]) <= 5 and doc["provenance"]["static_assets_version"] == "a25_static_v1"
    assert all(m["mass_balance_relative_error"] <= 0.01 for m in doc["diagnostics"].values())
    assert doc["summary"]["max_depth_m"] > 0 and doc["summary"]["peak_time_utc"]
    again = scenario.run_scenario(static_root, runs, mode="event", event_key="2015-12-01", duration_hours=6, frame_interval_minutes=30, members=3)
    assert again["cached"] and again["run_id"] == doc["run_id"]
    rid = doc["run_id"]
    peak = products.depth_frame(runs, rid)
    assert peak["unit"] == "m" and peak["rows"] == NY and peak["values"][0][-1] is None and peak["max_value"] > 0
    p95 = products.depth_frame(runs, rid, layer="depth_p95")
    p05 = products.depth_frame(runs, rid, layer="depth_p05")
    assert p95["max_value"] >= peak["max_value"] >= p05["max_value"]
    f3 = products.depth_frame(runs, rid, frame_index=3)
    assert f3["valid_time_utc"] == doc["frames"][3]["valid_time_utc"]
    assert all(v is None or v >= 0 for row in f3["values"] for v in row)
    b = products.buildings_page(static_root, runs, rid, limit=25)
    assert b["count"] == 25 and b["total"] == 60 and b["next_cursor"] == "25"
    item = b["buildings"][0]
    assert item["building_id"].startswith("way/") and item["height_source"] == "estimated" and item["depth_class"] in scenario.DEPTH_CLASSES
    assert products.buildings_page(static_root, runs, rid, cursor="50", limit=25)["next_cursor"] is None
    w = products.wards(runs, rid)
    assert {x["ward_id"] for x in w["wards"]} == {1, 2} and all(x["risk_level"] in {"low", "moderate", "high", "severe"} for x in w["wards"])
    r = products.roads(static_root, runs, rid, frame_index=4)
    states = {f["properties"]["state"] for f in r["features"]}
    assert "UNKNOWN" in states and states <= {"ASSESSED_PASSABLE", "ASSESSED_BLOCKED", "UNKNOWN"}
    unknown = [f for f in r["features"] if f["properties"]["state"] == "UNKNOWN"]
    assert all(f["properties"]["depth_m"] is None for f in unknown)
    strict = products.roads(static_root, runs, rid, frame_index=4, blocked_depth_threshold_m=0.1)
    assert sum(f["properties"]["state"] == "ASSESSED_BLOCKED" for f in strict["features"]) >= sum(f["properties"]["state"] == "ASSESSED_BLOCKED" for f in r["features"])
    s = products.shelters(static_root, runs, rid, capacity_factor=2.0)
    assert s["shelters"][0]["capacity_people"] == 500 and s["totals"]["demand_people"] is not None
    assert s["totals"]["served_people"] + s["totals"]["unserved_people"] + s["totals"]["unreachable_people"] == s["totals"]["demand_people"]
    assert products.static_layer(static_root, "wards")["features"][0]["properties"]["ward_id"] == 1
    assert products.static_layer(static_root, "buildings", limit=10)["next_cursor"] == "10"
    assert products.events(static_root)["events"][0]["event_key"] == "2015-12-01"


def test_what_if_custom_and_focus_runs(static_root, tmp_path):
    runs = tmp_path / "runs"
    base = scenario.run_scenario(static_root, runs, mode="event", event_key="2015-12-01", duration_hours=6)
    wi = scenario.run_scenario(static_root, runs, mode="what_if", duration_hours=6,
                               what_if={"base_run_id": base["run_id"], "rainfall_scale_pct": 150, "reservoir_release_m3s": {"CHEMBARAMBAKKAM": 200}, "tide_offset_m": 0.5})
    assert wi["run_id"].startswith("whatif-") and wi["forcing"]["inflow_cells_used"] == 1 and wi["forcing"]["tide_offset_m"] == 0.5
    assert wi["summary"]["flooded_area_km2"] >= base["summary"]["flooded_area_km2"]
    with pytest.raises(scenario.ScenarioError):
        scenario.run_scenario(static_root, runs, mode="what_if", duration_hours=6, what_if={"base_run_id": base["run_id"], "reservoir_release_m3s": {"VEERANAM": 5}})
    custom = scenario.run_scenario(static_root, runs, mode="custom", duration_hours=6,
                                   custom_rainfall={"start_time_utc": "2026-11-07T00:00:00Z", "interval_minutes": 15, "values_mm": [10] * 8})
    assert custom["run_id"].startswith("sim-") and custom["forcing"]["total_mm_domain_mean"] == pytest.approx(80.0)
    with pytest.raises(scenario.ScenarioError):
        scenario.run_scenario(static_root, runs, mode="custom", duration_hours=6, custom_rainfall={"start_time_utc": "2026-11-07T00:00:00Z", "interval_minutes": 20, "values_mm": [1]})
    focus = scenario.run_scenario(static_root, runs, mode="event", event_key="2015-12-01", duration_hours=6, resolution="focus", focus_area="VELACHERY")
    assert focus["grid"]["cell_size_m"] == 30 and focus["parent_run_id"] == base["run_id"]
    assert products.depth_frame(runs, focus["run_id"])["rows"] == 24
    with pytest.raises(scenario.ScenarioError):
        scenario.run_scenario(static_root, runs, mode="event", event_key="nope", duration_hours=6)
