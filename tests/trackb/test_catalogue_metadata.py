from pathlib import Path
import sys

from pydantic import ValidationError
import pytest

AI_SERVICE = Path(__file__).resolve().parents[2] / "services" / "ai-service"
sys.path.insert(0, str(AI_SERVICE))
from app.database import _layer_payload  # noqa: E402
from app.main import Layer  # noqa: E402


def test_layer_payload_exposes_only_catalogued_metadata_and_evidenced_tile_range():
    payload = _layer_payload((
        "roads", "road_edges", "EPSG:4326", 32644, 15,
        "a" * 64, None, None, "OpenStreetMap ODbL",
    ))

    assert payload["source_crs"] == "EPSG:4326"
    assert payload["target_srid"] == 32644
    assert payload["units"] == {
        "length_m": "m", "speed_kmh": "km/h", "travel_time_min": "min"
    }
    assert payload["zoom"] == {"min": 0, "max": 22}
    assert payload["attribution"] == "OpenStreetMap ODbL"
    assert payload["vintage"] is None
    assert payload["provenance"]["source_url"] is None
    assert payload["nodata"] == "not_declared_in_catalogue"
    assert payload["tile_endpoint_available"] is False
    assert Layer.model_validate(payload)


def test_unknown_layer_marks_units_zoom_and_vintage_unavailable():
    payload = _layer_payload(("unknown", "unmapped_source", "unknown", 32644, 0,
                              "b" * 64, None, None, "unknown"))

    assert payload["units"] == {}
    assert payload["zoom"] is None
    assert payload["vintage"] is None
    assert payload["loaded_row_count"] == 0
    assert payload["tile_endpoint_available"] is False
    Layer.model_validate(payload)


def test_layer_contract_rejects_unverified_zoom_values():
    payload = _layer_payload(("roads", "road_edges", "EPSG:4326", 32644, 1,
                              "c" * 64, None, None, "attribution"))
    payload["zoom"] = {"min": -1, "max": 30}

    with pytest.raises(ValidationError):
        Layer.model_validate(payload)


def test_layer_provenance_is_typed_and_rejects_malformed_hash_or_url():
    payload = _layer_payload(("roads", "road_edges", "EPSG:4326", 32644, 1,
                              "d" * 64, "https://example.invalid/roads", None, "attribution"))
    layer = Layer.model_validate(payload)
    assert str(layer.provenance.source_url) == "https://example.invalid/roads"
    assert layer.provenance.source_sha256 == "d" * 64

    payload["provenance"]["source_sha256"] = "not-a-sha256"
    with pytest.raises(ValidationError):
        Layer.model_validate(payload)

    payload["provenance"] = {"source_sha256": None, "source_url": "not a URL"}
    with pytest.raises(ValidationError):
        Layer.model_validate(payload)


def test_zoom_range_is_ordered_and_tile_endpoint_cannot_be_claimed():
    payload = _layer_payload(("roads", "road_edges", "EPSG:4326", 32644, 1,
                              "e" * 64, None, None, "attribution"))
    payload["zoom"] = {"min": 20, "max": 2}
    with pytest.raises(ValidationError):
        Layer.model_validate(payload)

    payload["zoom"] = {"min": 0, "max": 22}
    payload["tile_endpoint_available"] = True
    with pytest.raises(ValidationError):
        Layer.model_validate(payload)
