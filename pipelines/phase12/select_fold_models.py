"""Select parameters and depth cut-points on training blocks only."""
import json
from pathlib import Path
import numpy as np
from sklearn.isotonic import IsotonicRegression
from .simulate import ROOT,OUTPUT,load_static,folds,metrics

THRESHOLDS=(.01,.03,.05,.10,.15,.30,.50)

def run(output=OUTPUT,filename='selected_model_spatialcv.json'):
    target=output/filename
    if target.exists():raise FileExistsError(f'refusing to overwrite {target}')
    data=load_static();split=folds(data['blocks'],data['eligible']);result={'seed':20261026,'fold_design':'5-fold spatial block CV; 3 km buffer around held-out blocks; member, threshold and isotonic calibrator fit on training blocks only','events':{}}
    for event,key in [('2015-11-12','target_2015_11_12'),('2015-11-24','target_2015_11_24')]:
        with np.load(output/f'member_peak_depth_{event}_DERIVED.npz') as z: depth=z['depth_m']
        y=(data['labels'][key]>=.10).astype(np.uint8);fold_rows=[]
        for fold,(train,test) in enumerate(split,1):
            best=None
            for member in range(depth.shape[0]):
                best_member=(-1.,None)
                for th in THRESHOLDS:
                    pred=depth[member]>=th;tp=int(np.sum(pred&y&train));fp=int(np.sum(pred&~y.astype(bool)&train));fn=int(np.sum(~pred&y&train));iou=tp/max(tp+fp+fn,1)
                    if iou>best_member[0]:best_member=(iou,th)
                candidate=(best_member[0],-member,best_member[1],member)
                if best is None or candidate>best:best=candidate
            train_iou,_,threshold,member=best
            calibrator=IsotonicRegression(out_of_bounds='clip').fit(depth[member][train],y[train])
            mask=test&data['eligible'];prob=calibrator.predict(depth[member][mask]);truth=y[mask]
            m=metrics(truth,depth[member][mask],prob);pred=depth[member][mask]>=threshold
            tp=int(np.sum(pred&(truth==1)));fp=int(np.sum(pred&(truth==0)));fn=int(np.sum(~pred&(truth==1)))
            m.update({'fold':fold,'selected_member_id':member+1,'training_iou':float(train_iou),'threshold_m':float(threshold),'f1':2*tp/max(2*tp+fp+fn,1),'iou':tp/max(tp+fp+fn,1),'test_cells':int(mask.sum())});fold_rows.append(m)
        result['events'][event]={'folds':fold_rows,'median_training_threshold_m':float(np.median([r['threshold_m'] for r in fold_rows])),'selected_members':[r['selected_member_id'] for r in fold_rows],'training_rule':'choose the member and one of seven thresholds maximizing training-block IoU; fit isotonic calibration on training depths and labels; evaluate once on held-out blocks'}
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,default=OUTPUT);a=p.parse_args();out=a.output_dir if a.output_dir.is_absolute() else ROOT/a.output_dir
    r=run(out);print(json.dumps({k:{'folds':v['folds'],'median_threshold_m':v['median_training_threshold_m']} for k,v in r['events'].items()},indent=2))
