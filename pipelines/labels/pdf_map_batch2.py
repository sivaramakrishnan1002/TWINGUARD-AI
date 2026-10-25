"""Extract and diagnose the existing NRSC 2023 GeoPDF map; no raw PDF is modified."""
from __future__ import annotations
import json, math, sys
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject
from rasterio.features import shapes
from shapely.geometry import shape
from pyproj import Transformer
from PIL import Image
from pypdf import PdfReader
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
PDF=ROOT/'data/raw/historical_floods/2023/tncyclone50dsc07122023_0600hrs_map.pdf'
RENDER=ROOT/'tmp/pdfs/cyclone2023_200dpi.png'
OUT=ROOT/'data/features/labels/map_batch2'
REPORT=ROOT/'docs/GEO_PDF_LABELS_BATCH2.md'
EVAL=ROOT/'docs/PHASE9C_OUT_OF_EVENT_2023.md'
RASTER_OUT=OUT/'nrsc_2023_dec07_preliminary_red_class_native_geopdf.tif'
POLY_OUT=OUT/'nrsc_2023_dec07_preliminary_red_class.gpkg'
QA_PNG=ROOT/'docs/figures/nrsc_2023_dec07_geopdf_overlay.png'


def red_class(rgb: np.ndarray) -> np.ndarray:
    a=np.asarray(rgb)
    return (a[...,0]>=170)&(a[...,0]>1.6*a[...,1])&(a[...,0]>1.4*a[...,2])&(a[...,1]<150)&(a[...,2]<150)


def georef_bbox_from_measure(page, raster_width, raster_height, dpi=200):
    view=next(v for v in page['/VP'] if v.get('/Name')=='Layers')
    measure=view['/Measure'].get_object()
    if str(measure.get('/Subtype'))!='/GEO' or len(measure.get('/GPTS',[]))!=8:
        raise ValueError('Expected four GeoPDF geographic control coordinates')
    gpts=np.asarray(measure['/GPTS'],dtype=float).reshape(4,2)
    # GeoPDF LPTS order is lower-left, upper-left, upper-right, lower-right here.
    south=float(min(gpts[:,0])); north=float(max(gpts[:,0])); west=float(min(gpts[:,1])); east=float(max(gpts[:,1]))
    if not (south<north and west<east): raise ValueError('GeoPDF corner coordinates are not a nonzero extent')
    # The first viewport is the map frame. The page's embedded strip width is
    # 2695 px and matches the frame at 200 dpi; using the geographic corner set
    # yields a north-up, unrotated display extent.
    return from_bounds(west,south,east,north,raster_width,raster_height), (west,south,east,north), measure


def run():
    for p in (RASTER_OUT,POLY_OUT,REPORT,EVAL,QA_PNG):
        if p.exists(): raise FileExistsError(f'Refusing to overwrite {p.relative_to(ROOT)}')
    if not PDF.exists() or not RENDER.exists(): raise FileNotFoundError('Required local PDF or 200 dpi page render is missing')
    reader=PdfReader(PDF); page=reader.pages[0]
    # Crop the viewport from the full-page raster. PDF points convert to pixels at dpi/72.
    viewport=next(v for v in page['/VP'] if v.get('/Name')=='Layers')
    box=[float(x) for x in viewport['/BBox']]
    scale=200.0/72.0
    page_h=float(page.mediabox.height)
    left,top,right,bottom=box
    crop=(round(left*scale),round((page_h-top)*scale),round(right*scale),round((page_h-bottom)*scale))
    with Image.open(RENDER) as im:
        pane=im.crop(crop).convert('RGB')
        rgb=np.asarray(pane)
    # Exclude the red legend swatch at the bottom-right of the map frame.
    cls=red_class(rgb)
    h,w=cls.shape
    cls[max(0,h-430):min(h,h-260),max(0,w-760):min(w,w-300)]=False
    transform,bounds,measure=georef_bbox_from_measure(page,w,h)
    west,south,east,north=bounds
    with rasterio.open(RASTER_OUT,'w',driver='GTiff',width=w,height=h,count=1,dtype='uint8',crs='EPSG:4326',transform=transform,nodata=255,compress='deflate') as dst:
        dst.write(np.where(cls,1,0).astype('uint8'),1); dst.set_band_description(1,'Red legend class: Flood / Standing Water due to Rains; preliminary NRSC map class')
        dst.update_tags(status='PRELIMINARY MAP DIGITISATION; NOT QA ACCEPTED',source=PDF.name,legend='red flood / standing water due to rains',map_date='2023-12-07',georeferencing='GeoPDF /GPTS /GCS WGS84')
    # Polygonise the exact red class from the native map-frame pixel grid.
    from pyproj import CRS
    geoms=[]
    for geom,val in shapes(cls.astype('uint8'),mask=cls,transform=transform,connectivity=8):
        if val==1: geoms.append(shape(geom))
    import geopandas as gpd
    if geoms:
        gdf=gpd.GeoDataFrame({'event':['Michaung 2023']*len(geoms),'map_date':['2023-12-07']*len(geoms),'source':['NRSC NDEM GeoPDF']*len(geoms),'class':['Flood / Standing Water due to Rains']*len(geoms),'qa_status':['PRELIMINARY_NOT_ACCEPTED']*len(geoms)},geometry=geoms,crs='EPSG:4326')
        gdf.to_file(POLY_OUT,layer='preliminary_red_class',driver='GPKG')
    else: raise ValueError('No red legend-class pixels found in map viewport')
    # Resample map class to the project grid for a cautious cross-check only.
    template=ROOT/'data/features/terrain/elevation_m.tif'
    with rasterio.open(template) as dem:
        shape_grid=(dem.height,dem.width); profile=dem.profile.copy(); dst_transform=dem.transform; dst_crs=dem.crs
    projected=np.full(shape_grid,255,dtype=np.uint8)
    with rasterio.open(RASTER_OUT) as src:
        reproject(src.read(1),projected,src_transform=src.transform,src_crs=src.crs,src_nodata=255,dst_transform=dst_transform,dst_crs=dst_crs,dst_nodata=255,resampling=Resampling.nearest)
    table_path=ROOT/'data/features/static/cell_table_phase9b_v2.parquet'
    import pyarrow.parquet as pq
    tab=pq.read_table(table_path,columns=['row','col']).to_pandas(); rows=tab.row.to_numpy(int); cols=tab.col.to_numpy(int)
    cma=np.zeros(shape_grid,bool); cma[rows,cols]=True
    label=(projected==1)&cma
    # rasterized label may only have 0/1 where the PDF viewport covers grid cells
    covered=(projected!=255)&cma
    prob_path=ROOT/'data/features/predictions/phase9c_addendum_cr004_v6/radar_probability_mean_apparent.tif'
    obs_path=ROOT/'data/features/predictions/phase9c_addendum_cr004_v6/radar_observability_mask.tif'
    phys_path=ROOT/'data/features/terrain/urban_physical_v1/physical_susceptibility_rank.tif'
    def read_aligned(path):
        with rasterio.open(path) as src:
            a=np.full(shape_grid,np.nan,dtype=np.float32)
            reproject(src.read(1),a,src_transform=src.transform,src_crs=src.crs,src_nodata=src.nodata,dst_transform=dst_transform,dst_crs=dst_crs,dst_nodata=np.nan,resampling=Resampling.nearest)
            return a
    prob=read_aligned(prob_path); obs=read_aligned(obs_path)>0; phys=read_aligned(phys_path)
    model_ids=covered&obs&np.isfinite(prob); physical_ids=covered&np.isfinite(phys)
    def score(pred,mask):
        y=label[mask].astype(int); x=pred[mask]
        return {'n':int(mask.sum()),'positive_cells':int(y.sum()),'prevalence':float(y.mean()) if len(y) else None,
                'pr_auc':float(average_precision_score(y,x)) if len(y) and y.sum() else None,
                'roc_auc':float(roc_auc_score(y,x)) if len(np.unique(y))==2 else None}
    model_metrics=score(prob,model_ids); physical_metrics=score(phys,physical_ids)
    # Overlay at project grid for visual sanity against CMA boundary and existing OSM waterways.
    import geopandas as gpd
    import matplotlib.pyplot as plt
    boundary=gpd.read_file(ROOT/'data/raw/boundary/chennai_cma_boundary.geojson').to_crs(dst_crs)
    waterways=gpd.read_file(ROOT/'data/features/osm/chennai_osm_features.gpkg',layer='waterways').to_crs(dst_crs)
    fig,ax=plt.subplots(figsize=(8,8))
    ax.imshow(np.where(covered,label,np.nan),extent=(profile['transform'].c,profile['transform'].c+profile['transform'].a*shape_grid[1],profile['transform'].f+profile['transform'].e*shape_grid[0],profile['transform'].f),cmap='Reds',alpha=.65,interpolation='nearest')
    boundary.boundary.plot(ax=ax,color='black',linewidth=.7,label='CMA boundary')
    waterways.plot(ax=ax,color='#146c94',linewidth=.25,alpha=.7,label='OSM waterways')
    ax.set_title('NRSC 2023 GeoPDF red class (preliminary) on project grid'); ax.set_aspect('equal'); ax.legend(loc='lower left'); fig.tight_layout(); fig.savefig(QA_PNG,dpi=160); plt.close(fig)
    # GeoPDF has corners/extent and WGS84, but no unambiguous common point controls for residual calculation.
    info={'source_pdf':PDF.relative_to(ROOT).as_posix(),'page':1,'native_render_pixels':[w,h],'GeoPDF_GPTS':[float(x) for x in measure['/GPTS']],
          'GCS_WKT':str(measure.get('/GCS',{}).get('/WKT','')),'bbox_wgs84':[west,south,east,north],
          'red_class_pixels':int(cls.sum()),'polygon_count':len(geoms),'CMA_cells_covered':int(covered.sum()),'CMA_red_cells':int(label.sum()),
          'CMA_red_area_km2_30m_resampled':float(label.sum()*900/1e6), 'radar_observable_cross_check':model_metrics,'physical_layer_cross_check':physical_metrics,
          'control_point_error_m':'NOT COMPUTED: no map graticule or unambiguous OSM-identifiable control points tied to exact PDF pixel positions; GeoPDF georeference still requires manual overlay QA.',
          'qa_status':'PRELIMINARY_NOT_ACCEPTED','map_disclaimer':'Map states preliminary, no ground verification, and flood class may include rain accumulation, low-lying water and paddy standing water.'}
    (OUT/'nrsc_2023_dec07_diagnostic.json').write_text(json.dumps(info,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    REPORT.write_text('# GeoPDF map inspection — Batch 2\n\n## Findings\n\n- 2023 Dec 7 Michaung map is a two-page NRSC rapid map based on RISAT-1A MRS SAR, pre-image 5 Nov 2023, post-image 7 Dec 2023. The first page contains a GeoPDF `/GEO` viewport with geographic `/GPTS` corners and WGS84 `/GCS`; automated placement in WGS84 is feasible. The red legend class is “Flood / Standing Water due to Rains.”\n- Embedded images were extracted in native resolution beneath `data/processed/pdf_maps/batch2/`; a diagnostic map-frame render was thresholded and polygonised. The resulting raster/vector are explicitly **PRELIMINARY_NOT_ACCEPTED**. The map itself warns that it has no ground verification and may include rain accumulation, low-lying water or paddy standing water.\n- Georeferencing residual against OSM is **not computed**: there is no graticule and no unambiguous OSM control point tied to an exact map-pixel coordinate. Therefore the polygon layer is not accepted as tier B/C and was not loaded into the label schema. Manual visual control-point QA is required first.\n- 2021 NRSC PDF has a GeoPDF viewport, but its projected `/GCS` WKT says WGS 84 / UTM zone 45N while its `/GPTS` points locate Chennai near 80.25°E (zone 44 area). CRS ambiguity is unresolved; manual-needed.\n- `tnflood50dsc12182023_1800hrs_vap1.pdf` is a 18 Dec 2023 Tuticorin district map, outside CMA; inspected and excluded from Chennai labels. No December 2015 maps were present under `data/raw/historical_floods/2015/december_maps`; skipped.\n\n## QA and outputs\n\nThe map class was identified from the red legend swatch and extracted as a preliminary diagnostic. The rendered class was overlaid on the CMA boundary and OSM waterways for visual inspection; exact OSM control-point RMS could not be measured, so no map geometry was accepted for training. The WGS84 GeoPDF viewport bbox, class pixel/polygon counts, and cross-check metrics are in `data/features/labels/map_batch2/nrsc_2023_dec07_diagnostic.json`. See `docs/figures/nrsc_2023_dec07_geopdf_overlay.png`.\n',encoding='utf-8')
    EVAL.write_text('# Phase 9C out-of-event check: 2023 map\n\nThis is a **preliminary map cross-check**, not independent validated event accuracy. The Phase 9C model was trained on a November 2015 SAR-derived label; the Dec 2023 NRSC GeoPDF is a different event, but the legend includes both flooding and standing/rain water and the map says no ground verification. GeoPDF provides a WGS84 viewport, but no OSM control-point RMS was available; therefore no tier B/C label was loaded.\n\n| Comparison domain | n cells | map-positive cells | prevalence | PR-AUC | ROC-AUC |\n|---|---:|---:|---:|---:|---:|\n'+f"| 2015 Phase 9C radar-observable cells | {model_metrics['n']} | {model_metrics['positive_cells']} | {model_metrics['prevalence']:.6f} | {model_metrics['pr_auc']:.6f} | {model_metrics['roc_auc']:.6f} |\n"+f"| New A04c physical score, full covered CMA | {physical_metrics['n']} | {physical_metrics['positive_cells']} | {physical_metrics['prevalence']:.6f} | {physical_metrics['pr_auc']:.6f} | {physical_metrics['roc_auc']:.6f} |\n\nMap-positive area in CMA after nearest-neighbour resampling to the 30 m analysis grid is about **{info['CMA_red_area_km2_30m_resampled']:.2f} km²**; this number is map-scale approximate, not a precise inundation area. The comparisons are documented as descriptive cross-checks only. The map class is not accepted as validation truth because it can include standing paddy/rain water, has no field verification, and lacks independently measured control-point residuals.\n",encoding='utf-8')
    print(json.dumps({'native_pixels':[w,h],'red_class_pixels':int(cls.sum()),'polygons':len(geoms),'cma_cells':int(covered.sum()),'red_cells':int(label.sum()),'radar':model_metrics,'physical':physical_metrics},indent=2))

if __name__=='__main__': run()
