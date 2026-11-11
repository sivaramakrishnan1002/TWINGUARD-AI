"""B57: missing OSM shelter names (NaN, None, empty, literal "nan") get a stable fallback, never "nan"."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "ai-service"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v3_support import assert_contract, build_fixture, custom_request  # noqa: E402

from app import main  # noqa: E402
from app.v3 import static  # noqa: E402
from app.v3.runs import MANAGER  # noqa: E402

RUN = "/v3/simulations/{run_id}"


@pytest.mark.parametrize("name,expected", [
    (float("nan"), "Unnamed college (osm:9)"),
    (None, "Unnamed college (osm:9)"),
    ("", "Unnamed college (osm:9)"),
    ("  ", "Unnamed college (osm:9)"),
    ("nan", "Unnamed college (osm:9)"),
    ("NaN", "Unnamed college (osm:9)"),
    ("None", "Unnamed college (osm:9)"),
    (" Valley College ", "Valley College"),
    ("Nandanam Arts College", "Nandanam Arts College"),  # starts with "nan" but is a real name
])
def test_shelter_name_fallback(name, expected):
    assert static.shelter_name(name, "college", "osm:9") == expected


def test_community_hall_category_label():
    assert static.shelter_name(None, "community_hall", "osm:7") == "Unnamed community hall (osm:7)"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    grid_dir, product_dir = build_fixture(tmp_path)
    shelters = json.loads((product_dir / "shelters.json").read_text(encoding="utf-8"))
    shelters[0]["name"] = None       # high school (dry, reachable)
    shelters[1]["name"] = math.nan   # valley college (floods -> unreachable incident)
    shelters[2]["name"] = "nan"      # literal string written by the old bundle build
    (product_dir / "shelters.json").write_text(json.dumps(shelters), encoding="utf-8")  # writes NaN token for math.nan
    for key, value in {"TWINGUARD_LIVE_STATIC": str(grid_dir), "TWINGUARD_V3_PRODUCT_STATIC": str(product_dir),
                       "TWINGUARD_V3_RUNS": str(tmp_path / "runs"), "TWINGUARD_V3_INLINE_WORKER": "1",
                       "TWINGUARD_V3_MEMBERS": "1", "TWINGUARD_V3_RUN_MIN_INTERVAL_S": "0", "TWINGUARD_V3_ENGINE": "a06",
                       "TWINGUARD_V3_DEVICE_PROBE": "0", "TWINGUARD_V3_LIVE": "0"}.items():
        monkeypatch.setenv(key, value)
    static.clear_cache()
    client = TestClient(main.app)
    run_id = client.post("/v3/simulations", json=custom_request()).json()["run_id"]
    assert MANAGER.wait_idle(60)
    yield client, run_id
    static.clear_cache()


def test_no_nan_names_in_any_response(env):
    client, run_id = env
    report = assert_contract(client.get(RUN.format(run_id=run_id) + "/shelters"), RUN + "/shelters")
    names = {s["shelter_id"]: s["name"] for s in report["shelters"]}
    assert names == {"osm:1": "Unnamed school (osm:1)", "osm:2": "Unnamed college (osm:2)", "osm:3": "Unnamed shelter (osm:3)"}

    incidents = assert_contract(client.get(RUN.format(run_id=run_id) + "/incidents?min_severity=info"), RUN + "/incidents")["incidents"]
    unreachable = [i for i in incidents if i["type"] == "shelter_unreachable"]
    assert unreachable and all("nan" not in i["title"].lower().replace("unnamed", "") for i in unreachable)
    assert any(i["title"] == "Shelter unreachable: Unnamed college (osm:2)" for i in unreachable)

    layer = assert_contract(client.get("/v3/static/shelters"), "/v3/static/{layer}")
    assert {f["properties"]["name"] for f in layer["features"]} == set(names.values())

    blob = json.dumps([report, incidents, layer]).lower()
    assert ": nan" not in blob and '"nan"' not in blob and "nan)" not in blob
