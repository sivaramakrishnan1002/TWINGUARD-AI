#!/usr/bin/env python
"""Exploratory flood-label checks. Never produces final training labels."""
import io,json,zipfile
from pathlib import Path
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.shutil import copy as rio_copy
from rasterio.features import geometry_mask,rasterize
from rasterio.warp import Resampling,reproject
from affine import Affine
from shapely.geometry import mapping

ROOT=Path(__file__).resolve().parents[2]; RAW=ROOT/'data/raw'; OUT=ROOT/'data/processed/labels_inspection'; GRID_PATH=ROOT/'data/processed/grid/grid_definition.json'
def main():
    OUT.mkdir(parents=True,exist_ok=True); grid=json.loads(GRID_PATH.read_text()); crs=grid['crs']; tr=Affine(*grid['transform']); shape=(grid['height'],grid['width'])
    boundary=gpd.read_file(RAW/'boundary/chennai_cma_boundary.geojson').to_crs(crs); poly=boundary.geometry.union_all()
    zpath=next((RAW/'historical_floods/2015/2015-12-04').glob('*.zip'))
    base='zip://'+zpath.as_posix()+'!'
    layers={'2015-09-01':'S1_20150901_PreFlood','2015-10-14':'LS8_20151014_PreFlood','2015-11-12':'S1_20151112_Flood','2015-11-24':'S1_20151124_Flood'}
    rasters={}; stats={}
    for date,name in layers.items():
        g=gpd.read_file(base+name+'.shp')
        g=g.to_crs(crs)
        ix=g.sindex.query(poly,predicate='intersects'); selected=g.iloc[ix]
        if len(selected):
            geoms=[geom.intersection(poly) for geom in selected.geometry if geom is not None and geom.intersects(poly)]
        else: geoms=[]
        if date in ('2015-09-01','2015-10-14'):
            vals=[]
            for _,row in selected.iterrows():
                geom=row.geometry.intersection(poly)
                if geom.is_empty: continue
                cat=str(row.get('Water_Clas',''))
                code=1 if 'Satellite Detected Water' in cat else 2
                vals.append((mapping(geom),code))
            arr=rasterize(vals,out_shape=shape,transform=tr,fill=0,dtype='uint8',all_touched=False)
            typ='PreFlood reference, exploratory only (1 satellite detected water, 2 possible saturated/wet soil; source says static/no water change)'
        else:
            arr=rasterize([(mapping(gm),1) for gm in geoms],out_shape=shape,transform=tr,fill=0,dtype='uint8',all_touched=False)
            typ='UNOSAT observed event layer, exploratory only; not Dec 1-8 peak'
        rasters[date]=arr
        path=OUT/f'{date}_EXPLORATORY_NOT_FINAL.tif'
        tmp=path.with_name(path.stem+'_temporary.tif')
        with rasterio.open(tmp,'w',driver='GTiff',width=grid['width'],height=grid['height'],count=1,dtype='uint8',crs=crs,transform=tr,nodata=255,tiled=True,blockxsize=256,blockysize=256,compress='DEFLATE') as dst: dst.write(arr,1)
        rio_copy(tmp,path,driver='COG',compress='DEFLATE',blocksize=256,overview_resampling='nearest');tmp.unlink()
        stats[date]={'features_intersecting_CMA':int(len(selected)),'source_class_counts':selected['Water_Clas'].astype(str).value_counts().to_dict(),'raster_nonzero_cells':int((arr>0).sum()),'rasterized_area_km2':float((arr>0).sum()*900/1e6),'role':typ}
    baseline=((rasters['2015-09-01']>0)|(rasters['2015-10-14']>0))
    flood=((rasters['2015-11-12']>0)|(rasters['2015-11-24']>0))
    residual=flood&~baseline
    baseline_test=residual.astype('uint8')
    path=OUT/'november_flood_minus_sep_oct_reference_TEST_ONLY.tif';tmp=path.with_name(path.stem+'_temporary.tif')
    with rasterio.open(tmp,'w',driver='GTiff',width=grid['width'],height=grid['height'],count=1,dtype='uint8',crs=crs,transform=tr,nodata=255,tiled=True,blockxsize=256,blockysize=256,compress='DEFLATE') as dst: dst.write(baseline_test,1)
    rio_copy(tmp,path,driver='COG',compress='DEFLATE',blocksize=256,overview_resampling='nearest');tmp.unlink()
    # GFD event max extent, counted on native 0.0022458 degree MODIS grid by pixel centre.
    zp=RAW/'historical_floods/2015/global_flood_database/DFO_4309_From_20151110_to_20151204.zip'
    with zipfile.ZipFile(zp) as arc:
        tif=next(n for n in arc.namelist() if n.lower().endswith('.tif'))
        with rasterio.open('/vsizip/'+zp.resolve().as_posix()+'/'+tif) as src:
            b4326=boundary.to_crs(src.crs)
            win=rasterio.windows.from_bounds(*b4326.total_bounds,transform=src.transform).round_offsets().round_lengths()
            win=win.intersection(rasterio.windows.Window(0,0,src.width,src.height))
            transform=src.window_transform(win); a=src.read(1,window=win)
            inside=geometry_mask([mapping(b4326.geometry.union_all())],out_shape=a.shape,transform=transform,invert=True,all_touched=False)
            flood_count=int(((a==1)&inside).sum()); total_inside=int(inside.sum())
            res=src.res; midlat=float(b4326.geometry.union_all().centroid.y)
            nominal_km2=abs(res[0]*111320*np.cos(np.radians(midlat))*res[1]*110574)/1e6
            gfd={'event_id':4309,'event_start':'2015-11-10','event_end':'2015-12-04','event_centroid':[78.855441,11.827777],'flooded_pixel_centres_inside_CMA':flood_count,'approx_area_km2_nominal_pixel_area':flood_count*nominal_km2,'nominal_resolution_degrees':list(res),'approx_pixel_size_m_at_CMA_latitude':[float(res[0]*111320*np.cos(np.radians(midlat))),float(res[1]*110574)],'method':'native MODIS event-grid band 1 value==1, pixel-centre inclusion within CMA; approximate cell-area estimate, coarse (~250 m), not Chennai-specific verified event mask','cma_grid_pixels_sampled':total_inside}
    # OpenCity KML: observed point files kept separate from modeled return-period hazards.
    oc=[]
    b4326=boundary.to_crs('EPSG:4326').geometry.union_all()
    import pandas as pd
    manifest=pd.read_csv(ROOT/'docs'/'DATA_MANIFEST.csv',encoding='utf-8-sig')
    titles={Path(str(row['filename'])).name:str(row['dataset']) for _,row in manifest.iterrows() if str(row.get('filename','')).startswith('historical_floods/2015/opencity_flood_points/')}
    for p in sorted((RAW/'historical_floods/2015/opencity_flood_points').glob('*.kml')):
        g=gpd.read_file(p)
        if g.crs is None: g=g.set_crs('EPSG:4326')
        g=g.to_crs('EPSG:4326'); inside_count=0; invalid=0
        for geom in g.geometry:
            if geom is None or geom.is_empty: continue
            try: inside_count += int(geom.intersects(b4326))
            except Exception: invalid += 1
        title=titles.get(p.name,'unknown')
        category='modeled hazard zone' if ('return period' in title.lower() or 'hazard zone' in title.lower() or 'flows' in title.lower()) else ('observed points/incidents' if 'point' in title.lower() else 'source type needs review')
        oc.append({'file':p.name,'dataset':title,'category':category,'features_total':len(g),'geometry_types':','.join(sorted(g.geometry.geom_type.unique())),'features_intersecting_CMA':inside_count,'invalid_or_failed_spatial_predicates':invalid,'interpretation':'modeled hazard polygons must not be described as observed flood extent; confirm metadata before label use'})
    pd.DataFrame(oc).to_csv(OUT/'opencity_kml_CMA_inventory.csv',index=False)
    result={'unosat_layers':stats,'baseline_reference_test':{'overlap_pixels':int((flood&baseline).sum()),'gross_november_rasterized_km2':float(flood.sum()*900/1e6),'after_subtracting_sep_oct_reference_km2':float(residual.sum()*900/1e6),'warning':'idea to verify: baseline classes are Satellite Detected Water or possible wet soil and source Water_Stat says no water change/static level. This simple union subtraction is exploratory only, not a validated water/flood distinction.'},'global_flood_database':gfd,'opencity':oc}
    (OUT/'label_inspection_summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

def poly_transform(frame,crs): return frame.to_crs(crs).geometry.union_all()
if __name__=='__main__': main()
