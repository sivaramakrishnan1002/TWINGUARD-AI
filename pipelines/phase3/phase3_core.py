#!/usr/bin/env python
"""Reproducible, raw-read-only Phase 3 grid and raster feature preparation."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.shutil import copy as rio_copy
from affine import Affine
from rasterio.features import rasterize
from rasterio.warp import Resampling, reproject, transform_bounds
from shapely.geometry import mapping

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
FEATURES = ROOT / "data" / "features"
GRID_JSON = PROCESSED / "grid" / "grid_definition.json"
CRS = "EPSG:32644"
RES = 30.0
NODATA = -9999.0


def boundary():
    frame = gpd.read_file(RAW / "boundary" / "chennai_cma_boundary.geojson")
    if frame.crs is None or frame.empty:
        raise ValueError("CMA boundary is empty or has no CRS")
    return frame.to_crs(CRS)


def load_grid():
    if not GRID_JSON.exists():
        raise FileNotFoundError("Run --task grid first")
    return json.loads(GRID_JSON.read_text(encoding="utf-8"))


def profile(grid, dtype, nodata, compress="DEFLATE"):
    return dict(driver="GTiff", width=grid["width"], height=grid["height"], count=1,
                dtype=dtype, crs=CRS, transform=Affine(*grid["transform"]),
                nodata=nodata, tiled=True, blockxsize=256, blockysize=256,
                compress=compress, predictor=2 if dtype.startswith("float") else 1,
                BIGTIFF="IF_SAFER")


def write_cog(path, array, grid, dtype=None, nodata=NODATA):
    path.parent.mkdir(parents=True, exist_ok=True)
    dt = dtype or str(array.dtype)
    temp=path.with_name(path.stem+"_temporary.tif")
    with rasterio.open(temp, "w", **profile(grid, dt, nodata)) as dst:
        dst.write(array.astype(dt, copy=False), 1)
        factors = [f for f in (2, 4, 8, 16) if min(array.shape) // f >= 128]
        if factors:
            dst.build_overviews(factors, Resampling.nearest if dt.startswith("uint") else Resampling.average)
            dst.update_tags(ns="rio_overview", resampling="nearest" if dt.startswith("uint") else "average")
    rio_copy(temp,path,driver="COG",compress="DEFLATE",blocksize=256,
             overview_resampling="nearest" if dt.startswith("uint") else "average",BIGTIFF="IF_SAFER")
    temp.unlink()


def make_grid():
    poly = boundary().geometry.union_all()
    xmin, ymin, xmax, ymax = poly.bounds
    xmin -= 2000; ymin -= 2000; xmax += 2000; ymax += 2000
    left = math.floor(xmin / RES) * RES
    bottom = math.floor(ymin / RES) * RES
    right = math.ceil(xmax / RES) * RES
    top = math.ceil(ymax / RES) * RES
    width = int(round((right-left)/RES)); height = int(round((top-bottom)/RES))
    transform = [RES, 0.0, left, 0.0, -RES, top]
    grid = {"crs": CRS, "resolution_m": RES, "width": width, "height": height,
            "bounds_projected_m": [left, bottom, right, top], "transform": transform,
            "alignment_origin_m": [0, 0], "buffer_m": 2000,
            "boundary_source": "data/raw/boundary/chennai_cma_boundary.geojson",
            "mask_rule": "pixel-centre-in-boundary (all_touched=false)",
            "resampling": {"continuous": "bilinear", "categorical": "nearest",
                           "population_counts": "sum-preserving resampling (rasterio Resampling.sum)"}}
    GRID_JSON.parent.mkdir(parents=True, exist_ok=True)
    GRID_JSON.write_text(json.dumps(grid, indent=2)+"\n", encoding="utf-8")
    mask = rasterize([(mapping(poly), 1)], out_shape=(height,width), transform=Affine(*transform),
                     fill=0, dtype="uint8", all_touched=False)
    write_cog(PROCESSED / "grid" / "cma_mask.tif", mask, grid, "uint8", 255)
    return grid


def dest_valid_mask(grid):
    with rasterio.open(PROCESSED / "grid" / "cma_mask.tif") as src:
        return src.read(1) == 1


def warp_source(src_path, grid, resampling, nodata=NODATA, dtype="float32"):
    dst = np.full((grid["height"], grid["width"]), nodata, dtype=dtype)
    with rasterio.open(src_path) as src:
        reproject(source=rasterio.band(src, 1), destination=dst,
                  src_transform=src.transform, src_crs=src.crs, src_nodata=src.nodata,
                  dst_transform=Affine(*grid["transform"]), dst_crs=CRS,
                  dst_nodata=nodata, resampling=resampling, init_dest_nodata=False,
                  num_threads=2)
    return dst


def terrain():
    grid = load_grid()
    dest = np.full((grid["height"],grid["width"]), NODATA, dtype="float32")
    dem_paths = sorted((RAW/"dem").glob("*.tif"))
    if len(dem_paths) != 4:
        raise ValueError(f"Expected four logged DEM tiles; found {len(dem_paths)}")
    for p in dem_paths:
        with rasterio.open(p) as src:
            reproject(rasterio.band(src,1), dest, src_transform=src.transform, src_crs=src.crs,
                      src_nodata=src.nodata, dst_transform=Affine(*grid["transform"]), dst_crs=CRS,
                      dst_nodata=NODATA, resampling=Resampling.bilinear, init_dest_nodata=False,
                      num_threads=2)
    cma_mask = dest_valid_mask(grid)
    valid = np.isfinite(dest) & (dest != NODATA)
    dest[~valid] = NODATA
    out = FEATURES/"terrain"; out.mkdir(parents=True, exist_ok=True)
    write_cog(out/"elevation_m.tif", dest, grid)
    # Cell-scale derivatives from the 30 m projected elevation surface.
    z = dest.astype("float64"); z[~valid] = np.nan
    gy, gx = np.gradient(z, RES, RES)
    slope = np.degrees(np.arctan(np.hypot(gx,gy))).astype("float32")
    aspect = ((np.degrees(np.arctan2(-gx,-gy))+360)%360).astype("float32")
    slope[~valid] = NODATA; aspect[~valid] = NODATA
    write_cog(out/"slope_deg.tif", slope, grid)
    write_cog(out/"aspect_deg.tif", aspect, grid)
    # Laplacian curvature as a simple, explicitly named second-derivative proxy.
    dgy_dy, dgy_dx = np.gradient(gy, RES, RES)
    dgx_dy, dgx_dx = np.gradient(gx, RES, RES)
    curvature = (dgx_dx+dgy_dy).astype("float32"); curvature[~valid] = NODATA
    write_cog(out/"curvature_laplacian_per_m.tif", curvature, grid)
    # D8 routing on unconditioned DSM: direction codes 1..8, 0 for no lower neighbour.
    # Accumulation follows strictly descending elevation routes; sinks are retained.
    h,w = dest.shape
    best = np.zeros((h,w), dtype="float32")
    direction = np.zeros((h,w), dtype="uint8")
    downstream = np.full((h,w), -1, dtype="int64")
    offsets = [(-1,0),( -1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1)]
    for code,(dy,dx) in enumerate(offsets,1):
        ys=slice(max(0,-dy),min(h,h-dy)); xs=slice(max(0,-dx),min(w,w-dx))
        yn=slice(max(0,dy),min(h,h+dy)); xn=slice(max(0,dx),min(w,w+dx))
        dz=(z[ys,xs]-z[yn,xn])/(RES*(math.sqrt(2) if dy and dx else 1))
        eligible=valid[ys,xs]&valid[yn,xn]&(dz>best[ys,xs])
        best_view=best[ys,xs]; best_view[eligible]=dz[eligible]
        dir_view=direction[ys,xs]; dir_view[eligible]=code
        src_y,src_x=np.mgrid[ys,xs]
        down_view=downstream[ys,xs]; down_view[eligible]=(src_y[eligible]+dy)*w+(src_x[eligible]+dx)
    flow=direction.copy(); flow[~valid]=255
    write_cog(out/"flow_direction_d8.tif",flow,grid,"uint8",255)
    accum=np.zeros(h*w,dtype="float32"); accum[valid.ravel()]=1
    # Route high-to-low in sorted order so each cell receives upstream counts first.
    order=np.flatnonzero(valid.ravel())
    order=order[np.argsort(-z.ravel()[order], kind="stable")]
    down=downstream.ravel()
    for i in order:
        j=down[i]
        if j>=0: accum[j]+=accum[i]
    accum=accum.reshape(h,w); accum[~valid]=NODATA
    write_cog(out/"flow_accumulation_cells_d8.tif",accum,grid)
    # TWI proxy uses contributing area per contour width and slope floor 0.1 degree.
    slope_rad=np.maximum(np.radians(np.maximum(slope,0)),np.radians(0.1))
    twi=np.log((np.maximum(accum,1)*RES/np.maximum(np.tan(slope_rad),1e-6)).astype("float64")).astype("float32")
    twi[~valid]=NODATA
    write_cog(out/"twi_d8_proxy.tif",twi,grid)
    return {"valid_cells_buffered_grid":int(valid.sum()),"cma_valid_cells":int((valid&cma_mask).sum()),"elevation_min_m_cma":float(np.nanmin(dest[cma_mask&valid])),"elevation_max_m_cma":float(np.nanmax(dest[cma_mask&valid])),"slope_max_deg_cma":float(np.nanmax(slope[cma_mask&valid])),"sink_cells_cma":int(((direction==0)&valid&cma_mask).sum())}


def categorical():
    grid=load_grid(); mask=dest_valid_mask(grid)
    p=RAW/"landcover"/"ESA_WorldCover_10m_2021_v200_N12E078_Map.tif"
    data=warp_source(p,grid,Resampling.mode,nodata=0,dtype="uint8")
    out=FEATURES/"landcover"; write_cog(out/"worldcover_2021_class.tif",data,grid,"uint8",0)
    classes,counts=np.unique(data[mask],return_counts=True)
    (out/"class_counts_cma.json").write_text(json.dumps({str(int(c)):int(n) for c,n in zip(classes,counts)},indent=2)+"\n",encoding="utf-8")
    # Area-weighted class fractions: reproject one-hot 10 m masks to each target 30 m cell.
    codes=[10,20,30,40,50,60,70,80,90,95,100]
    frac=np.zeros((len(codes),grid["height"],grid["width"]),dtype="float32")
    block=256
    with rasterio.open(p) as src:
        for row in range(0,grid['height'],block):
            for col in range(0,grid['width'],block):
                hh=min(block,grid['height']-row); ww=min(block,grid['width']-col)
                dst_tr=Affine(*grid['transform'])*Affine.translation(col,row)
                left=dst_tr.c; top=dst_tr.f; right=left+ww*RES; bottom=top-hh*RES
                ll=transform_bounds(CRS,src.crs,left,bottom,right,top,densify_pts=9)
                win=rasterio.windows.from_bounds(*ll,transform=src.transform).round_offsets().round_lengths()
                win=win.intersection(rasterio.windows.Window(0,0,src.width,src.height))
                if win.width<=0 or win.height<=0:continue
                raw=src.read(1,window=win)
                for bi,code in enumerate(codes):
                    target=np.full((hh,ww),-9999.0,dtype="float32")
                    reproject(source=(raw==code).astype("uint8"),destination=target,
                              src_transform=src.window_transform(win),src_crs=src.crs,src_nodata=255,
                              dst_transform=dst_tr,dst_crs=CRS,dst_nodata=-9999,resampling=Resampling.average,
                              num_threads=2)
                    target[target==-9999]=0
                    target[target<1e-7]=0
                    frac[bi,row:row+hh,col:col+ww]=target
    out.mkdir(parents=True,exist_ok=True); mult=out/"worldcover_2021_area_fractions_30m.tif"; tmp=mult.with_name(mult.stem+"_temporary.tif")
    with rasterio.open(tmp,"w",driver="GTiff",width=grid['width'],height=grid['height'],count=len(codes),dtype="float32",crs=CRS,transform=Affine(*grid['transform']),nodata=-9999,tiled=True,blockxsize=256,blockysize=256,compress="DEFLATE",predictor=2,BIGTIFF="IF_SAFER") as dst:
        for i,c in enumerate(codes,1):dst.write(frac[i-1],i);dst.set_band_description(i,f"class_{c}_area_fraction")
    rio_copy(tmp,mult,driver="COG",compress="DEFLATE",blocksize=256,overview_resampling="average",BIGTIFF="IF_SAFER");tmp.unlink()
    means={str(code):float(frac[i][mask].mean()) for i,code in enumerate(codes)}
    (out/"class_area_fraction_means_cma.json").write_text(json.dumps(means,indent=2)+"\n",encoding="utf-8")
    return {"class_codes":classes.tolist(),"cma_cells":int(mask.sum()),"area_fraction_bands":len(codes),"mean_class_fractions_cma":means}


def population():
    grid=load_grid(); mask=dest_valid_mask(grid)
    p=RAW/"population"/"ind_pop_2021_CN_100m_R2025A_v1.tif"
    data=warp_source(p,grid,Resampling.sum,nodata=NODATA,dtype="float32")
    # Retain buffered-grid cells; compute the summary strictly inside the CMA boundary.
    valid=mask&(data!=NODATA)&np.isfinite(data)
    out=FEATURES/"population"; write_cog(out/"worldpop_2021_sum_resampled_30m.tif",data,grid)
    return {"cma_cells":int(mask.sum()),"positive_cells":int((valid&(data>0)).sum()),"zero_cells":int((valid&(data==0)).sum()),"nodata_cells":int((mask&~valid).sum()),"sum_model_estimate":float(data[valid].sum()),"resampling":"rasterio Resampling.sum; verify conservation against source zonal total"}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--task",choices=["grid","terrain","landcover","population","all"],default="all")
    args=parser.parse_args()
    result={}
    if args.task in ("grid","all"):
        g=make_grid(); result["grid"]={k:g[k] for k in ("crs","resolution_m","width","height","bounds_projected_m","buffer_m")}
    if args.task in ("terrain","all"): result["terrain"]=terrain()
    if args.task in ("landcover","all"): result["landcover"]=categorical()
    if args.task in ("population","all"): result["population"]=population()
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
