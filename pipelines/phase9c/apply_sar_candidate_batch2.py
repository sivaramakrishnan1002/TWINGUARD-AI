"""Apply accepted 24-Nov SAR map-reproduction model to the preregistered later dates."""
from __future__ import annotations
import json,sys
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
import rasterio
from rasterio.warp import reproject,Resampling
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from pipelines.phase9c.calibrated_sar_candidate import train_sample,align,SEED
from pipelines.phase9c import urban_censoring as p9c
OUT=ROOT/'data/features/labels/sar_calibrated_batch2/applied_v2'
REPORT=ROOT/'docs/SAR_CALIBRATED_LABELS_BATCH2_APPLIED_V2.md'
MET=OUT/'application_metrics.json'


def application_valid_mask(eligible: np.ndarray, features: np.ndarray) -> np.ndarray:
    """Keep only the predeclared label-eligible cells with required non-HAND inputs."""
    if features.ndim != 2 or features.shape[0] != eligible.shape[0] or features.shape[1] < 6:
        raise ValueError('features must be a 2D array aligned with eligibility and include required static columns')
    return (eligible.astype(bool, copy=False)
            & np.isfinite(features[:, 0]) & np.isfinite(features[:, 1])
            & np.isfinite(features[:, 2]) & np.isfinite(features[:, 3])
            & np.isfinite(features[:, 5:]).all(axis=1))


def main():
    if OUT.exists() and any(OUT.iterdir()):raise FileExistsError('Refusing to overwrite SAR candidate applied outputs')
    if REPORT.exists():raise FileExistsError('Refusing to overwrite applied SAR report')
    OUT.mkdir(parents=True,exist_ok=True)
    with rasterio.open(ROOT/'data/features/terrain/elevation_m.tif') as d: shape=d.shape;transform=d.transform;crs=d.crs;profile=d.profile.copy()
    tab=pq.read_table(ROOT/'data/features/static/cell_table_phase9b_v2.parquet').to_pandas()
    labs=pq.read_table(ROOT/'data/features/predictions/labels_nov2015.parquet').to_pandas()
    if not np.array_equal(tab.cell_id.to_numpy(),labs.cell_id.to_numpy()):raise ValueError('source grid order mismatch')
    rows=tab.row.to_numpy(int);cols=tab.col.to_numpy(int);n=len(tab)
    def f(col):return tab[col].to_numpy(dtype=np.float32,na_value=np.nan)
    labels=labs.target_2015_11_24.to_numpy(np.uint8);eligible=labs.eligible_for_model.to_numpy(bool)
    hand=align(ROOT/'data/processed/sar_work/hand_d8_100cells_20261025_03_DEFAULT.tif',shape,transform,crs,Resampling.nearest)[rows,cols]
    static=np.column_stack([hand,f('slope_deg'),f('tree_fraction'),f('crop_fraction'),f('grass_fraction'),f('bare_fraction'),f('built_up_fraction'),f('water_fraction_phase9b')]).astype(np.float32)
    train_dir=ROOT/'data/processed/sar_work/run_20261025_002401/rtc_aligned'
    def train_feature(scene,reference):
        event_vv=align(train_dir/(scene+'_VV_dB_lee5.tif'),shape,transform,crs,Resampling.bilinear)[rows,cols]
        event_vh=align(train_dir/(scene+'_VH_dB_lee5.tif'),shape,transform,crs,Resampling.bilinear)[rows,cols]
        ref_vv=align(train_dir/(reference+'_VV_dB_lee5.tif'),shape,transform,crs,Resampling.bilinear)[rows,cols]
        ref_vh=align(train_dir/(reference+'_VH_dB_lee5.tif'),shape,transform,crs,Resampling.bilinear)[rows,cols]
        return np.column_stack([event_vv,event_vh,event_vv-ref_vv,event_vh-ref_vh,static]).astype(np.float32)
    X=train_feature('2015-11-24','2015-10-19')
    valid=application_valid_mask(eligible,X)
    ids=np.flatnonzero(valid);sample,weights=train_sample(labels,ids,SEED+9999)
    model=make_pipeline(SimpleImputer(strategy='median',add_indicator=True),StandardScaler(),LogisticRegression(max_iter=300,C=1.0,solver='lbfgs',random_state=SEED))
    model.fit(X[sample],labels[sample],logisticregression__sample_weight=weights)
    validation=json.load(open(ROOT/'data/features/labels/sar_calibrated_batch2/metrics.json',encoding='utf-8'))
    threshold=float(np.median([f['metrics']['sar_full']['threshold'] for f in validation['folds']]))
    def apply(event,baseline,label,context_reference=None):
        xx=train_feature(event,baseline)
        valid_map=application_valid_mask(eligible,xx)
        p=np.full(n,np.nan,np.float32);p[valid_map]=model.predict_proba(xx[valid_map])[:,1].astype(np.float32)
        pg=np.full(shape,np.nan,np.float32);pg[rows,cols]=p
        cp=np.full(shape,255,np.uint8);cp[rows[valid_map],cols[valid_map]]=(p[valid_map]>=threshold).astype(np.uint8)
        prob_path=OUT/f'{event}_sar_candidate_probability_DERIVED_TIER_D.tif';cls_path=OUT/f'{event}_sar_candidate_class_DERIVED_TIER_D.tif'
        prof=dict(profile);prof.update(driver='GTiff',count=1,dtype='float32',nodata=-9999,compress='deflate',predictor=3)
        with rasterio.open(prob_path,'w',**prof) as dst:
            a=np.where(np.isfinite(pg),pg,-9999).astype(np.float32);dst.write(a,1);dst.set_band_description(1,'SAR-derived model probability; candidate, not field validated');dst.update_tags(status='DERIVED_TIER_D_PENDING_INDEPENDENT_VALIDATION',threshold=threshold,event_scene=event,model='trained on UNOSAT 2015-11-24 label; same-scene circularity caveat')
        prof.update(dtype='uint8',nodata=255,predictor=1)
        with rasterio.open(cls_path,'w',**prof) as dst:
            dst.write(cp,1);dst.set_band_description(1,'Candidate flood class; 1 above training-selected OOF threshold, 0 below');dst.update_tags(status='DERIVED_TIER_D_PENDING_INDEPENDENT_VALIDATION',threshold=threshold,method='same fitted SAR logistic model applied without tuning')
        nvalid=int(valid_map.sum());flooded=int((cp==1).sum());area=flooded*900/1e6
        lc=p9c.dominant_landcover_grid(tab,rows,cols,shape)
        built=np.full(shape,np.nan,np.float32);built[rows,cols]=f('built_up_fraction')
        domain=np.isfinite(pg)&np.isfinite(built)
        pts=p9c.point_features(built,lc,pg,pg,domain,domain,{'crs':crs,'transform':transform,'height':shape[0],'width':shape[1]})
        for q in pts:
            if q['row'] is not None and q['col'] is not None:q['risk']=float(pg[q['row'],q['col']]) if np.isfinite(pg[q['row'],q['col']]) else None
        hits={}
        for pct in (1,5,10,20):hits[str(pct)]=p9c.block_bootstrap_point_hits([dict(q) for q in pts],pg,built,domain,pct,SEED+pct+(1000 if event.startswith('2021') else 0),reps=1000,landcover_grid=lc)
        return {'event_scene':event,'reference_scene_used_for_model_feature':baseline,'other_reference_scene_checked_not_used':context_reference,'threshold':threshold,'valid_CMA_cells':nvalid,'predicted_positive_cells':flooded,'predicted_area_km2_30m_grid_approx':area,'opencity_point_hits':hits,'probability_raster':prob_path.relative_to(ROOT).as_posix(),'class_raster':cls_path.relative_to(ROOT).as_posix()}
    results={
      '2015-12-06':apply('2015-12-06','2015-10-19','2015-12-06','2015-11-24'),
      '2021-11-16':apply('2021-11-16','2021-11-04','2021-11-16','2021-10-23')}
    meta={'status':'DERIVED SAR candidate; Tier D pending independent validation; not ground truth','model_source':'spatial-block 24-Nov 2015 model trained on UNOSAT map; unchanged coefficients and OOF threshold','threshold':threshold,'results':results,
      'GFD_comparison':{'event':'GFD 4309, coarse, ends 2015-12-04','published_reference_area_km2':65.43,'local_raster_found':False,'spatial_comparison':'not computed; area-only context is temporally mismatched and not directly comparable'},
      '2021_NRSC_comparison':'not computed; available NRSC PDF GeoPDF CRS mismatch remains unresolved/manual-needed (see GEO_PDF_LABELS_BATCH2.md).',
      'OpenCity_limit':'945 observed points have unclear dates/approximate locations; spatial ranking is not date-matched validation.',
      'reference_handling':'For Dec 6 the model-compatible dB changes use Oct 19; Nov 24 is retained as a prior-scene context only. For Nov 16 2021 the model-compatible baseline is Nov 4; Oct 23 was checked as an older reference context but not added as an untrained feature.',
      'caveats':['The 24 Nov target may be derived from the same SAR scene, so acceptance only establishes map reproduction.','2015 training and 2021 application have different event-reference time gaps; 2021 comparison is diagnostic.','GFD raster not present locally; no spatial GFD comparison or label-schema load.','The 2021 PDF is unresolved for georeferencing, so it was not used for validation.']}
    MET.write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    lines=['# SAR candidate application to 6 Dec 2015 and 16 Nov 2021','',f"The unchanged 24-Nov model passed its preregistered reproduction gate (spatially buffered OOF IoU {validation['pooled_oof']['sar_full']['iou']:.3f} >= 0.25). This permits only a **Tier C candidate** for map reproduction; both later-event rasters remain **DERIVED Tier D pending independent validation**.",'',f"One OOF threshold of {threshold:.2f} was applied without retuning.",'','| Event | Valid CMA cells | Candidate area (km², 30 m grid approx.) | OpenCity top 1% / 5% / 10% / 20% hit share |','|---|---:|---:|---|']
    for event,r in results.items():
        h=r['opencity_point_hits']; lines.append(f"| {event} | {r['valid_CMA_cells']:,} | {r['predicted_area_km2_30m_grid_approx']:.2f} | "+' / '.join(f"{100*h[str(p)]['observed_share']:.2f}% (n={h[str(p)]['n']})" if h[str(p)]['observed_share'] is not None else 'n/a' for p in (1,5,10,20))+' |')
    lines+=['','## Cross-checks and limits','',f"The Global Flood Database event 4309 reference area is 65.43 km² and its event ends 4 Dec 2015, but no local GFD raster was found; therefore the only comparison available here is area context (not spatial overlap). The NRSC 2021 PDF was not used because its GeoPDF CRS ambiguity remains manual-needed. OpenCity point locations are approximate and dates unclear, so those hit shares are not event validation.",'','For 6 Dec 2015, dB-change inputs use 19 Oct 2015 to match the trained feature definition; 24 Nov is checked only as a prior-scene context. For 2021, 4 Nov is the model input baseline and 23 Oct is a second reference context only. These temporal differences limit transfer. The 24 Nov label may use the same event SAR scene, making the high reproduction score circular. No maps were loaded into the label database and no output is ground truth.','']
    REPORT.write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({k:{'area_km2':v['predicted_area_km2_30m_grid_approx'],'valid_cells':v['valid_CMA_cells'],'point_n':v['opencity_point_hits']['10']['n']} for k,v in results.items()},indent=2))

if __name__=='__main__':main()
