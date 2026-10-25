import numpy as np
from pipelines.phase9c.calibrated_sar_candidate import buffered_train_test,choose_threshold,metric_row


def test_buffer_removes_adjacent_block_rows_and_columns():
    groups=np.array([1,2,3,4,5,6]); tiles={1:(0,0),2:(0,1),3:(0,2),4:(1,1),5:(2,2),6:(3,3)}
    train=np.array([0,2,3,4,5]);test=np.array([1])
    tr,te=buffered_train_test(train,test,groups,tiles)
    assert groups[te].tolist()==[2]
    assert 1 not in groups[tr] and 3 not in groups[tr] and 4 not in groups[tr]
    assert 5 in groups[tr] and 6 in groups[tr]


def test_threshold_is_selected_from_training_labels_only():
    t,iou=choose_threshold(np.array([0,0,1,1]),np.array([.1,.2,.7,.8]))
    assert .2<t<=.7 and iou==1.0


def test_metrics_use_true_prevalence_and_confusion_counts():
    y=np.array([1,0,1,0]);p=np.array([.9,.2,.7,.8]);m=metric_row(y,p,.5)
    assert m['prevalence']==.5 and m['confusion_matrix']=={'tn':1,'fp':1,'fn':0,'tp':2}
    assert m['iou']==2/3
