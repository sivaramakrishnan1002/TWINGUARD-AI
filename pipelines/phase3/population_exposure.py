#!/usr/bin/env python
"""Summarize model population near roads and facilities; buffers are proxy exposure."""
from pathlib import Path
import json
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from affine import Affine
from rasterio.features import rasterize
from rasterio.shutil import copy as rio_copy

ROOT=Path(__file__).resolve().parents[2]; GRID=ROOT/'data/processed/grid/grid_definition.json'; POP=ROOT/'data/features/population/worldpop_2021_sum_resampled_30m.tif'; ROADS=ROOT/'data/features/roads/chennai_road_graph.gpkg'; FACILITIES=ROOT/'data/features/facilities/chennai_facilities.gpkg'; OUT=ROOT/'data/processed/exposure'
def save_cog(path,array,src):
    if path.exists():
        # A previous interrupted run may already have created this derived mask.
        # Preserve it and let the validation stage check its grid/COG structure.
        return
    temp=path.with_name(path.stem+'_temporary.tif')
    with rasterio.open(temp,'w',driver='GTiff',width=src.width,height=src.height,count=1,dtype='uint8',crs=src.crs,transform=src.transform,nodata=255,tiled=True,blockxsize=256,blockysize=256,compress='DEFLATE') as dst:dst.write(array,1)
    rio_copy(temp,path,driver='COG',compress='DEFLATE',blocksize=256,overview_resampling='nearest');temp.unlink()
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    roads=gpd.read_file(ROADS,layer='road_segments'); facilities=gpd.read_file(FACILITIES,layer='facilities')
    with rasterio.open(POP) as pop:
        vals=pop.read(1); valid=(vals!=pop.nodata)&np.isfinite(vals); gridmask=rasterio.open(ROOT/'data/processed/grid/cma_mask.tif').read(1)==1
        roads_in=roads[roads.geometry.notna()&~roads.geometry.is_empty]
        # Union-like rasterization of 100 m road buffers counts a population cell once.
        road_path=OUT/'road_network_100m_buffer_mask.tif'; fac_path=OUT/'facility_500m_union_mask.tif'
        if road_path.exists():
            with rasterio.open(road_path) as src:
                if (src.width,src.height,src.transform,src.crs)!=(pop.width,pop.height,pop.transform,pop.crs):raise ValueError('Existing road buffer mask grid differs from population grid')
                road_mask=src.read(1)
        else:
            road_shapes=((geom.buffer(100),1) for geom in roads_in.geometry)
            road_mask=rasterize(road_shapes,out_shape=(pop.height,pop.width),transform=pop.transform,fill=0,dtype='uint8',all_touched=False)
        if fac_path.exists():
            with rasterio.open(fac_path) as src:
                if (src.width,src.height,src.transform,src.crs)!=(pop.width,pop.height,pop.transform,pop.crs):raise ValueError('Existing facility buffer mask grid differs from population grid')
                fac_mask=src.read(1)
        else:
            fac_shapes=((geom.buffer(500),1) for geom in facilities.geometry if geom is not None and not geom.is_empty)
            fac_mask=rasterize(fac_shapes,out_shape=(pop.height,pop.width),transform=pop.transform,fill=0,dtype='uint8',all_touched=False)
        cma=gridmask
        for name,arr in [('road_network_100m_buffer_mask.tif',road_mask),('facility_500m_union_mask.tif',fac_mask)]:save_cog(OUT/name,arr,pop)
        summaries={}
        for name,arr in [('all_mapped_roads_100m',road_mask),('all_osm_facilities_500m_union',fac_mask)]:
            m=(arr==1)&cma; dat=vals[m]; good=(dat!=pop.nodata)&np.isfinite(dat)
            summaries[name]={'CMA_buffer_cells':int(m.sum()),'valid_population_cells':int(good.sum()),'nodata_cells':int((~good).sum()),'population_model_estimate_sum':float(dat[good].sum()),'exposure_buffer':'100 m around mapped road segments' if 'roads' in name else '500 m circles around mapped OSM facility points','interpretation':'2021 WorldPop alpha constrained model estimate; buffers measure proximity exposure, not people on roads or service-area reach'}
        # Per-facility 500 m circle sums are overlapping catchments and must not be added together.
        rows=[]; tr=pop.transform; radius_m=500.0
        # OSM facilities in this extraction are points. Pixel-centre distances
        # reproduce a 500 m circular buffer while avoiding thousands of GEOS masks.
        reach=int(np.ceil(radius_m/min(abs(tr.a),abs(tr.e))))+1
        offsets=np.arange(-reach,reach+1)
        oy,ox=np.meshgrid(offsets,offsets,indexing='ij')
        dx=(ox+0.5)*tr.a; dy=(oy+0.5)*tr.e
        for row in facilities.itertuples():
            x,y=row.geometry.x,row.geometry.y
            col=int(np.floor((x-tr.c)/tr.a)); rr=int(np.floor((y-tr.f)/tr.e))
            # Select cells whose centres fall within the 500 m circle.
            keep=(dx+(tr.c+(col+0.5)*tr.a-x-(tr.a*0.5)))**2 + (dy+(tr.f+(rr+0.5)*tr.e-y-(tr.e*0.5)))**2 <= radius_m**2
            rs=rr+oy[keep]; cs=col+ox[keep]
            inside=(rs>=0)&(rs<pop.height)&(cs>=0)&(cs<pop.width)
            rs,cs=rs[inside],cs[inside]
            in_cma=gridmask[rs,cs]
            rs,cs=rs[in_cma],cs[in_cma]
            dat=vals[rs,cs]; good=(dat!=pop.nodata)&np.isfinite(dat)
            rows.append({'osmid':getattr(row,'osmid',None),'category':getattr(row,'category',None),'name':getattr(row,'name',None),'nearest_road_distance_m':getattr(row,'nearest_road_distance_m',None),'population_within_500m_model_estimate':float(dat[good].sum()),'valid_cells':int(good.sum()),'nodata_cells':int((~good).sum()),'note':'overlapping 500 m circles; do not sum these rows as unique people'})
        csv_path=OUT/'osm_facility_500m_population_estimates.csv'; summary_path=OUT/'population_exposure_summary.json'
        if csv_path.exists() or summary_path.exists():raise FileExistsError('Refusing to overwrite an existing exposure summary output')
        pd.DataFrame(rows).to_csv(csv_path,index=False)
        result={'source':'WorldPop R2025A 2021 constrained model; raw source unmodified','crs':pop.crs.to_string(),'grid_resolution_m':pop.res,'summary':summaries,'facilities_with_500m_summary':len(rows),'method':'pixel-centre inclusion, sum of 30 m sum-resampled model counts; nodata remains excluded','caveats':['WorldPop is alpha and is a model estimate, not a census.','OSM road/facility coverage may be incomplete.','Overlapping catchment totals are not unique population totals.','Road buffer means proximity only; it is not evacuation exposure or road accessibility.']}
        summary_path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
