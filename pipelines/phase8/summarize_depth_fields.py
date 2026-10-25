"""Read-only QA summary for the generated T6 depth rasters."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize

from pipelines.phase8.depth_fields import DEM, EVENTS, GRID, NODATA, OUT, ROOT, fetch_official_event_geometries


def distribution(array: np.ndarray, nodata: float) -> dict:
    values=array[np.isfinite(array)&(array!=nodata)]
    if not values.size:
        return {"count":0,"min":None,"median":None,"mean":None,"p95":None,"max":None}
    return {"count":int(values.size),"min":float(values.min()),"median":float(np.median(values)),
            "mean":float(values.mean()),"p95":float(np.percentile(values,95)),"max":float(values.max())}


def summarize(output_dir: Path=OUT) -> dict:
    result={"status":"DERIVED assumption-based depth product; not observed depth or a calibrated uncertainty forecast",
            "events":{}}
    with rasterio.open(GRID) as grid, rasterio.open(DEM) as dem_ds:
        cma=grid.read(1)==1; dem=dem_ds.read(1); dem_nd=dem_ds.nodata
        dem_valid=np.isfinite(dem)&((dem!=dem_nd) if dem_nd is not None else True)
        for date in sorted(EVENTS):
            geoms=fetch_official_event_geometries(date)
            extent=rasterize(((geom,1) for geom in geoms),out_shape=(grid.height,grid.width),
                             transform=grid.transform,fill=0,dtype="uint8")==1
            extent &= cma
            item={"source_features":len(geoms),"rasterized_extent_cells":int(extent.sum()),
                  "rasterized_extent_area_km2":float(extent.sum()*0.0009),
                  "extent_cells_without_cleaned_dem":int((extent&~dem_valid).sum()),
                  "extent_cells_with_cleaned_dem":int((extent&dem_valid).sum()),
                  "depth_coverage_fraction_of_rasterized_extent":float((extent&dem_valid).sum()/extent.sum()) if extent.any() else None,
                  "rasters":{}}
            arrays={}
            for name in ("mean","p05","p95"):
                path=output_dir/f"depth_{name}_{date}_UNOSAT_A_DERIVED.tif"
                with rasterio.open(path) as ds:
                    array=ds.read(1); tags=ds.tags(); profile=(ds.crs.to_epsg(),ds.transform,ds.width,ds.height,ds.nodata)
                arrays[name]=array
                item["rasters"][name]={"path":str(path.relative_to(ROOT)).replace("\\","/"),
                    "crs_epsg":profile[0],"pixel_size_m":[abs(profile[1].a),abs(profile[1].e)],
                    "nodata":profile[4],"distribution_m":distribution(array,NODATA),
                    "version":tags.get("version"),"run_time_utc":tags.get("run_time_utc")}
            valid=(arrays["mean"]!=NODATA)&(arrays["p05"]!=NODATA)&(arrays["p95"]!=NODATA)
            item["band_order_violations"]={"p05_above_mean":int((arrays["p05"][valid]>arrays["mean"][valid]).sum()),
                                           "mean_above_p95":int((arrays["mean"][valid]>arrays["p95"][valid]).sum())}
            result["events"][date]=item
    return result


def main(output: Path) -> None:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}; choose a new output path")
    report=summarize()
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({date:{"extent_km2":x["rasterized_extent_area_km2"],
          "depth_valid_cells":x["extent_cells_with_cleaned_dem"],"coverage":x["depth_coverage_fraction_of_rasterized_extent"],
          "depth_mean":x["rasters"]["mean"]["distribution_m"],"band_order_violations":x["band_order_violations"]}
          for date,x in report["events"].items()},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT/"docs/T6_DEPTH_OUTPUTS.json")
    main(parser.parse_args().output)
