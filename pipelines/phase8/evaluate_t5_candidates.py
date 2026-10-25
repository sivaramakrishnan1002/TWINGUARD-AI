"""Summarize fixed-rule Batch 1 candidate rasters and coarse observations."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import rowcol
from rasterio.warp import Resampling, reproject, transform
from pipelines.phase8.physics_thresholds import align_exact

ROOT = Path(__file__).resolve().parents[2]
FEATURES = ROOT / "data/features"
PROCESSED = ROOT / "data/processed"
RAW = ROOT / "data/raw"
OUT = ROOT / "docs/T5_APPLY_METRICS_v2.json"
RUNS = {
    "2015-12-06": {
        "run_id": "20261025_T5_20151206",
        "reference_scenes": ["2015-10-19", "2015-11-24"],
        "hand": "hand_d8_100cells_20261025_T5_20151206_DEFAULT.tif",
    },
    "2021-11-16": {
        "run_id": "20261025_T5_20211116",
        "reference_scenes": ["2021-10-23", "2021-11-04"],
        "hand": "hand_d8_100cells_20261025_T5_20211116_DEFAULT.tif",
    },
}


def stats(values: np.ndarray) -> dict:
    values = values[np.isfinite(values)]
    if not values.size:
        return {"count": 0, "min": None, "p05": None, "median": None, "mean": None, "p95": None, "max": None}
    return {"count": int(values.size), "min": float(values.min()),
            "p05": float(np.percentile(values, 5)), "median": float(np.median(values)),
            "mean": float(values.mean()), "p95": float(np.percentile(values, 95)),
            "max": float(values.max())}


def aligned_band(path: Path, profile: dict) -> tuple[np.ndarray, float | int | None]:
    with rasterio.open(path) as ds:
        arr = align_exact(ds.read(1), ds.transform, ds.crs, profile["transform"], profile["crs"],
                          (profile["height"], profile["width"]),
                          fill_value=ds.nodata if ds.nodata is not None else 0)
        return arr, ds.nodata


def parse_kml_point_coords(path: Path) -> list[tuple[float, float]]:
    ns = {"k": "http://www.opengis.net/kml/2.2"}
    root = ET.parse(path).getroot()
    coords=[]
    for placemark in root.findall(".//k:Placemark", ns):
        if placemark.find(".//k:Point", ns) is None:
            continue
        node = placemark.find(".//k:Point/k:coordinates", ns)
        if node is None or not node.text:
            continue
        for token in node.text.split():
            bits=token.split(",")
            if len(bits)>=2:
                coords.append((float(bits[0]),float(bits[1])))
    return coords


def candidate_point_check(candidate: np.ndarray, transform_affine, crs, cma: np.ndarray) -> dict:
    paths=[RAW/"historical_floods/2015/opencity_flood_points/814ca028-4c84-4bd0-aa67-6dbaeb9b6ba5.kml",
           RAW/"historical_floods/2015/opencity_flood_points/93d2905a-a580-482d-96b0-4d9ccf5273ef.kml"]
    allcoords=[]; perfile={}
    for path in paths:
        points=parse_kml_point_coords(path)
        perfile[path.name]=len(points)
        allcoords.extend(points)
    xs,ys=transform("EPSG:4326",crs,[p[0] for p in allcoords],[p[1] for p in allcoords])
    inside=hits=0
    for x,y in zip(xs,ys):
        row,col=rowcol(transform_affine,x,y)
        if 0<=row<candidate.shape[0] and 0<=col<candidate.shape[1] and cma[row,col]:
            inside+=1
            hits+=int(candidate[row,col]==1)
    return {"source_files":perfile,"total_point_features":len(allcoords),"points_inside_cma":inside,
            "points_in_candidate":hits,"share_inside_points_in_candidate":hits/inside if inside else None,
            "date_status":"source does not provide a reliable event date; spatial overlap only"}


def gfd_check(candidate: np.ndarray, cma: np.ndarray, profile: dict) -> dict:
    archive=RAW/"historical_floods/2015/global_flood_database/DFO_4309_From_20151110_to_20151204.zip"
    with ZipFile(archive) as zf:
        member="DFO_4309_From_20151110_to_20151204.tif"
        with MemoryFile(zf.read(member)) as mem:
            with mem.open() as src:
                srcdata=src.read(1)
                pred_coarse=np.full(srcdata.shape,255,dtype=np.uint8)
                cma_coarse=np.zeros(srcdata.shape,dtype=np.uint8)
                reproject(candidate.astype(np.uint8),pred_coarse,src_transform=profile["transform"],src_crs=profile["crs"],
                          src_nodata=255,dst_transform=src.transform,dst_crs=src.crs,dst_nodata=255,
                          resampling=Resampling.max)
                reproject(cma.astype(np.uint8),cma_coarse,src_transform=profile["transform"],src_crs=profile["crs"],
                          src_nodata=0,dst_transform=src.transform,dst_crs=src.crs,dst_nodata=0,
                          resampling=Resampling.nearest)
                valid=(cma_coarse==1)&(src.dataset_mask()>0)
                gfd=(srcdata==1)&valid
                pred=(pred_coarse==1)&valid
                inter=int((gfd&pred).sum()); union=int((gfd|pred).sum())
                return {"archive":str(archive.relative_to(ROOT)).replace("\\","/"),"member":member,
                        "native_crs":src.crs.to_string(),"native_shape":[src.height,src.width],
                        "comparison_grid":"GFD native grid; candidate resampled with maximum (any source flood pixel represented), CMA with nearest",
                        "valid_comparison_cells":int(valid.sum()),"gfd_flood_cells":int(gfd.sum()),
                        "candidate_coarse_cells_touched":int(pred.sum()),"intersection_cells":inter,
                        "union_cells":union,"coarse_iou":inter/union if union else None,
                        "warning":"GFD event 4309 covers 10 Nov–4 Dec 2015; this candidate is 6 Dec, so dates do not match."}


def main() -> None:
    if OUT.exists():
        raise FileExistsError(f"Refusing to overwrite {OUT.name}; archive the old report and choose a new output path")
    reports={}
    for event,info in RUNS.items():
        run=info["run_id"]
        label_path=FEATURES/f"labels/label_{event}_rule_v2_{run}_DERIVED.tif"
        hand_path=PROCESSED/f"sar_work/{info['hand']}"
        with rasterio.open(label_path) as ds:
            labels=ds.read(1); profile=ds.profile.copy(); affine=ds.transform; crs=ds.crs
        cma_arr,_=aligned_band(PROCESSED/"grid/cma_mask.tif",profile); cma=cma_arr==1
        wc,_=aligned_band(FEATURES/"landcover/worldcover_2021_class.tif",profile)
        dem,dem_nd=aligned_band(PROCESSED/"terrain_cleaned/cleaned_elevation_m.tif",profile); dem=dem.astype(np.float32)
        hand,hand_nd=aligned_band(hand_path,profile); hand=hand.astype(np.float32)
        flooded=cma & (labels==1)
        eligible=cma & (labels!=255)
        dem_valid=cma & np.isfinite(dem) & ((dem!=dem_nd) if dem_nd is not None else True)
        hand_valid=cma & np.isfinite(hand) & ((hand!=hand_nd) if hand_nd is not None else True)
        classes={10:"tree",20:"shrub",30:"grass",40:"cropland",50:"built_up",60:"bare",70:"snow_ice",80:"water",90:"wetland",95:"mangrove",100:"moss_lichen"}
        lc={}
        for code,name in classes.items():
            cm=cma & (wc==code); em=eligible & (wc==code); fm=flooded & (wc==code)
            if cm.any():
                lc[name]={"class_cells_in_cma":int(cm.sum()),"eligible_cells":int(em.sum()),
                          "predicted_flood_cells":int(fm.sum()),"eligible_fraction_of_class":float(em.sum()/cm.sum()),
                          "predicted_flood_fraction_of_eligible_class":float(fm.sum()/em.sum()) if em.any() else None,
                          "predicted_flood_fraction_of_all_class_cells":float(fm.sum()/cm.sum())}
        reports[event]={"status":"DERIVED fixed-rule candidate; not accepted and not a ground-truth label",
                        "run_id":run,"reference_scenes":info["reference_scenes"],"candidate_file":str(label_path.relative_to(ROOT)).replace("\\","/"),
                        "cma_cells":int(cma.sum()),"eligible_cells":int(eligible.sum()),"flood_cells":int(flooded.sum()),
                        "candidate_area_km2":float(flooded.sum()*0.0009),"eligible_fraction_cma":float(eligible.sum()/cma.sum()),
                        "landcover_fractions":lc,
                        "elevation_m":{"all_valid_cma":stats(dem[dem_valid]),"predicted_flood":stats(dem[flooded&dem_valid])},
                        "hand_m":{"all_valid_cma":stats(hand[hand_valid]),"predicted_flood":stats(hand[flooded&hand_valid]),
                                  "valid_fraction_cma":float(hand_valid.sum()/cma.sum())},
                        "limitations":["HAND validity is only about 1.91% of CMA, so the rule is strongly coverage-limited.",
                                       "WorldCover 2021 is used for both historical events and may differ from event-date land cover.",
                                       "No official vector reference exists for this event/date; no preregistered B/C score can be assigned."]}
        profile_for_gfd=profile.copy()
        if event=="2015-12-06":
            reports[event]["global_flood_database_4309"]=gfd_check(labels,cma,profile_for_gfd)
            reports[event]["opencity_observed_point_overlap"]=candidate_point_check(labels,affine,crs,cma)
    OUT.write_text(json.dumps(reports,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({event:{"candidate_area_km2":r["candidate_area_km2"],"elevation_m":r["elevation_m"],"hand_m":r["hand_m"],
                              "gfd":r.get("global_flood_database_4309"),"points":r.get("opencity_observed_point_overlap")} for event,r in reports.items()},indent=2))


if __name__=="__main__":
    main()
