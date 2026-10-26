"""Training-fold-only recalibration of the saved A06 depth ensembles."""
import json
from pathlib import Path
import numpy as np
from .simulate import ROOT,OUTPUT,load_static,folds,cv_member

def run(output=OUTPUT):
    target=output/'calibrated_metrics_spatialcv.json'
    if target.exists():raise FileExistsError(f'refusing to overwrite {target}')
    data=load_static(); split=folds(data['blocks'],data['eligible']); events={}
    for event,key in [('2015-11-12','target_2015_11_12'),('2015-11-24','target_2015_11_24')]:
        with np.load(output/f'member_peak_depth_{event}_DERIVED.npz') as archive: depth=archive['depth_m']
        member_results=[]
        for i in range(depth.shape[0]):
            rows,threshold=cv_member(depth[i],data['eligible'],data['labels'][key],split)
            member_results.append({'member':i+1,'threshold_m':threshold,'folds':rows})
        fold_metrics=[]
        for f in range(5):
            row={}
            for metric in ('roc_auc','pr_auc','brier','ece','f1','iou','prevalence'):
                row[metric]=float(np.nanmean([m['folds'][f][metric] for m in member_results]))
            row['fold']=f+1;fold_metrics.append(row)
        thresholds=[m['threshold_m'] for m in member_results]
        events[event]={'metrics':'AUC from fold-calibrated isotonic probabilities; threshold F1/IoU from training-only depth threshold','folds':fold_metrics,'member_threshold_median_m':float(np.median(thresholds)),'member_threshold_mean_m':float(np.mean(thresholds)),'member_threshold_sd_m':float(np.std(thresholds,ddof=1)),'member_metrics':member_results}
    result={'status':'recalibrated summary; original simulation arrays unchanged','seed':20261026,'fold_design':'5-fold spatial block; 3 km test buffer; fitting and threshold selection use training cells only','events':events}
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,default=OUTPUT);a=p.parse_args();path=a.output_dir if a.output_dir.is_absolute() else ROOT/a.output_dir
    r=run(path);print(json.dumps({k:{'folds':v['folds'],'threshold_median_m':v['member_threshold_median_m'],'threshold_sd_m':v['member_threshold_sd_m']} for k,v in r['events'].items()},indent=2))
