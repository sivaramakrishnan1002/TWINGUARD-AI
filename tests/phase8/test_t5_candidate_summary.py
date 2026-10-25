from pathlib import Path

import numpy as np

from pipelines.phase8.evaluate_t5_candidates import parse_kml_point_coords, stats


def test_stats_reports_distribution_and_empty_values():
    result = stats(np.array([1.0, 2.0, 3.0, np.nan]))
    assert result["count"] == 3
    assert result["median"] == 2.0
    assert stats(np.array([np.nan]))["count"] == 0


def test_kml_parser_reads_point_coords_only(tmp_path: Path):
    path = tmp_path / "tiny.kml"
    path.write_text("""<kml xmlns=\"http://www.opengis.net/kml/2.2\"><Document>
      <Placemark><Point><coordinates>80.1,13.0,0</coordinates></Point></Placemark>
      <Placemark><LineString><coordinates>80.2,13.1,0 80.3,13.2,0</coordinates></LineString></Placemark>
    </Document></kml>""", encoding="utf-8")
    assert parse_kml_point_coords(path) == [(80.1, 13.0)]
