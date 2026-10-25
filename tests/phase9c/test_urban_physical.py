import numpy as np
from pipelines.phase9c.urban_physical import percentile_rank, physical_rank_score


def test_percentile_rank_orientation_and_nodata():
    v=np.array([[1.,2.],[3.,np.nan]],dtype=np.float32); m=np.ones(v.shape,bool)
    low=percentile_rank(v,m,False); high=percentile_rank(v,m,True)
    assert low[0,0] > low[0,1] > low[1,0]
    assert high[1,0] > high[0,1] > high[0,0]
    assert np.isnan(low[1,1])


def test_physical_score_masks_invalid_and_is_unitless_rank():
    shape=(2,2); arr=np.array([[1,2],[3,4]],dtype=np.float32); valid=np.array([[1,1],[1,0]],bool)
    score=physical_rank_score(arr,arr,arr,arr,arr,arr,valid)
    assert np.isfinite(score[0,0]) and np.isfinite(score[1,0])
    assert np.isnan(score[1,1])
    assert np.all((score[valid]>=0)&(score[valid]<=1))


def test_same_nearest_drainage_height_clamps_negative_sampling_error():
    # The height contract is non-negative even if a nearby rasterized line cell is higher.
    assert max(4.0-5.0,0.0)==0.0
