"""Owner-set scenario resources (SCENARIO_INPUT): a local versioned store, not dispatch data."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone

from . import config

_LOCK = threading.Lock()

# Initial demo set, explicitly scenario inputs (the owner replaces it with PUT /v3/scenario-resources).
DEFAULT_RESOURCES = [
    {"resource_id": "boats-central", "type": "boat", "count": 6, "base": {"name": "Scenario base: Central", "location": {"lon": 80.2707, "lat": 13.0827}}},
    {"resource_id": "boats-south", "type": "boat", "count": 6, "base": {"name": "Scenario base: Velachery", "location": {"lon": 80.2209, "lat": 12.9815}}},
    {"resource_id": "teams-adyar", "type": "rescue_team", "count": 8, "base": {"name": "Scenario base: Adyar", "location": {"lon": 80.2565, "lat": 13.0012}}},
    {"resource_id": "teams-north", "type": "rescue_team", "count": 6, "base": {"name": "Scenario base: Tondiarpet", "location": {"lon": 80.2880, "lat": 13.1270}}},
    {"resource_id": "vehicles-porur", "type": "vehicle", "count": 10, "base": {"name": "Scenario base: Porur", "location": {"lon": 80.1568, "lat": 13.0382}}},
    {"resource_id": "ambulances-central", "type": "ambulance", "count": 8, "base": {"name": "Scenario base: Egmore", "location": {"lon": 80.2610, "lat": 13.0732}}},
    {"resource_id": "pumps-tnagar", "type": "pump", "count": 12, "base": {"name": "Scenario base: T. Nagar", "location": {"lon": 80.2341, "lat": 13.0418}}},
]


class VersionConflict(Exception):
    pass


def _path():
    root = config.runs_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root / "_resources.json"


def _tag(resources: list[dict]) -> list[dict]:
    return [{**r, "source_mode": "SCENARIO_INPUT"} for r in resources]


def get() -> dict:
    with _LOCK:
        try:
            doc = json.loads(_path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            doc = {"version": 0, "updated_at": None, "resources": DEFAULT_RESOURCES}
        doc["resources"] = _tag(doc["resources"])
        return doc


def put(version: int | None, resources: list[dict]) -> dict:
    current = get()
    with _LOCK:
        if version is None or version != current["version"]:
            raise VersionConflict()
        doc = {"version": current["version"] + 1,
               "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "resources": [{k: v for k, v in r.items() if k != "source_mode"} for r in resources]}
        tmp = _path().with_suffix(".tmp")
        tmp.write_text(json.dumps(doc), encoding="utf-8")
        os.replace(tmp, _path())
        doc["resources"] = _tag(doc["resources"])
        return doc
