#!/usr/bin/env python
"""Create a file-level lineage catalogue for derived Phase 3/4 outputs."""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/DATA_LINEAGE.md"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def provenance(path: Path) -> tuple[str, str]:
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith("data/processed/sar_work/hand_d8_100cells_"):
        return ("data/processed/terrain_cleaned/cleaned_elevation_m.tif; data/processed/terrain_cleaned/flow_direction_d8.tif; data/processed/terrain_cleaned/flow_accumulation_cells_d8.tif",
                "pipelines/phase8/flood_rule_v2.py")
    if rel.startswith("data/processed/sar_work/"):
        return ("data/raw/satellite/hpy3_rtc/*.zip; data/raw/boundary/chennai_cma_boundary.geojson; data/processed/grid/cma_mask.tif; data/processed/labels_inspection/2015-09-01_EXPLORATORY_NOT_FINAL.tif; data/processed/labels_inspection/2015-10-14_EXPLORATORY_NOT_FINAL.tif; data/features/static/cell_table.parquet",
                "pipelines/phase8/sar_labels.py")
    if rel.startswith("data/features/labels/") and "rule_v2" in rel:
        return ("data/processed/sar_work/rtc_aligned/*_gamma0_power_lee5.tif; data/processed/terrain_cleaned/slope_deg_edge_safe.tif; data/processed/terrain_cleaned/cleaned_elevation_m.tif; data/features/landcover/worldcover_2021_class.tif; docs/T2_PHYSICS_THRESHOLDS.json; labels.v_usable_flood_labels",
                "pipelines/phase8/flood_rule_v2.py; pipelines/phase8/evaluate_rule_v2.py")
    if rel.startswith("data/features/labels/"):
        return ("data/raw/satellite/hpy3_rtc/*.zip; data/raw/boundary/chennai_cma_boundary.geojson; data/processed/grid/cma_mask.tif; data/processed/labels_inspection/*2015*.tif; data/features/static/cell_table.parquet",
                "pipelines/phase8/sar_labels.py; pipelines/phase8/load_labels.py")
    if rel.startswith("data/features/depth/"):
        return ("labels.v_usable_flood_labels (tier A UNOSAT events); data/processed/grid/cma_mask.tif; data/processed/terrain_cleaned/cleaned_elevation_m.tif",
                "pipelines/phase8/depth_fields.py")
    if rel.startswith("data/processed/terrain_cleaned/"):
        return ("data/features/terrain/elevation_m.tif; data/features/landcover/worldcover_2021_class.tif; data/features/hydrology/chennai_waterways.gpkg; data/raw/boundary/chennai_cma_boundary.geojson",
                "pipelines/phase4/terrain_conditioning.py")
    if rel.startswith("data/processed/routing/"):
        return ("data/features/osm/chennai_osm_features.gpkg; data/processed/terrain_cleaned/cleaned_elevation_m.tif; data/raw/boundary/chennai_cma_boundary.geojson",
                "pipelines/phase4/routing_profile.py")
    if rel.startswith("data/processed/alignment/"):
        return ("data/processed/grid/cma_mask.tif; data/processed/grid/grid_definition.json; raster/vector layers listed in registry",
                "pipelines/phase4/spatial_alignment.py; pipelines/phase4/validation_blocks.py")
    if rel.startswith("data/processed/grid/"):
        return ("data/raw/boundary/chennai_cma_boundary.geojson", "pipelines/phase3/phase3_core.py")
    if rel.startswith("data/processed/labels_inspection/"):
        return ("data/raw/historical_floods/2015/2015-12-04/FL20151123IND_shp.zip; data/raw/boundary/chennai_cma_boundary.geojson",
                "pipelines/phase3/flood_labels_inspection.py")
    if rel.startswith("data/processed/exposure/"):
        return ("data/features/population/worldpop_2021_sum_resampled_30m.tif; data/features/osm/chennai_osm_features.gpkg; data/processed/grid/cma_mask.tif",
                "pipelines/phase3/population_exposure.py")
    if rel.startswith("data/features/events/"):
        return ("data/features/weather/era5_event_hourly_features.csv; data/features/weather/daily_era5_nasa_power_comparison.csv; data/features/reservoirs/kaggle_daily_storage_features.csv; data/features/reservoirs/opencity_monthly_storage_tidy.csv",
                "pipelines/phase4/qc_check.py; pipelines/phase4/time_alignment.py (Parquet outputs pending)")
    if rel.startswith("data/features/predictions/"):
        return ("data/features/static/cell_table.parquet; data/processed/alignment/spatial_blocks.tif; data/processed/grid/cma_mask.tif; data/processed/labels_inspection/2015-09-01_EXPLORATORY_NOT_FINAL.tif; data/processed/labels_inspection/2015-10-14_EXPLORATORY_NOT_FINAL.tif; data/processed/labels_inspection/2015-11-12_EXPLORATORY_NOT_FINAL.tif; data/processed/labels_inspection/2015-11-24_EXPLORATORY_NOT_FINAL.tif",
                "pipelines/phase9/pilot.py")
    if rel.startswith("data/features/terrain/"):
        return ("data/raw/dem/Copernicus DSM tiles; data/raw/boundary/chennai_cma_boundary.geojson", "pipelines/phase3/phase3_core.py")
    if rel.startswith("data/features/landcover/"):
        return ("data/raw/landcover/ESA_WorldCover_10m_2021_v200_N12E078_Map.tif; data/processed/grid/grid_definition.json", "pipelines/phase3/phase3_core.py")
    if rel.startswith("data/features/population/"):
        return ("data/raw/population/ind_pop_2021_CN_100m_R2025A_v1.tif; data/processed/grid/grid_definition.json", "pipelines/phase3/phase3_core.py")
    if rel.startswith("data/features/weather/"):
        return ("data/raw/weather/ Open-Meteo ERA5 and NASA POWER JSON; data/raw/weather/imerg/*.nc4", "pipelines/phase3/weather_reservoirs.py; pipelines/phase4/ingest_imerg.py")
    if rel.startswith("data/features/reservoirs/"):
        return ("data/raw/reservoirs/ Kaggle archive and six OpenCity lake CSVs; existing weather features", "pipelines/phase3/weather_reservoirs.py")
    if rel.startswith("data/features/osm/") or rel.startswith("data/features/roads/"):
        return ("data/raw/roads/southern-zone-latest.osm.pbf; data/raw/boundary/chennai_cma_boundary.geojson", "pipelines/phase3/osm_extract_graph.py; pipelines/phase3/split_osm_layers.py")
    if rel.startswith("data/features/buildings/"):
        return ("data/raw/roads/southern-zone-latest.osm.pbf; data/raw/boundary/chennai_cma_boundary.geojson", "pipelines/phase3/osm_extract_graph.py; pipelines/phase3/split_osm_layers.py")
    if rel.startswith("data/features/facilities/") or rel.startswith("data/features/hydrology/"):
        return ("data/raw/roads/southern-zone-latest.osm.pbf; data/raw/boundary/chennai_cma_boundary.geojson", "pipelines/phase3/osm_extract_graph.py; pipelines/phase3/split_osm_layers.py")
    return ("not recorded in repository metadata", "not recorded in repository metadata")


def main() -> int:
    files = []
    for root in (ROOT / "data/processed", ROOT / "data/features"):
        if root.exists():
            files.extend(p for p in root.rglob("*") if p.is_file())
    lines = ["# Derived data lineage", "",
             "File-level lineage for every current file under `data/processed` and `data/features`. Rows are DERIVED outputs. Creation date is the current filesystem modification time in Asia/Kolkata; input/script attribution is based on the saved pipeline/report conventions and is explicitly marked unrecorded where the repo does not retain exact run metadata. SHA-256 is calculated from the current output bytes.", "",
             f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}", "",
             "| Output file | Input files | Script | Creation date/time | Size (bytes) | SHA-256 |", "|---|---|---|---|---:|---|"]
    for path in sorted(files):
        ins, script = provenance(path)
        stat = path.stat()
        created = datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds")
        lines.append(f"| `{path.relative_to(ROOT).as_posix()}` | {ins} | `{script}` | {created} | {stat.st_size} | `{digest(path)}` |")
    # This report is a generated inventory and must be refreshable as new
    # derived files are added. Write to a sibling temporary, then replace the
    # prior generated report atomically; source/data outputs are never touched.
    temp = DOC.with_suffix(".md.tmp")
    temp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temp.replace(DOC)
    print(f"LINEAGE_ROWS={len(files)}; REPORT={DOC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
