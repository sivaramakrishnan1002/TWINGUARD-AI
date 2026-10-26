"""Read-only, coarse cross-checks for the A06 simulation products."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import rasterio
import geopandas as gpd
import pandas as pd
from rasterio.warp import Resampling, reproject
from .simulate import ROOT, OUTPUT, CELL_M, load_static

def validate(output=OUTPUT,filename='validation_summary.json'):
    result_path=output/filename
    if result_path.exists(): raise FileExistsError(f'refusing to overwrite {result_path}')
    summary=json.loads((output/'simulation_summary.json').read_text(encoding='utf-8'))
    grid=load_static(); valid=grid['eligible']; transform=grid['transform']; crs=grid['crs']
    zips=list((ROOT/'data/raw/historical_floods/2015/global_flood_database').glob('DFO_4309*.zip'))
    if len(zips)!=1: raise ValueError(f'expected one local DFO 4309 archive, found {len(zips)}')
    import zipfile
    with zipfile.ZipFile(zips[0]) as zf:
        tifs=[n for n in zf.namelist() if n.lower().endswith('.tif')]
    if len(tifs)!=1: raise ValueError(f'expected one GeoTIFF in GFD archive, found {len(tifs)}')
    uri=f'zip://{zips[0].as_posix()}!{tifs[0]}'
    gfd=np.full(valid.shape,np.nan,dtype=np.float32)
    with rasterio.open(uri) as src:
        reproject(source=rasterio.band(src,1),destination=gfd,src_transform=src.transform,src_crs=src.crs,src_nodata=np.nan,dst_transform=transform,dst_crs=crs,dst_nodata=np.nan,resampling=Resampling.nearest)
        gfd_meta={'member':tifs[0],'crs':str(src.crs),'bands':list(src.descriptions),'extent':'DFO event 4309, 10 Nov–4 Dec 2015'}
    gfd_flood=np.isfinite(gfd)&(gfd>0)
    observed_files=[]
    for p in (ROOT/'data/raw/historical_floods/2015/opencity_flood_points').glob('*.kml'):
        g=gpd.read_file(p)
        if len(g) and g.geometry.geom_type.isin(['Point','MultiPoint']).any(): observed_files.append((p,g))
    points=gpd.GeoDataFrame(pd.concat([g for _,g in observed_files],ignore_index=True),crs='EPSG:4326').to_crs(crs)
    result={'gfd':gfd_meta,'opencity':{'files':[(p.name,len(g)) for p,g in observed_files],'total_points':len(points),'dates':'unclear','locations':'approximate'},'events':{}}
    area=lambda count:float(count*CELL_M*CELL_M/1e6)
    for event,ev in summary['events'].items():
        th=float(ev['median_training_threshold_m'])
        tif=output/f'depth_peak_mean_{event}_DERIVED.tif'
        with rasterio.open(tif) as ds: depth=ds.read(1); nd=ds.nodata
        mask=valid&np.isfinite(gfd)&(depth!=nd)
        pred=depth>=th; tp=int(np.sum(pred&gfd_flood&mask)); fp=int(np.sum(pred&~gfd_flood&mask)); fn=int(np.sum(~pred&gfd_flood&mask))
        hits=inside=0
        for geom in points.geometry:
            if geom is None or geom.is_empty: continue
            row,col=rasterio.transform.rowcol(transform,geom.x,geom.y)
            if 0<=row<depth.shape[0] and 0<=col<depth.shape[1] and mask[row,col]:
                inside+=1; hits+=int(pred[row,col])
        result['events'][event]={'threshold_m':th,'gfd_valid_model_cells':int(mask.sum()),'gfd_flood_area_km2':area(int(np.sum(gfd_flood&mask))),'model_area_km2':area(int(np.sum(pred&mask))),'overlap_area_km2':area(tp),'gfd_iou':tp/max(tp+fp+fn,1),'gfd_precision':tp/max(tp+fp,1),'gfd_recall':tp/max(tp+fn,1),'opencity_assessed_points':inside,'opencity_hit_points':hits,'opencity_hit_share':hits/max(inside,1),'opencity_outside_or_nodata':len(points)-inside}
    result['interpretation']='Coarse and date-mismatched spatial cross-checks only. GFD spans 10 Nov–4 Dec; OpenCity dates are unclear and coordinates approximate. These are not independent depth truth or hydraulic validation.'
    result_path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--output-dir',type=Path,default=OUTPUT);p.add_argument('--filename',default='validation_summary.json'); a=p.parse_args()
    path=a.output_dir if a.output_dir.is_absolute() else ROOT/a.output_dir
    print(json.dumps(validate(path,a.filename),indent=2))
