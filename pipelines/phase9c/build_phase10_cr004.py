"""Build CR-004 corrected Phase 10 display without refitting models."""
from pathlib import Path
import sys
import numpy as np
import rasterio
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from pipelines.phase9c.addendum_cr004 import composite_bands
feat=ROOT/"data/features/static/cell_table_phase9b_v2.parquet"
obs_path=ROOT/"data/features/predictions/phase9c_addendum_cr004_v6/radar_observability_mask.tif"
prob_path=ROOT/"data/features/predictions/phase9c_addendum_cr004_v6/radar_probability_mean_apparent.tif"
out=ROOT/"data/features/predictions/phase10_cr004_v9"
physical_path=ROOT/"data/features/predictions/phase9c_addendum_cr004_v7/physical_susceptibility_all_unobservable.tif"
if out.exists() and any(out.iterdir()): raise FileExistsError("Phase 10 v4 output folder exists and is not empty")
if physical_path.exists(): raise FileExistsError("Physical v4 output already exists")
import pandas as pd
table=pd.read_parquet(feat)
with rasterio.open(obs_path) as d:
 obs=d.read(1)==1
 meta=d.profile.copy()
with rasterio.open(ROOT/"data/processed/grid/cma_mask.tif") as d:
 cma=d.read(1)==1
with rasterio.open(prob_path) as d: prob=d.read(1).astype(np.float32)
rows=table.row.to_numpy(np.int32); cols=table.col.to_numpy(np.int32)
cols_phys=["hand_d8_accum100_m","local_depression_depth_m","twi_d8_proxy","distance_to_exact_named_waterway_m"]
physical=np.zeros(len(table),np.float32); valid_count=np.zeros(len(table),np.uint8)
for col in cols_phys:
 a=table[col].to_numpy(float); ok=np.isfinite(a)
 if ok.sum()>1:
  v=-a[ok] if col.startswith("distance_") else a[ok]
  order=np.argsort(v,kind="mergesort"); rank=np.empty(len(order),np.float32)
  rank[order]=np.linspace(0,1,len(order),dtype=np.float32)
  physical[np.flatnonzero(ok)]+=rank;valid_count+=ok.astype(np.uint8)
physical[valid_count>0]/=valid_count[valid_count>0]
physical[valid_count==0]=np.nan
physgrid=np.full((meta["height"],meta["width"]),np.nan,np.float32);physgrid[rows,cols]=physical
physgrid[obs]=np.nan; physgrid[~cma]=np.nan
bands=composite_bands(cma,obs,prob,physgrid)
meta.update(driver="GTiff",count=3,dtype="float32",nodata=-9999,compress="deflate",predictor=3)
out.mkdir(parents=True)
physical_path.parent.mkdir(parents=True,exist_ok=True)
with rasterio.open(physical_path,"w",**{**meta,"count":1}) as d:
 d.write(physgrid,1);d.set_band_description(1,"PHYSICAL score where radar labels cannot assess; no label fitting")
 d.update_tags(method="equal mean of within-CMA percentile ranks; distance inverted",status="PHYSICAL, not fitted to labels")
with rasterio.open(out/"radar_visible_plus_physical_composite.tif","w",**meta) as d:
 d.write(bands);d.set_band_description(1,"Apparent radar-visible class 1-4; NoData outside observability")
 d.set_band_description(2,"Physical susceptibility score outside radar mask; separate from probability")
 d.set_band_description(3,"unreliable_from_labels: 1 outside radar mask, 0 inside")
 d.update_tags(status="APPARENT SINGLE EVENT; NOT FORECAST")
print("Created the final mask-aware Phase 10 CR-004 composite and full-CMA physical complement.")
print("CMA cells:",int(cma.sum()),"radar-visible:",int(obs.sum()),"physical outside with one or more inputs:",int(np.isfinite(physgrid).sum()))
