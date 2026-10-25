"""CR-004 Lane A Phase 9C addendum. Existing inputs only; versioned outputs."""
from __future__ import annotations
import hashlib,json,math,sys,time
from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import Resampling,reproject
from sklearn.metrics import average_precision_score
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from pipelines.phase9b import model_upgrade as p9
from pipelines.phase9c import urban_censoring as p9c
OUT=ROOT/"data/features/predictions/phase9c_addendum_cr004_v6"
MET=ROOT/"docs/PHASE9C_ADDENDUM_CR004_V6.json"
REG=ROOT/"docs/PHASE9C_ADDENDUM_CR004_V6_MODEL_REGISTRY.json"
REP=ROOT/"docs/PHASE9C_ADDENDUM_CR004_V6.md"
LIN=ROOT/"docs/PHASE9C_ADDENDUM_CR004_V6_LINEAGE.md"
FIG=ROOT/"docs/figures/phase9c_addendum_cr004_v6.png"
P10=ROOT/"data/features/predictions/phase10_cr004_v8"
SEED=20261025
BINS=p9c.BUILT_BINS
SETS={
 "i_terrain_hydrology":p9.TERRAIN_FEATURES,
 "ii_plus_landcover_no_built":p9.TERRAIN_FEATURES+["tree_fraction","crop_fraction","grass_fraction","bare_fraction"],
 "iii_plus_built_fraction":p9.TERRAIN_FEATURES+["tree_fraction","crop_fraction","grass_fraction","bare_fraction","built_up_fraction"],
}
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()
def readgrid(path,meta):
 with rasterio.open(path) as s:
  a=np.zeros((meta["height"],meta["width"]),np.uint8)
  reproject(rasterio.band(s,1),a,src_transform=s.transform,src_crs=s.crs,src_nodata=s.nodata,
   dst_transform=meta["transform"],dst_crs=meta["crs"],dst_nodata=0,resampling=Resampling.nearest)
  return a
def prlift(y,p,ids):
 prev=float(y[ids].mean()) if len(ids) else None
 ap=float(average_precision_score(y[ids],p[ids])) if len(ids) and y[ids].sum() else None
 return {"n":int(len(ids)),"prevalence":prev,"pr_auc":ap,"lift":ap/prev if ap is not None and prev else None}
def phase9c_eligibility(phase9_eligible, population_is_nodata):
 # Population missingness is an exposure-data flag; it cannot censor hazard labels.
 return np.asarray(phase9_eligible,dtype=bool).copy()
def composite_bands(cma, observed, probability, physical):
 cma=np.asarray(cma,dtype=bool); observed=np.asarray(observed,dtype=bool)&cma
 probability=np.asarray(probability,dtype=float); physical=np.asarray(physical,dtype=float)
 if not (cma.shape==observed.shape==probability.shape==physical.shape): raise ValueError("composite arrays must share a grid")
 out=np.full((3,)+cma.shape,-9999,dtype=np.float32)
 m=observed&np.isfinite(probability); out[0,m]=np.digitize(probability[m],[.1,.25,.5])+1
 m=cma&~observed&np.isfinite(physical); out[1,m]=physical[m]
 out[2,cma]=0; out[2,cma&~observed]=1
 return out
def write_raster(path,meta,a,dtype="float32",nodata=-9999,desc=""):
 path.parent.mkdir(parents=True,exist_ok=True)
 prof={"driver":"GTiff","height":meta["height"],"width":meta["width"],"count":1,"dtype":dtype,
  "crs":meta["crs"],"transform":meta["transform"],"nodata":nodata,"compress":"deflate",
  "predictor":3 if dtype.startswith("float") else 1}
 with rasterio.open(path,"w",**prof) as d:
  d.write(a.astype(dtype),1); d.set_band_description(1,desc); d.update_tags(run="CR-004",label="unchanged Phase 9 SAR-derived label")
def run():
 for path in (OUT,P10):
  if path.exists() and any(path.iterdir()): raise FileExistsError("Versioned output folder already contains files")
 for f in (MET,REG,REP,LIN,FIG):
  if f.exists(): raise FileExistsError("CR-004 report output already exists")
 OUT.mkdir(parents=True); P10.mkdir(parents=True)
 t0=time.perf_counter()
 table,labels,y,eligible,_,_,groups,positions,rows,cols,_=p9.load_data()
 with rasterio.open(ROOT/"data/processed/grid/cma_mask.tif") as d:
  meta={"height":d.height,"width":d.width,"crs":d.crs,"transform":d.transform,"profile":d.profile}
 cma=readgrid(ROOT/"data/processed/grid/cma_mask.tif",meta)==1
 ref=readgrid(ROOT/"data/processed/sar_work/rtc_aligned/2015-10-19_valid_layover_shadow_mask.tif",meta)==1
 ev=readgrid(ROOT/"data/processed/sar_work/rtc_aligned/2015-11-24_valid_layover_shadow_mask.tif",meta)==1
 rf=readgrid(ROOT/"data/processed/sar_work/rtc_aligned/2015-10-19_layover_shadow_flags.tif",meta)
 ef=readgrid(ROOT/"data/processed/sar_work/rtc_aligned/2015-11-24_layover_shadow_flags.tif",meta)
 bgrid=np.full(cma.shape,np.nan,np.float32); sgrid=np.full(cma.shape,np.nan,np.float32)
 bgrid[rows,cols]=table.built_up_fraction.to_numpy(np.float32); sgrid[rows,cols]=table.slope_deg.to_numpy(np.float32)
 eligible=phase9c_eligibility(eligible,table.population_is_nodata.to_numpy(bool))
 lbl=np.zeros(cma.shape,bool); lbl[rows,cols]=eligible
 radar=ref&ev&(((rf&(4|16))==0)&((ef&(4|16))==0))
 dense=np.isfinite(bgrid)&(bgrid>p9c.OBS_BUILT_CUTOFF)
 steep=np.isfinite(sgrid)&(sgrid>p9c.OBS_SLOPE_CUTOFF_DEG)
 obs=cma&lbl&radar&~dense&~steep&np.isfinite(sgrid)
 domain=obs[rows,cols]&eligible
 idx=np.flatnonzero(domain); built=table.built_up_fraction.to_numpy(float)
 popna=table.population_is_nodata.to_numpy(bool)
 dropped=eligible&popna&(y==1); di=np.flatnonzero(dropped)
 # Descriptive diagnostics for all formerly censored flooded cells.
 fcols=["tree_fraction","crop_fraction","grass_fraction","bare_fraction","built_up_fraction_phase9b","water_fraction_phase9b"]
 f=table[fcols].to_numpy(float); lc=np.argmax(np.where(np.isfinite(f),f,-np.inf),axis=1); lc[~np.isfinite(f).any(axis=1)]=-1
 lc_names=["tree","crop","grass","bare","built_up","water"]
 diag={"positive_cells_dropped_by_population_mask":int(len(di)),
  "within_radar_observability":int(obs[rows[di],cols[di]].sum()),
  "land_cover":{n:int((lc[di]==j).sum()) for j,n in enumerate(lc_names)}|{"unknown":int((lc[di]<0).sum())},
  "built_up_bins":{n:int(((built[di]>=lo)&(built[di]<hi)).sum()) for n,lo,hi in BINS},
  "distance_bins_m":{},"3km_blocks":{str(int(g)):int((groups[di]==g).sum()) for g in np.unique(groups[di])}}
 for key,col in (("water","distance_to_all_available_water_m"),("coast","distance_to_coast_or_sea_m")):
  v=table[col].to_numpy(float)[di]; edges=[0,100,300,1000,5000,np.inf]; names=["0-100","100-300","300-1000","1000-5000",">5000"]
  diag["distance_bins_m"][key]={n:int(((v>=a)&(v<z)).sum()) for n,a,z in zip(names,edges[:-1],edges[1:])}
  diag["distance_bins_m"][key]["missing"]=int((~np.isfinite(v)).sum())
 with rasterio.open(ROOT/"data/raw/population/ind_pop_2021_CN_100m_R2025A_v1.tif") as d:
  wp={"nodata":d.nodata,"dtype":d.dtypes[0],"crs":str(d.crs),"pixel_size":list(map(float,d.res)),"tags":d.tags()}
 diag["worldpop_source_metadata"]=wp
 diag["why_unknown"]="The raster declares -99999 as NoData, but its tags do not explain each missing pixel. Spatial pattern summaries are descriptive and cannot establish a cell-specific cause."
 if len(idx)<1 or len(np.unique(groups[idx]))<p9.OUTER_FOLDS: raise ValueError("Insufficient observable cells for buffered spatial folds")
 outer=p9.outer_folds(idx,y,groups,positions)
 results={}; preds={}
 tmod=time.perf_counter()
 for si,(name,features) in enumerate(SETS.items()):
  x=p9.make_matrix(table,features); pred=np.full(len(y),np.nan,np.float32); fr=[]; mondrian=[]
  for spec in outer:
   r=p9.evaluate_outer("random_forest",p9.MODEL_DEFAULTS["random_forest"],x,y,groups,spec["train"],spec["test"],positions,SEED+si*10000+spec["fold"]*100)
   pred[spec["test"]]=r["probability"]; fr.append(r["metrics"])
   train_idx=r["train_calibration_indices"]; train_p=r["train_calibration_probability"]
   pooled_q=float(np.quantile(np.abs(y[train_idx]-train_p),.90,method="higher"))
   for bin_name,lo,hi in BINS:
    tm=(built[train_idx]>=lo)&(built[train_idx]<hi)
    q=float(np.quantile(np.abs(y[train_idx[tm]]-train_p[tm]),.90,method="higher")) if tm.any() else pooled_q
    test=spec["test"]; vm=(built[test]>=lo)&(built[test]<hi)
    if vm.any():
     pp=r["probability"][vm]; yy=y[test][vm]
     low=np.maximum(0,pp-q); high=np.minimum(1,pp+q)
     mondrian.append({"fold":int(spec["fold"]),"built_up_bin":bin_name,"n_train_calibration":int(tm.sum()),
      "n_test":int(vm.sum()),"q90_abs_residual":q,"coverage":float(((yy>=low)&(yy<=high)).mean()),
      "mean_width":float((high-low).mean())})
   print(name+" fold "+str(spec["fold"])+"/5 done",flush=True)
  preds[name]=pred
  results[name]={"features":features,"parameters":p9.MODEL_DEFAULTS["random_forest"],
   "fold_mean_sd":p9.summarize_folds(fr,["roc_auc","pr_auc","brier","f1","iou"]),
   "fold_metrics":fr,"fold_mondrian_90":mondrian,"pooled_metrics":p9.metric_bundle(y[idx],pred[idx],.5,float(y[idx].mean())),
   "domain":prlift(y,pred,idx)}
 refname="iii_plus_built_fraction"; pred=preds[refname]
 # Fair single-variable baselines and random baseline on identical outer folds.
 baselines={}
 for bi,(name,feat) in enumerate((("elevation_only","elevation_m"),("named_waterway_distance_only","distance_to_exact_named_waterway_m"))):
  x=p9.make_matrix(table,[feat]); pp=np.full(len(y),np.nan,np.float32); fr=[]
  for sp in outer:
   r=p9.evaluate_outer("logistic",{},x,y,groups,sp["train"],sp["test"],positions,SEED+80000+bi*1000+sp["fold"])
   pp[sp["test"]]=r["probability"];fr.append(r["metrics"])
  baselines[name]={"fold_mean_sd":p9.summarize_folds(fr,["roc_auc","pr_auc","brier"]),"pooled":prlift(y,pp,idx)}
 rp=np.full(len(y),np.nan,np.float32)
 for sp in outer: rp[sp["test"]]=float(y[sp["train"]].mean())
 baselines["random_prevalence"]={"pooled":prlift(y,rp,idx),"fold_mean_sd":{"roc_auc":{"mean":.5,"sd":0.0}}}
 dense_ids=idx[built[idx]<=p9c.OBS_BUILT_CUTOFF]
 domains={"all_radar_visible":prlift(y,pred,idx),"excluding_built_gt_0_50":prlift(y,pred,dense_ids)}
 stratum_scores={}
 for model_name,model_pred in preds.items():
  stratum_scores[model_name]={"all":prlift(y,model_pred,idx),"excluding_built_gt_0_50":prlift(y,model_pred,dense_ids),"built_up_bins":{}}
  for bn,lo,hi in BINS:
   ids=idx[(built[idx]>=lo)&(built[idx]<hi)]
   stratum_scores[model_name]["built_up_bins"][bn]=prlift(y,model_pred,ids)
 # within-stratum top percentile precision and recall
 top={}
 for name,lo,hi in BINS:
  ids=idx[(built[idx]>=lo)&(built[idx]<hi)]; row={"n":int(len(ids)),"prevalence":float(y[ids].mean()) if len(ids) else None,"top":{}}
  if len(ids):
   order=ids[np.argsort(-pred[ids],kind="mergesort")]
   for pct in (1,2,5,10):
    chosen=order[:max(1,int(math.ceil(len(order)*pct/100)))]
    row["top"][str(pct)]={"precision":float(y[chosen].mean()),"recall":float(y[chosen].sum()/max(int(y[ids].sum()),1))}
  top[name]=row
 # Apparent full-domain uncertainty bands, with Mondrian quantiles from OOF predictions.
 qs={}
 for bn,lo,hi in BINS:
  ids=idx[(built[idx]>=lo)&(built[idx]<hi)]
  qs[bn]=float(np.quantile(np.abs(y[ids]-pred[ids]),.90,method="higher")) if len(ids) else None
 # Full data apparent surface; no output claims held-out calibration.
 x=p9.make_matrix(table,SETS[refname]); sampled,sample=p9.sample_train(idx,y,groups,SEED+200000)
 model=p9.fit_estimator("random_forest",p9.MODEL_DEFAULTS["random_forest"],x[sampled],y[sampled],SEED+200000)
 # Calibrate the full-data apparent surface from outer-fold out-of-fold predictions.
 apparent=np.full(len(y),np.nan,np.float32)
 map_calibrator=p9.fit_platt(pred[idx],y[idx])
 apparent[idx]=p9.apply_platt(map_calibrator,model.predict_proba(x[idx])[:,1]).astype(np.float32)
 probgrid=np.full(cma.shape,np.nan,np.float32);probgrid[rows,cols]=apparent
 probgrid[~obs]=np.nan
 # physical score is a separate non-trained rank composite for cells outside mask.
 phys=np.zeros(len(table),np.float32); physcols=["hand_d8_accum100_m","local_depression_depth_m","twi_d8_proxy","distance_to_exact_named_waterway_m"]
 for col in physcols:
  a=table[col].to_numpy(float); ok=np.isfinite(a)
  v=-a[ok] if col.startswith("distance_") else a[ok]
  if ok.sum()>1:
   order=np.argsort(v,kind="mergesort"); rank=np.empty(len(order),np.float32);rank[order]=np.linspace(0,1,len(order),dtype=np.float32)
   phys[np.flatnonzero(ok)]+=rank/len(physcols)
 phys[~eligible]=np.nan
 physgrid=np.full(cma.shape,np.nan,np.float32);physgrid[rows,cols]=phys;physgrid[obs]=np.nan
 confidence=np.full(cma.shape,255,np.uint8);confidence[cma]=0;confidence[obs]=1;confidence[cma&~obs]=2
 write_raster(OUT/"radar_observability_mask.tif",meta,np.where(cma,obs,255),"uint8",255,"1 radar assessed, 0 not assessed, 255 outside CMA")
 write_raster(OUT/"radar_probability_mean_apparent.tif",meta,probgrid,desc="Apparent full-data probability; radar-visible cells only")
 p05=np.full(cma.shape,np.nan,np.float32);p95=np.full(cma.shape,np.nan,np.float32)
 for bn,lo,hi in BINS:
  cells=obs&np.isfinite(bgrid)&(bgrid>=lo)&(bgrid<hi)
  if qs[bn] is not None:
   p05[cells]=np.maximum(0,probgrid[cells]-qs[bn]);p95[cells]=np.minimum(1,probgrid[cells]+qs[bn])
 write_raster(OUT/"radar_probability_p05_apparent.tif",meta,p05,desc="Apparent lower bound using OOF Mondrian residual quantile")
 write_raster(OUT/"radar_probability_p95_apparent.tif",meta,p95,desc="Apparent upper bound using OOF Mondrian residual quantile")
 p05=np.full(cma.shape,np.nan,np.float32);p95=np.full(cma.shape,np.nan,np.float32)
 for bn,lo,hi in BINS:
  cells=obs&np.isfinite(bgrid)&(bgrid>=lo)&(bgrid<hi)
  if qs[bn] is not None:
   p05[cells]=np.maximum(0,probgrid[cells]-qs[bn]);p95[cells]=np.minimum(1,probgrid[cells]+qs[bn])
 write_raster(OUT/"radar_probability_p05_apparent.tif",meta,p05,desc="Apparent 5th percentile bound from OOF Mondrian residual quantile")
 write_raster(OUT/"radar_probability_p95_apparent.tif",meta,p95,desc="Apparent 95th percentile bound from OOF Mondrian residual quantile")
 write_raster(OUT/"physical_susceptibility_unobservable.tif",meta,np.where(cma&~obs,physgrid,np.nan),desc="PHYSICAL, not fitted to labels; outside radar observability")
 write_raster(OUT/"urban_confidence.tif",meta,confidence,"uint8",255,"1 radar visible; 2 unreliable from labels; 0 label ineligible; 255 outside CMA")
 comp=composite_bands(cma,obs,probgrid,physgrid)
 P10.mkdir(exist_ok=True)
 prof=dict(meta["profile"]);prof.update(driver="GTiff",count=3,dtype="float32",nodata=-9999,compress="deflate",predictor=3)
 with rasterio.open(P10/"radar_visible_plus_physical_composite.tif","w",**prof) as d:
  d.write(comp);d.set_band_description(1,"Apparent class 1-4 inside observability only")
  d.set_band_description(2,"Physical score outside observability only");d.set_band_description(3,"unreliable_from_labels 1 outside radar mask")
  d.update_tags(status="APPARENT SINGLE EVENT; NOT FORECAST")
 # Independent point validation with matched built-up and dominant landcover chance baseline.
 lcgrid=p9c.dominant_landcover_grid(table,rows,cols,cma.shape)
 points=p9c.point_features(bgrid,lcgrid,probgrid,physgrid,obs,np.isfinite(physgrid),meta)
 point={}
 for pct in (1,5,10,20):
  cp=[dict(v) for v in points]
  for v in cp:
   if v["row"] is not None and v["col"] is not None:v["risk"]=float(probgrid[v["row"],v["col"]]) if np.isfinite(probgrid[v["row"],v["col"]]) else None
  point[str(pct)]=p9c.block_bootstrap_point_hits(cp,probgrid,bgrid,obs,pct,SEED+pct,reps=500,landcover_grid=lcgrid)
 physical_points={}
 outside=cma&~obs
 for pct in (1,5,10,20):
  cp=[dict(v) for v in points]
  for v in cp:
   if v["row"] is not None and v["col"] is not None:v["risk"]=float(physgrid[v["row"],v["col"]]) if np.isfinite(physgrid[v["row"],v["col"]]) else None
  physical_points[str(pct)]=p9c.block_bootstrap_point_hits(cp,physgrid,bgrid,outside,pct,SEED+500+pct,reps=500,landcover_grid=lcgrid)
 metrics={"status":"CR-004; unchanged Phase 9 target; single-event radar-visible flooding; not field truth or forecast",
  "eligibility":{"phase9_eligible_cells":int(eligible.sum()),"population_nodata_retained":int((eligible&popna).sum()),
   "model_domain_cells":int(len(idx)),"model_positive_cells":int(y[idx].sum()),"prevalence":float(y[idx].mean()),
   "observability":{"dense_builtup_gt_0_50":int((cma&dense).sum()),"steep_slope_gt_15":int((cma&steep).sum()),
    "radar_invalid_or_masked":int((cma&~radar).sum()),"slope_missing":int((cma&~np.isfinite(sgrid)).sum())},
   "dropped_positive_cell_diagnostic":diag},
  "feature_sets":results,"same_fold_baselines":baselines,"dense_urban_exclusion":domains,
  "evaluation_domain_prevalence_pr_auc_lift_by_feature_set":stratum_scores,
  "built_up_stratum_top_precision_recall":top,
  "independent_opencity_points_dates_unclear_locations_approximate":point,
  "physical_complement_point_validation":physical_points,
  "conformal":{"method":"spatially buffered inner out-of-fold absolute-residual quantile, stratified by built-up bin (Mondrian); quantile fit in each outer training set only",
   "reference_model_fold_stratum_coverage":results[refname]["fold_mondrian_90"],
  "apparent_map_quantiles_by_built_up_bin":qs,
   "mean_outer_fold_coverage_by_bin":{bn:float(np.mean([z["coverage"] for z in results[refname]["fold_mondrian_90"] if z["built_up_bin"]==bn])) for bn,lo,hi in BINS if any(z["built_up_bin"]==bn for z in results[refname]["fold_mondrian_90"])},
   "stratum_summary":{n:{"mean_coverage":float(np.mean([r["coverage"] for r in results[refname]["fold_mondrian_90"] if r["built_up_bin"]==n])),
    "mean_width":float(np.mean([r["mean_width"] for r in results[refname]["fold_mondrian_90"] if r["built_up_bin"]==n]))}
    for n,_,_ in BINS if any(r["built_up_bin"]==n for r in results[refname]["fold_mondrian_90"])},
   "note":"Nominal 90% coverage is not guaranteed; report empirical folds and strata, especially any below 88%."},
  "physical_complement":{"status":"PHYSICAL, NOT FITTED TO LABELS","features":physcols,"method":"equal mean of within-eligible-cell percentile ranks; distance inverted"},
  "phase10_display":{"path":"data/features/predictions/phase10_cr004_v8/radar_visible_plus_physical_composite.tif","data_driven_inside_observability_only":True,"physical_outside_with_unreliable_flag":True},
  "ensemble":{"status":"not run; default random forest retained as reference and ensemble option deferred"},
  "runtime_seconds":time.perf_counter()-t0}
 MET.write_text(json.dumps(metrics,indent=2,allow_nan=False)+"\n",encoding="utf-8")
 registry={"model":"default_random_forest","parameters":p9.MODEL_DEFAULTS["random_forest"],"seed":SEED,"feature_sets":SETS,
  "feature_sha256":sha(p9.FEATURE_TABLE),"label_sha256":sha(p9.LABEL_TABLE),
  "sampling":{"all_positive":True,"negative_to_positive":p9.NEGATIVE_TO_POSITIVE},
  "metrics_file":"docs/PHASE9C_ADDENDUM_CR004.json","command":".venv/Scripts/python.exe pipelines/phase9c/addendum_cr004.py",
  "interpretation":"single-event radar-visible susceptibility; full-data raster is apparent"}
 REG.write_text(json.dumps(registry,indent=2)+"\n",encoding="utf-8")
 lines=["# Phase 9C addendum CR-004","",
  "## Scope","",
  "The unchanged Phase 9 target is a single November 2015 SAR-derived event. The model describes radar-visible flooding. It is not field truth, a forecast, or cross-event evidence.","",
  "## WorldPop eligibility audit","",
  f"Phase 9 eligible cells: {eligible.sum():,}; retained despite WorldPop NoData: {(eligible&popna).sum():,}; radar-visible evaluation cells: {len(idx):,}, prevalence {y[idx].mean():.6f}. The previous WorldPop mask had removed {len(di):,} positive cells. WorldPop is exposure only. The source NoData is -99999; metadata does not identify why each cell is missing. Descriptive distributions are in the JSON; they do not prove a specific cause.","",
  "## Models and baselines","",
  "All three feature sets use the same buffered 3 km spatial folds, default random forest, training-only sampling/calibration, and true-prevalence outer evaluation. Population, road-node distance and building density are excluded. No search was run. Feature set C includes built-up fraction as requested.","",
  "| Set | Prevalence | PR-AUC | Lift | ROC-AUC mean (SD) | Brier mean (SD) |","|---|---:|---:|---:|---:|---:|"]
 for n,r in results.items():
  q=r["domain"]; a=r["fold_mean_sd"]["roc_auc"]; b=r["fold_mean_sd"]["brier"]
  lines.append(f"| {n} | {q['prevalence']:.6f} | {q['pr_auc']:.6f} | {q['lift']:.3f} | {a['mean']:.4f} ({a['sd']:.4f}) | {b['mean']:.5f} ({b['sd']:.5f}) |")
 lines+=["","Same-fold baselines and all fold metrics are in the JSON. Dense-urban exclusion results include prevalence, PR-AUC and lift. Top 1/2/5/10 percent precision and recall are reported by built-up stratum in the JSON.","",
  "## OpenCity points and uncertainty","",
  "OpenCity point dates are unclear and locations approximate. The JSON reports top 1/5/10/20 percent hit rates and a chance comparison matched by built-up stratum and dominant land cover, with 3 km block bootstrap intervals.","",
  "Conformal bands are re-calibrated inside each outer training fold using buffered inner out-of-fold residuals stratified by built-up bin. Empirical outer-fold coverage and width by stratum, plus apparent map bounds, are recorded in JSON. Any stratum below 88% is under-covered; nominal 90% is not guaranteed.","",
  "## Physical complement and Phase 10 display","",
  "Outside the radar observability mask, a separate rank-based PHYSICAL layer is shown with an unreliable-from-labels flag. It is not fitted to flood labels and is not a flood probability. The Phase 10 composite keeps the physical score and apparent radar class in separate bands.","",
  "## Reproducibility","",
  "Command: .venv/Scripts/python.exe pipelines/phase9c/addendum_cr004.py. Seed: 20261025. Hyperparameter search: none.",""]
 REP.write_text("\n".join(lines),encoding="utf-8")
 LIN.write_text("# CR-004 lineage\n\nRead-only inputs: Phase 9B feature table, unchanged Nov 2015 label table, CMA/blocks/radar masks, WorldPop metadata and OpenCity KML points. No raw files were changed.\n\nFeature SHA-256: "+registry["feature_sha256"]+"\n\nLabel SHA-256: "+registry["label_sha256"]+"\n\nOutputs: "+", ".join([str(p.relative_to(ROOT)) for p in (OUT,P10)])+"\n",encoding="utf-8")
 import matplotlib; matplotlib.use("Agg")
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(1,2,figsize=(10,4))
 im=ax[0].imshow(np.ma.masked_invalid(probgrid),vmin=0,vmax=1,cmap="magma");ax[0].set_title("Apparent radar-visible probability");fig.colorbar(im,ax=ax[0])
 im=ax[1].imshow(np.ma.masked_invalid(physgrid),vmin=0,vmax=1,cmap="terrain");ax[1].set_title("Physical outside mask; unreliable");fig.colorbar(im,ax=ax[1])
 for a in ax:a.axis("off")
 fig.tight_layout();fig.savefig(FIG,dpi=140);plt.close(fig)
 return metrics
if __name__=="__main__":
 m=run();print(json.dumps({"status":m["status"],"domain":m["eligibility"]["model_domain_cells"],"prevalence":m["eligibility"]["prevalence"],"runtime_seconds":m["runtime_seconds"]},indent=2))
