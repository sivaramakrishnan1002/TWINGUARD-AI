from pathlib import Path

from pipelines.labels.sar_diagnostic_v2 import run


def test_diagnostic_uses_matched_cells_and_reports_direction_and_shifts():
    root = Path(__file__).resolve().parents[2]
    result = run(root)
    counts = result["counts"]
    assert counts["matched_positive"] == counts["matched_negative"]
    assert counts["unmatched_positive_strata"] == 0
    assert result["grid_alignment"]["label"]["crs"] == "EPSG:32644"
    assert result["auc"]["VV event dB"]["flood_direction"] == "lower"
    assert result["auc"]["VV event dB"]["direction_aware_auc"] >= 0.7
    shift = result["label_shift_overlap_iou"]
    assert shift["1"]["iou_cardinal_mean"] > shift["2"]["iou_cardinal_mean"] > shift["3"]["iou_cardinal_mean"]
