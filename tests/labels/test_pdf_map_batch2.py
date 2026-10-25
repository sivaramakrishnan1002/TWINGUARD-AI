import numpy as np
from pipelines.labels.pdf_map_batch2 import red_class


def test_red_class_matches_legend_red_not_gray_or_black():
    a=np.array([[[255,0,0],[255,120,120],[160,20,20],[100,100,100],[0,0,0]]],dtype=np.uint8)
    assert red_class(a).tolist()==[[True,True,False,False,False]]

