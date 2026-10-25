import numpy as np

from pipelines.phase8.evaluate_rule_v2 import assign_tier, score


def test_confusion_metrics_and_iou():
    truth = np.array([True, True, False, False])
    pred = np.array([True, False, True, False])
    result = score(truth, pred)
    assert (result["tp"], result["fp"], result["fn"], result["tn"]) == (1, 1, 1, 1)
    assert result["precision"] == result["recall"] == result["f1"] == 0.5
    assert result["iou"] == 1 / 3


def test_tier_requires_both_area_and_iou_gates():
    assert assign_tier(0.40, 49.08) == "B"
    assert assign_tier(0.40, 49.07) == "D"
    assert assign_tier(0.25, 200.0) == "C"
    assert assign_tier(0.24, 98.16) == "D"
