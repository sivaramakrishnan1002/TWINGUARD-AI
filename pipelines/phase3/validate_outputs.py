#!/usr/bin/env python
"""Final read-only validation of generated Phase 3 products and common-grid alignment."""
import json
from pathlib import Path
import rasterio
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
GRID=ROOT/'data/processed/grid/grid_definition.json'
def main():
    g=json.loads(GRID.read_text()); expected=(g['width'],g['height'],g['crs'],tuple(g['transform']))
    rasters=sorted(p for base in (ROOT/'data/processed/grid',ROOT/'data/processed/labels_inspection',ROOT/'data/processed/exposure',ROOT/'data/features') for p in base.rglob('*.tif'))
    errors=[]; warnings=[]; records=[]
    for p in rasters:
        with rasterio.open(p) as ds:
            actual=(ds.width,ds.height,ds.crs.to_string(),tuple(ds.transform)[:6])
            aligned=actual[:3]==expected[:3] and np.allclose(actual[3],expected[3],rtol=0,atol=1e-9)
            count=0; nodata_count=0; minimum=None; maximum=None
            for _,window in ds.block_windows(1):
                a=ds.read(1,window=window,masked=True)
                count+=int(a.count());nodata_count+=int(a.size-a.count())
                if a.count():
                    lo=float(a.min());hi=float(a.max());minimum=lo if minimum is None else min(minimum,lo);maximum=hi if maximum is None else max(maximum,hi)
            layout=ds.tags(ns='IMAGE_STRUCTURE').get('LAYOUT')
            rec={'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'grid_aligned':bool(aligned),'layout':layout,'valid_values_band1':count,'nodata_band1':nodata_count,'min_band1':minimum,'max_band1':maximum}
            records.append(rec)
            if p.stat().st_size<=0:errors.append(f'empty file: {rec["path"]}')
            if not aligned:errors.append(f'grid mismatch: {rec["path"]}')
            if count==0:errors.append(f'no valid first-band data: {rec["path"]}')
            if layout!='COG':warnings.append(f'not stored as a cloud optimized GeoTIFF: {rec["path"]} (layout={layout}); valid tiled GeoTIFF retained without overwrite')
    for rel in ['data/features/weather/era5_event_hourly_features.csv','data/features/weather/daily_era5_nasa_power_comparison.csv','data/features/reservoirs/kaggle_daily_storage_features.csv','data/features/reservoirs/opencity_monthly_storage_tidy.csv','data/features/osm/osm_graph_summary.json']:
        p=ROOT/rel
        if p.exists() and p.stat().st_size==0:errors.append(f'empty table/summary: {rel}')
    result={'expected_grid':{'width':expected[0],'height':expected[1],'crs':expected[2],'transform':expected[3]},'rasters_checked':len(records),'raster_records':records,'warnings':warnings,'errors':errors,'passed':not errors}
    out=ROOT/'docs'/'PHASE3_VALIDATION.json';out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'rasters_checked':len(records),'passed':not errors,'warnings':warnings,'errors':errors,'validation_file':out.relative_to(ROOT).as_posix()},indent=2))
    if errors:raise SystemExit(1)
if __name__=='__main__':main()
