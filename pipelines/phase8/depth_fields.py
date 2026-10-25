"""Create assumption-labelled depth fields from official flood extent polygons."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize
from scipy.ndimage import binary_erosion, label
from shapely import wkb
from sqlalchemy import text

from pipelines.stage5.db_common import make_engine

ROOT = Path(__file__).resolve().parents[2]
GRID = ROOT / "data/processed/grid/cma_mask.tif"
DEM = ROOT / "data/processed/terrain_cleaned/cleaned_elevation_m.tif"
OUT = ROOT / "data/features/depth/batch1_v1"
EVENTS = {"2015-11-12", "2015-11-24"}
NODATA = -9999.0


def depth_from_edge_surface(flood: np.ndarray, dem: np.ndarray, dem_nodata: float | int | None,
                            error_m: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Assign a local flat water surface per connected rasterized extent component."""
    if error_m < 0:
        raise ValueError("DEM error allowance must be non-negative")
    dem_ok=np.isfinite(dem) & ((dem!=dem_nodata) if dem_nodata is not None else True)
    flood=flood.astype(bool) & dem_ok
    components,ncomp=label(flood,structure=np.ones((3,3),dtype=np.uint8))
    mean=np.full(dem.shape,NODATA,dtype=np.float32)
    p05=np.full(dem.shape,NODATA,dtype=np.float32)
    p95=np.full(dem.shape,NODATA,dtype=np.float32)
    surface_levels=[]; component_sizes=[]; edge_sample_count=0; no_edge=0
    for component_id in range(1,ncomp+1):
        cells=components==component_id
        edge=cells & ~binary_erosion(cells,structure=np.ones((3,3),dtype=bool),border_value=0)
        edge_values=dem[edge & dem_ok]
        if not edge_values.size:
            no_edge+=1
            continue
        water_surface=float(np.median(edge_values))
        d=np.maximum(0.0,water_surface-dem[cells]).astype(np.float32)
        mean[cells]=d
        p05[cells]=np.maximum(0.0,d-error_m)
        p95[cells]=d+error_m
        surface_levels.append(water_surface)
        component_sizes.append(int(cells.sum()))
        edge_sample_count+=int(edge_values.size)
    surfaces=np.asarray(surface_levels,dtype=np.float64)
    return mean,p05,p95,{"components":int(ncomp),"components_without_valid_edge":no_edge,
                         "components_used":len(surface_levels),"component_edge_sample_count":edge_sample_count,
                         "component_water_surface_edge_median_summary":{
                             "min":float(surfaces.min()) if surfaces.size else None,
                             "median":float(np.median(surfaces)) if surfaces.size else None,
                             "p95":float(np.percentile(surfaces,95)) if surfaces.size else None,
                             "max":float(surfaces.max()) if surfaces.size else None},
                         "largest_component_cells":max(component_sizes) if component_sizes else 0,
                         "valid_flood_cells":int(np.count_nonzero(mean!=NODATA)),
                         "dem_error_allowance_m":error_m}


def fetch_official_event_geometries(event_date: str):
    engine=make_engine()
    try:
        with engine.connect() as conn:
            rows=conn.execute(text("""
                SELECT ST_AsBinary(ST_Intersection(l.geom, s.geom))
                FROM labels.v_usable_flood_labels l
                CROSS JOIN (SELECT ST_UnaryUnion(geom) AS geom FROM twinguard.study_area) s
                WHERE l.reference_role='event_flood' AND l.event_date=CAST(:event_date AS date)
                  AND l.tier='A' AND ST_Intersects(l.geom,s.geom)
                  AND NOT ST_IsEmpty(ST_Intersection(l.geom,s.geom))
            """),{"event_date":event_date}).fetchall()
    finally:
        engine.dispose()
    return [wkb.loads(bytes(row[0])) for row in rows]


def process_event(event_date: str, error_m: float, output_dir: Path=OUT) -> dict:
    geometries=fetch_official_event_geometries(event_date)
    if not geometries:
        raise RuntimeError(f"No tier A event geometry found for {event_date} in labels.v_usable_flood_labels")
    if any(path.exists() for path in [output_dir/f"depth_mean_{event_date}_UNOSAT_A_DERIVED.tif",
                                      output_dir/f"depth_p05_{event_date}_UNOSAT_A_DERIVED.tif",
                                      output_dir/f"depth_p95_{event_date}_UNOSAT_A_DERIVED.tif"]):
        raise FileExistsError(f"Depth output already exists for {event_date}; refusing overwrite")
    with rasterio.open(GRID) as grid_ds, rasterio.open(DEM) as dem_ds:
        profile=grid_ds.profile.copy()
        if grid_ds.crs.to_epsg()!=32644 or dem_ds.crs!=grid_ds.crs:
            raise ValueError("Expected aligned master grid and cleaned DEM in EPSG:32644")
        if (grid_ds.width,grid_ds.height)!=(dem_ds.width,dem_ds.height) or grid_ds.transform!=dem_ds.transform:
            raise ValueError("Master grid and cleaned DEM are not exactly aligned")
        cma=grid_ds.read(1)==1
        dem=dem_ds.read(1).astype(np.float32)
        dem_nodata=dem_ds.nodata
        flood=rasterize(((geom,1) for geom in geometries),out_shape=(grid_ds.height,grid_ds.width),
                        transform=grid_ds.transform,fill=0,dtype="uint8",all_touched=False)==1
        flood &= cma
        mean,p05,p95,details=depth_from_edge_surface(flood,dem,dem_nodata,error_m)
        profile.update(dtype="float32",count=1,nodata=NODATA,compress="deflate",tiled=True)
        run_time=datetime.now(timezone.utc).isoformat()
        for name,array in [("mean",mean),("p05",p05),("p95",p95)]:
            path=output_dir/f"depth_{name}_{event_date}_UNOSAT_A_DERIVED.tif"
            with rasterio.open(path,"w",**profile) as dst:
                dst.write(array,1)
                dst.update_tags(status="DERIVED_ASSUMPTION_NOT_OBSERVED",event_date=event_date,
                    source="labels.v_usable_flood_labels tier A official UNOSAT flood extent",
                    method="per 8-connected raster component: median cleaned-DEM elevation on rasterized flood boundary; depth=max(0, surface-DEM)",
                    uncertainty=f"symmetric deterministic allowance ±{error_m:g} m; DEFAULT_TO_CONFIRM",
                    dem="cleaned Copernicus GLO-30 DSM; buildings and vegetation remain",
                    grid="CMA master grid; EPSG:32644; 30 m",
                    run_time_utc=run_time,version="batch1-depth-v1",source_geometry_count=str(len(geometries)))
                dst.set_band_description(1,f"{name} flood depth, metres; DERIVED assumption-based estimate")
    details.update({"event_date":event_date,"source_features":len(geometries),"rasterized_flood_cells":int(flood.sum()),
                    "rasterized_extent_area_km2":float(flood.sum()*0.0009),
                    "depth_mean_valid_cells":int(np.count_nonzero(mean!=NODATA)),
                    "depth_mean_median_m":float(np.median(mean[mean!=NODATA])) if (mean!=NODATA).any() else None,
                    "outputs":[f"{path.as_posix()}" for path in [output_dir/f"depth_{n}_{event_date}_UNOSAT_A_DERIVED.tif" for n in ["mean","p05","p95"]]],
                    "run_time_utc":run_time})
    return details


def main(error_m: float=4.0, output_dir: Path=OUT, summary_path: Path | None=None) -> None:
    output_dir.mkdir(parents=True,exist_ok=True)
    if summary_path and summary_path.exists():
        raise FileExistsError("Refusing to overwrite depth summary; choose a new --summary path")
    results=[]
    for event in sorted(EVENTS):
        results.append(process_event(event,error_m,output_dir))
    if summary_path:
        summary_path.parent.mkdir(parents=True,exist_ok=True)
        summary_path.write_text(__import__("json").dumps({"status":"DERIVED assumption-based depth outputs; not observed depth","events":results},indent=2)+"\n",encoding="utf-8")
    print(__import__("json").dumps({event["event_date"]:{"rasterized_extent_area_km2":event["rasterized_extent_area_km2"],
          "depth_mean_valid_cells":event["depth_mean_valid_cells"],"components":event["components"],
          "component_water_surface_edge_median_summary":event["component_water_surface_edge_median_summary"],
          "outputs":event["outputs"]} for event in results},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--dem-error-m",type=float,default=4.0,
                        help="symmetric DEM uncertainty allowance in m (default assumption; confirm before operational use)")
    parser.add_argument("--output-dir",type=Path,default=OUT)
    parser.add_argument("--summary",type=Path,default=None)
    args=parser.parse_args()
    main(args.dem_error_m,args.output_dir,args.summary)
