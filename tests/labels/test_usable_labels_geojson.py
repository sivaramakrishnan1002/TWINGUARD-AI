from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from shapely.geometry import GeometryCollection, Point, Polygon, box
from shapely import to_wkb

from pipelines.labels.export_usable_labels_geojson import (
    ACCEPTED_TIERS,
    PROPERTY_NAMES,
    build_collection,
    serialize_row,
)


def row(*, tier="A", role="event_flood", geom=None, **overrides):
    item = {
        "label_key": f"key-{tier}-{role}",
        "event_date": date(2015, 11, 24),
        "method": "UNOSAT reference",
        "reference_role": role,
        "tier": tier,
        "is_derived": False,
        "is_valid": True,
        "in_cma": True,
        "source_id": "source-1",
        "source_sha256": "a" * 64,
        "loader": "fixture-loader",
        "load_time": datetime(2026, 10, 22, 12, 47, 3, tzinfo=timezone(timedelta(hours=5, minutes=30))),
        "geom_wkb": to_wkb(geom if geom is not None else box(400000, 1400000, 400030, 1400030)),
    }
    item.update(overrides)
    return item


def test_feature_properties_geometry_and_utc_time():
    feature, reason = serialize_row(row())
    assert reason is None
    assert feature["type"] == "Feature"
    assert set(feature["properties"]) == set(PROPERTY_NAMES)
    assert feature["properties"]["event_date"] == "2015-11-24"
    assert feature["properties"]["load_time"] == "2026-10-22T07:17:03.000000Z"
    assert feature["geometry"]["type"] == "Polygon"
    coordinates = feature["geometry"]["coordinates"][0][0]
    assert -180 <= coordinates[0] <= 180 and -90 <= coordinates[1] <= 90


def test_accepts_a_b_c_tiers_and_keeps_baseline_role_distinct():
    inputs = [row(tier=tier, role="baseline_water") for tier in sorted(ACCEPTED_TIERS)]
    collection, qa = build_collection(inputs)
    assert len(collection["features"]) == 3
    assert all(f["properties"]["reference_role"] == "baseline_water" for f in collection["features"])
    assert all(f["properties"]["tier"] in ACCEPTED_TIERS for f in collection["features"])
    assert qa["rejected_rows"] == 0


def test_filters_unaccepted_and_flagged_rows_with_reasons():
    inputs = [
        row(tier="D"),
        row(is_valid=False),
        row(in_cma=False),
        row(reference_role="modelled"),
    ]
    collection, qa = build_collection(inputs)
    assert collection["features"] == []
    assert [r["reason"] for r in qa["rejections"]] == [
        "tier_not_accepted_A_B_C", "row_not_marked_valid", "row_not_marked_in_cma", "reference_role_not_supported"
    ]


def test_unknown_provenance_is_null_not_invented():
    feature, reason = serialize_row(row(source_id=None, source_sha256=None, loader=None, method=None))
    assert reason is None
    assert feature["properties"]["source_id"] is None
    assert feature["properties"]["source_sha256"] is None
    assert feature["properties"]["loader"] is None
    assert feature["properties"]["method"] is None


def test_rejects_null_empty_invalid_and_nonpolygon_geometry():
    candidates = [
        row(geom_wkb=None),
        row(geom=Polygon()),
        row(geom=Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])),
        row(geom=Point(400000, 1400000)),
        row(geom=GeometryCollection([box(400000, 1400000, 400030, 1400030)])),
    ]
    reasons = [serialize_row(candidate)[1] for candidate in candidates]
    assert reasons == ["geometry_null", "geometry_empty", "geometry_invalid", "geometry_not_polygonal", "geometry_not_polygonal"]


def test_rejects_timezone_naive_load_time():
    try:
        serialize_row(row(load_time=datetime(2026, 1, 1)))
    except ValueError as exc:
        assert "timezone-naive" in str(exc)
    else:
        raise AssertionError("Naive load_time must not be assigned an invented timezone")
