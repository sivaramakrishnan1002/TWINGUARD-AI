import numpy as np

from pipelines.phase9c.apply_sar_candidate_batch2 import application_valid_mask


def test_application_respects_predeclared_eligibility_and_required_inputs():
    eligible = np.array([True, False, True, True])
    features = np.ones((4, 8), dtype=np.float32)
    features[2, 4] = np.nan  # HAND is intentionally allowed to be missing.
    features[3, 1] = np.nan  # Required SAR data is not allowed to be missing.

    actual = application_valid_mask(eligible, features)

    assert actual.tolist() == [True, False, True, False]


def test_application_rejects_misaligned_feature_arrays():
    try:
        application_valid_mask(np.array([True]), np.ones((2, 8), dtype=np.float32))
    except ValueError as exc:
        assert 'aligned with eligibility' in str(exc)
    else:
        raise AssertionError('misaligned arrays should be rejected')
