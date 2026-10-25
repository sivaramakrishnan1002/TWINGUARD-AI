import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from pipelines.labels.manual_map_loader import classify_tier, create_empty_template, validate_layer


def test_one_grid_cell_rmse_is_tier_b_and_above_is_c():
    assert classify_tier(30.0) == "B"
    assert classify_tier(30.001) == "C"


@pytest.mark.parametrize("value", [-0.1, float("nan"), float("inf")])
def test_invalid_rmse_rejected(value):
    with pytest.raises(ValueError):
        classify_tier(value)


def _rows(geometry, crs="EPSG:32644"):
    return gpd.GeoDataFrame([{
        "event": "2015-12", "map_date": "2015-12-06", "source": "manual-test-map.pdf",
        "digitiser": "tester", "confidence": "medium", "notes": "fixture",
        "georef_rmse_m": 30, "created": "2026-10-25T00:00:00Z", "geometry": geometry,
    }], crs=crs)


def test_valid_polygon_produces_tier_b_record():
    record = validate_layer(_rows(Polygon([(0, 0), (30, 0), (30, 30), (0, 30)])))[0]
    assert record["tier"] == "B"
    assert record["event_date"].isoformat() == "2015-12-06"
    assert record["label_key"].startswith("manual-map:")


def test_invalid_geometry_and_wrong_crs_are_rejected():
    bow_tie = Polygon([(0, 0), (30, 30), (0, 30), (30, 0), (0, 0)])
    with pytest.raises(ValueError, match="invalid geometry"):
        validate_layer(_rows(bow_tie))
    with pytest.raises(ValueError, match="EPSG:32644"):
        validate_layer(_rows(Polygon([(0, 0), (1, 0), (1, 1)]), crs="EPSG:4326"))


def test_empty_template_schema(tmp_path):
    path = tmp_path / "digitised_labels.gpkg"
    create_empty_template(path)
    template = gpd.read_file(path, layer="digitised_labels")
    assert len(template) == 0
    assert template.crs.to_epsg() == 32644
    assert set(["event", "map_date", "source", "digitiser", "confidence", "notes", "georef_rmse_m", "created"]) <= set(template.columns)
