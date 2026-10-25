"""Spatial-block diagnostic for an SAR-derived candidate; UNOSAT is not independent truth."""
from __future__ import annotations
import json,sys,time
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
import rasterio
from rasterio.warp import reproject,Resampling
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import average_precision_score,roc_auc_score,brier_score_loss,confusion_matrix
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
OUT=ROOT/'data/features/labels/sar_calibrated_batch2'
REPORT=ROOT/'docs/SAR_CALIBRATED_LABELS_BATCH2.md';METRICS=OUT/'metrics.json';REGISTRY=OUT/'model_registry.json'
SEED=20261025; NEG_RATIO=3; OUTER_FOLDS=5; INNER_FOLDS=3
SAR_DIR=ROOT/'data/processed/sar_work/run_20261025_002401/rtc_aligned'


def buffered_train_test(train_idx,test_idx,groups,tile_rc):
    test_groups=np.unique(groups[test_idx]); test_tiles={tuple(tile_rc[int(g)]) for g in test_groups}
    blocked={int(g) for g in np.unique(groups[train_idx]) if any(abs(tile_rc[int(g)][0]-r)<=1 and abs(tile_rc[int(g)][1]-c)<=1 for r,c in test_tiles)}
    keep=~np.isin(groups[train_idx],list(blocked))
    return train_idx[keep],test_idx



def spatial_column_folds(indices,groups,tile_rc,n_splits):
    """Contiguous east-west spatial bands; all 3 km blocks stay intact."""
    cols=sorted({tile_rc[int(g)][1] for g in np.unique(groups[indices])})
    if len(cols)<n_splits: raise ValueError('not enough distinct spatial block columns for requested folds')
    out=[]
    for chunk in np.array_split(np.asarray(cols),n_splits):
        test_cols=set(int(v) for v in chunk)
        test_mask=np.asarray([tile_rc[int(g)][1] in test_cols for g in groups[indices]],dtype=bool)
        out.append((indices[~test_mask],indices[test_mask]))
    return out


def train_sample(y,idx,seed,neg_ratio=NEG_RATIO):
    pos=idx[y[idx]==1]; neg=idx[y[idx]==0]
    if not len(pos) or not len(neg): raise ValueError('training fold must contain both classes')
    rng=np.random.default_rng(seed); n=min(len(neg),neg_ratio*len(pos)); negs=rng.choice(neg,size=n,replace=False)
    selected=np.concatenate([pos,negs]); weights=np.concatenate([np.ones(len(pos)),np.full(n,len(neg)/n)])
    order=rng.permutation(len(selected)); return selected[order],weights[order]


def choose_threshold(y_true,prob):
    candidates=np.unique(np.concatenate([np.linspace(.01,.99,99),np.quantile(prob,np.linspace(.05,.95,91))]))
    best=(0.5,-1.0)
    for t in candidates:
        pred=prob>=t; tp=np.sum(pred&(y_true==1)); fp=np.sum(pred&(y_true==0)); fn=np.sum(~pred&(y_true==1))
        iou=tp/max(tp+fp+fn,1)
        if iou>best[1]:best=(float(t),float(iou))
    return best


def expected_calibration_error(y,prob,bins=10):
    edges=np.linspace(0,1,bins+1); total=len(y); ece=0.0
    for i in range(bins):
        mask=(prob>=edges[i])&(prob<(edges[i+1] if i<bins-1 else edges[i+1]+1e-12))
        if mask.any(): ece+=(mask.sum()/total)*abs(float(y[mask].mean())-float(prob[mask].mean()))
    return float(ece)


def metric_row(y,p,threshold):
    pred=p>=threshold; tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    return {'n':int(len(y)),'prevalence':float(y.mean()),'threshold':float(threshold),'roc_auc':float(roc_auc_score(y,p)) if len(np.unique(y))>1 else None,
      'pr_auc':float(average_precision_score(y,p)) if y.sum() else None,'f1':float(2*tp/max(2*tp+fp+fn,1)),
      'iou':float(tp/max(tp+fp+fn,1)),'precision':float(tp/max(tp+fp,1)),'recall':float(tp/max(tp+fn,1)),
      'brier':float(brier_score_loss(y,p)),'ece_10_bin':expected_calibration_error(y,p),
      'confusion_matrix':{'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp)}}


def align(path,shape,transform,crs,resampling):
    with rasterio.open(path) as src:
        out=np.full(shape,np.nan,dtype=np.float32)
        reproject(src.read(1),out,src_transform=src.transform,src_crs=src.crs,src_nodata=src.nodata,
                  dst_transform=transform,dst_crs=crs,dst_nodata=np.nan,resampling=resampling)
        return out


def run():
    for p in (REPORT,METRICS,REGISTRY):
        if p.exists():raise FileExistsError(f'Refusing to overwrite {p.relative_to(ROOT)}')
    OUT.mkdir(parents=True,exist_ok=True)
    tic=time.perf_counter()
    with rasterio.open(ROOT/'data/features/terrain/elevation_m.tif') as dem:
        shape=dem.shape; transform=dem.transform; crs=dem.crs
    tab=pq.read_table(ROOT/'data/features/static/cell_table_phase9b_v2.parquet').to_pandas()
    labels=pq.read_table(ROOT/'data/features/predictions/labels_nov2015.parquet').to_pandas()
    if len(tab)!=len(labels) or not np.array_equal(tab.cell_id.to_numpy(),labels.cell_id.to_numpy()):raise ValueError('cell table/label cell_id ordering mismatch')
    row=tab.row.to_numpy(np.int32);col=tab.col.to_numpy(np.int32);n=len(tab)
    def f(name):return tab[name].to_numpy(dtype=np.float32,na_value=np.nan)
    # Raster inputs are bilinear-aligned to the existing 30 m master grid.
    srcs={x:align(SAR_DIR/(x+'.tif'),shape,transform,crs,Resampling.bilinear) for x in [
      '2015-11-24_VV_dB_lee5','2015-11-24_VH_dB_lee5','2015-10-19_VV_dB_lee5','2015-10-19_VH_dB_lee5']}
    hand=align(ROOT/'data/processed/sar_work/hand_d8_100cells_20261025_03_DEFAULT.tif',shape,transform,crs,Resampling.nearest)
    slope_grid=np.full(shape,np.nan,np.float32);slope_grid[row,col]=f('slope_deg')
    # Features in table order. VV/VH and per-polarisation event-minus-reference dB changes.
    features=np.column_stack([
      srcs['2015-11-24_VV_dB_lee5'][row,col],srcs['2015-11-24_VH_dB_lee5'][row,col],
      (srcs['2015-11-24_VV_dB_lee5']-srcs['2015-10-19_VV_dB_lee5'])[row,col],
      (srcs['2015-11-24_VH_dB_lee5']-srcs['2015-10-19_VH_dB_lee5'])[row,col],hand[row,col],f('slope_deg'),
      f('tree_fraction'),f('crop_fraction'),f('grass_fraction'),f('bare_fraction'),f('built_up_fraction'),f('water_fraction_phase9b')]).astype(np.float32)
    names=['event_vv_db','event_vh_db','vv_change_db','vh_change_db','hand_d8_100cells_m','slope_deg','tree_fraction','crop_fraction','grass_fraction','bare_fraction','built_up_fraction','water_fraction']
    y=labels.target_2015_11_24.to_numpy(np.uint8); eligible=labels.eligible_for_model.to_numpy(bool)
    finite_sar=np.isfinite(features[:,0])&np.isfinite(features[:,1])&np.isfinite(features[:,2])&np.isfinite(features[:,3])
    finite_nonhand=np.isfinite(features[:,5:]).all(axis=1)
    valid=eligible&finite_sar&finite_nonhand
    if valid.sum()<1000 or y[valid].sum()<100:raise ValueError(f'insufficient eligible cells after SAR features: n={valid.sum()}, positives={y[valid].sum()}')
    idx=np.flatnonzero(valid)
    with rasterio.open(ROOT/'data/processed/alignment/spatial_blocks.tif') as block:
        block_grid=block.read(1).astype(np.int32)
    groups=block_grid[row,col]
    keep=groups[idx]>0;idx=idx[keep]
    unique=np.unique(groups[idx]);tile_rc={}
    for g in unique:
        inds=idx[groups[idx]==g];tile_rc[int(g)]=(int(np.median(row[inds])//100),int(np.median(col[inds])//100))
    candidates={'sar_full':list(range(features.shape[1])),'vv_only':[0],'elevation_only':None,'waterway_distance_only':None}
    Xsets={'sar_full':features,'vv_only':features[:,[0]],'elevation_only':f('elevation_m')[:,None],'waterway_distance_only':f('distance_to_exact_named_waterway_m')[:,None]}
    results={};folds=[];oof={k:np.full(n,np.nan,np.float32) for k in candidates}
    split_list=spatial_column_folds(idx,groups,tile_rc,OUTER_FOLDS)
    for fold,(tr0,te0) in enumerate(split_list,1):
        tr,te=buffered_train_test(tr0,te0,groups,tile_rc)
        if y[tr].sum()<2 or y[te].sum()<2:raise ValueError(f'fold {fold} lacks positive class after buffering')
        fold_result={}
        for model_name,cols in candidates.items():
            X=Xsets[model_name]
            if cols is not None:X=X[:,cols]
            # Training-only inner block OOF predictions choose threshold; each inner split uses the same one-block buffer.
            inner_scores=np.full(len(tr),np.nan,np.float32); inner_pos={int(v):i for i,v in enumerate(tr)}
            for j,(itr0,iva0) in enumerate(spatial_column_folds(tr,groups,tile_rc,INNER_FOLDS),1):
                itr,iva=buffered_train_test(itr0,iva0,groups,tile_rc)
                if y[itr].sum()<2 or y[iva].sum()<2:continue
                smp,wt=train_sample(y,itr,SEED+fold*1000+j)
                model=make_pipeline(SimpleImputer(strategy='median',add_indicator=True),StandardScaler(),LogisticRegression(max_iter=300,C=1.0,solver='lbfgs',random_state=SEED))
                model.fit(X[smp],y[smp],logisticregression__sample_weight=wt)
                inner_scores[np.asarray([inner_pos[int(v)] for v in iva],dtype=np.int64)]=model.predict_proba(X[iva])[:,1]
            im=np.isfinite(inner_scores)
            if im.sum()<100:raise ValueError(f'fold {fold} model {model_name} has too few inner OOF predictions')
            threshold,_=choose_threshold(y[tr][im],inner_scores[im])
            smp,wt=train_sample(y,tr,SEED+fold*2000)
            model=make_pipeline(SimpleImputer(strategy='median',add_indicator=True),StandardScaler(),LogisticRegression(max_iter=300,C=1.0,solver='lbfgs',random_state=SEED))
            model.fit(X[smp],y[smp],logisticregression__sample_weight=wt)
            pred=model.predict_proba(X[te])[:,1].astype(np.float32);oof[model_name][te]=pred
            fold_result[model_name]=metric_row(y[te],pred,threshold)
        # seeded random score with threshold chosen to training prevalence, a non-learned baseline
        rng=np.random.default_rng(SEED+fold); rp=rng.random(len(te)).astype(np.float32);rth=float(1-y[tr].mean())
        oof.setdefault('random',np.full(n,np.nan,np.float32))[te]=rp
        fold_result['random']=metric_row(y[te],rp,rth)
        folds.append({'fold':fold,'train_cells_after_buffer':int(len(tr)),'test_cells':int(len(te)),'train_positives':int(y[tr].sum()),'test_positives':int(y[te].sum()),'buffered_blocks':int(len(set(groups[tr0])-set(groups[tr]))),'metrics':fold_result})
    pooled={}
    for name,pred in oof.items():
        m=np.isfinite(pred)&np.isin(np.arange(n),idx)
        if not m.any():continue
        # Use fold-specific thresholds for fold metrics; pooled metrics use median of fold thresholds.
        ts=[fold['metrics'][name]['threshold'] for fold in folds]
        pooled[name]=metric_row(y[m],pred[m],float(np.median(ts)))
    # Map candidate acceptance is based on the pooled out-of-fold SAR model IoU.
    accepted=pooled['sar_full']['iou']>=0.25
    status='TIER C candidate' if accepted else 'TIER D; rejected for label use'
    metrics={'status':status,'target':'official UNOSAT 2015-11-24 rasterized label; SAR-derived and not field validated','feature_set':names,
      'target_eligible_cells':int(eligible.sum()),'eligible_positive_cells':int((y&eligible).sum()),'evaluation_cells':int(len(idx)),
      'evaluation_positives':int(y[idx].sum()),'evaluation_prevalence':float(y[idx].mean()),'hand_valid_cells_in_evaluation':int(np.isfinite(features[idx,4]).sum()),
      'hand_valid_share':float(np.isfinite(features[idx,4]).mean()),'folds':folds,'pooled_oof':pooled,
      'acceptance_rule':'pooled spatially buffered out-of-fold IoU >= 0.25 permits Tier C candidate only; UNOSAT may use the same 24-Nov SAR scene, so this is map reproduction, not independent flood accuracy.',
      'accepted':bool(accepted),'reason_if_rejected':None if accepted else 'Held-out IoU below the pre-registered 0.25 gate; no follow-on SAR labels produced.',
      'sampling':{'all_positive_train_cells':True,'negative_to_positive_ratio':NEG_RATIO,'seed':SEED,'inverse_sampling_weights':'negative sample weighted by full-train negatives / sampled negatives to approximate true training prevalence'},
      'validation':{'outer_folds':OUTER_FOLDS,'inner_folds':INNER_FOLDS,'blocks':'3 km spatial_blocks.tif IDs; contiguous east-west bands of whole block columns with one-block (8-neighbor) training buffer; no block split across train/test.',
        'threshold':'selected per outer fold by maximum IoU on inner buffered block OOF predictions only; held-out test used only once.'},
      'caveats':['HAND is valid on only the reported share; missing values are imputed within each training fit with missingness indicator.','Labels and event SAR may originate from the same scene; this cannot establish physical detection or independent label validity.','Single date/event only; no Tier B/C independent maps accepted in this run.','Logistic score is calibrated through case-control training weights only; no claim of future calibration.']}
    METRICS.write_text(json.dumps(metrics,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    REGISTRY.write_text(json.dumps({'model':'LogisticRegression, spatially buffered inner OOF threshold selection','parameters':{'C':1.0,'max_iter':300,'solver':'lbfgs','imputer':'median plus missing indicator','negative_ratio':NEG_RATIO,'seed':SEED},'feature_names':names,'data_hashes':{},'metrics':pooled,'acceptance':status},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    report=['# Calibrated SAR candidate labels — Batch 2','',f'**Result: {status}.** The held-out comparison only measures reproduction of the UNOSAT 24 Nov 2015 map. It is not independent flood validation, because UNOSAT may have used the same SAR scene.','',
      f"Training/evaluation used {len(idx):,} cells ({int(y[idx].sum()):,} positive; prevalence {y[idx].mean():.4%}) from {int(eligible.sum()):,} eligible CMA cells. HAND was finite for {np.isfinite(features[idx,4]).sum():,} cells ({np.isfinite(features[idx,4]).mean():.2%}) and imputed within training folds with a missingness indicator.",
      '', '## Out-of-fold results', '', '| Candidate/baseline | ROC-AUC | PR-AUC | F1 | IoU | Precision | Recall | Brier | ECE |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name,m in pooled.items():report.append(f"| {name} | {m['roc_auc']:.4f} | {m['pr_auc']:.4f} | {m['f1']:.4f} | {m['iou']:.4f} | {m['precision']:.4f} | {m['recall']:.4f} | {m['brier']:.5f} | {m['ece_10_bin']:.5f} |")
    report+=['','The default model is not treated as an accepted flood label unless pooled held-out IoU reaches 0.25. The candidate and baselines use the same buffered 3 km spatial folds and training-only thresholds. Per-fold counts and metrics are in `data/features/labels/sar_calibrated_batch2/metrics.json`.','',
      '## Decision and limits','',metrics['reason_if_rejected'] or 'Gate passed for a Tier C candidate only; proceed with unchanged frozen method on the specified dates, with independent checks.',
      'No SAR output is called ground truth. The training comparison is circular if the official map was interpreted from this 24 Nov scene. Missing HAND is extensive and model behavior may mostly reflect the other SAR and land-cover features. The 2023 and 2021 PDF maps remain weak or manual validation references.','',
      '## Reproducibility','',f"Run: `.venv/Scripts/python.exe pipelines/phase9c/calibrated_sar_candidate.py`. Seed {SEED}; {OUTER_FOLDS} outer and {INNER_FOLDS} inner buffered spatial folds; no hyperparameter search.", '']
    REPORT.write_text('\n'.join(report),encoding='utf-8')
    print(json.dumps({'status':status,'cells':int(len(idx)),'positive':int(y[idx].sum()),'prevalence':float(y[idx].mean()),'hand_valid_share':metrics['hand_valid_share'],'sar_iou':pooled['sar_full']['iou'],'outputs':str(OUT.relative_to(ROOT)),'runtime_seconds':time.perf_counter()-tic},indent=2))

if __name__=='__main__':run()
