import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "experiments/temporal_models/batch2_v1"


def test_h1_feasibility_keeps_unscored_metrics_null():
    config = json.loads((RUN / "experiment_config.json").read_text(encoding="utf-8"))
    result = json.loads((RUN / "feasibility_results.json").read_text(encoding="utf-8"))
    assert config["status"] == "NOT_TESTABLE_WITH_CURRENT_ACCEPTED_INDEPENDENT_EVENT_LABELS"
    assert config["model_fit"] is False
    assert config["split_plan"]["eligible_held_out_events"] == 0
    assert result["status"] == "NOT_TESTABLE"
    assert all(
        result["metrics"][key] is None
        for key in ("precision", "recall", "f1", "iou", "csi", "pr_auc")
    )
    assert result["metrics"]["reason"].startswith("Not computed")


def test_only_accepted_november_event_layers_define_candidate_target():
    config = json.loads((RUN / "experiment_config.json").read_text(encoding="utf-8"))
    assert config["target"]["tier"] == "A"
    assert config["target"]["role"] == "event_flood"
    assert config["target"]["event_dates"] == ["2015-11-12", "2015-11-24"]
    assert "baseline_water" in config["target"]["mask"]
    assert config["split_plan"]["current_independent_accepted_flood_event_years"] == [2015]


def test_sar_candidates_and_uncertain_map_sources_are_not_scored_labels():
    config = json.loads((RUN / "experiment_config.json").read_text(encoding="utf-8"))
    sar = next(x for x in config["modalities"] if x["name"] == "sar_only")
    assert sar["scored"] is False
    assert sar["status"] == "excluded_from_scored_comparison"
    assert any("Tier D" in item for item in config["limitations"])
    assert config["model_hashes"] is None
