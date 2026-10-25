import numpy as np

from pipelines.phase8.depth_fields import NODATA, depth_from_edge_surface


def test_depth_uses_component_edge_and_preserves_extent_nodata():
    dem=np.array([[10.,10.,10.],[10.,3.,10.],[10.,10.,-9999.]],dtype=np.float32)
    flood=np.ones((3,3),dtype=bool)
    mean,p05,p95,meta=depth_from_edge_surface(flood,dem,-9999.,4.0)
    assert mean[1,1]==7.0
    assert p05[1,1]==3.0
    assert p95[1,1]==11.0
    assert mean[2,2]==NODATA
    assert meta["components"]==1
    assert meta["components_used"]==1
    assert meta["dem_error_allowance_m"]==4.0


def test_single_cell_edge_has_zero_depth_and_interval_is_nonnegative():
    dem=np.array([[2.0]],dtype=np.float32)
    mean,p05,p95,_=depth_from_edge_surface(np.array([[True]]),dem,None,4.0)
    assert mean[0,0]==0.0
    assert p05[0,0]==0.0
    assert p95[0,0]==4.0
