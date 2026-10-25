"""Create Phase 10 apparent risk classes, summaries, preview and MVT tiles."""
from __future__ import annotations

import csv
import json
import math
import shutil
import sqlite3
from pathlib import Path

import numpy as np
import psycopg
import rasterio
from rasterio.features import shapes
from rasterio.transform import rowcol
from rasterio.warp import transform_bounds
from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
GRID = ROOT / "data/processed/grid/cma_mask.tif"
BLOCKS = ROOT / "data/processed/alignment/spatial_blocks.tif"
POPULATION = ROOT / "data/features/population/worldpop_2021_sum_resampled_30m.tif"
P9B = ROOT / "data/features/predictions/phase9b_v2"
P9C = ROOT / "data/features/predictions/phase9c"
OUT = ROOT / "data/features/predictions/phase10_cr003_v3"
TILES = ROOT / "data/processed/tiles/phase10_cr003_v3"
REPORT = ROOT / "docs/PHASE10_RISK_MAP_CR003_V3.md"
SUMMARY = ROOT / "docs/PHASE10_RISK_MAP_CR003_V3.json"
POINT_METRICS = ROOT / "docs/PHASE9C_METRICS.json"
NODATA_CLASS = 255
CLASS_LABELS = {1: "low", 2: "moderate", 3: "high", 4: "very_high", 255: "not_assessed"}
THRESHOLDS = (0.05, 0.10, 0.25)


def classify(probability: np.ndarray, nodata: float) -> np.ndarray:
    valid = np.isfinite(probability) & (probability != nodata)
    result = np.full(probability.shape, NODATA_CLASS, dtype=np.uint8)
    result[valid] = np.digitize(probability[valid], THRESHOLDS, right=False) + 1
    return result


def read_dotenv(path: Path) -> dict[str, str]:
    """Parse only needed key-value lines; never emit values or exceptions with secrets."""
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def db_connect():
    cfg = read_dotenv(ROOT / ".env")
    return psycopg.connect(
        host=cfg.get("POSTGRES_HOST", "localhost"),
        port=int(cfg.get("POSTGRES_PORT", "5432")),
        dbname=cfg["POSTGRES_DB"], user=cfg["POSTGRES_USER"], password=cfg["POSTGRES_PASSWORD"],
        connect_timeout=5, options="-c default_transaction_read_only=on",
    )


def save_class(path: Path, values: np.ndarray, profile: dict, product: str) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    p = profile.copy()
    p.update(dtype="uint8", count=1, nodata=NODATA_CLASS, compress="deflate", tiled=True)
    with rasterio.open(path, "w", **p) as dst:
        dst.write(values, 1)
        dst.set_band_description(1, f"Apparent susceptibility class: 1 low, 2 moderate, 3 high, 4 very high; {product}")
        dst.update_tags(status="APPARENT_SINGLE_EVENT_NOT_FORECAST", probability_cut_points="0.05,0.10,0.25",
                        class_labels=json.dumps(CLASS_LABELS), source_product=product,
                        threshold_note="Fixed probability cut points; classes are not validated operational warnings")


def copy_inputs() -> dict[str, str]:
    copies = {
        "phase9b_probability_mean_apparent.tif": P9B / "probability_mean_apparent.tif",
        "phase9b_interval_lower90_apparent.tif": P9B / "interval_lower90_apparent.tif",
        "phase9b_interval_upper90_apparent.tif": P9B / "interval_upper90_apparent.tif",
        "phase9c_radar_probability_mean_apparent.tif": P9C / "radar_probability_mean_apparent.tif",
        "phase9c_radar_mondrian_p05_apparent.tif": P9C / "radar_mondrian_p05_apparent.tif",
        "phase9c_radar_mondrian_p95_apparent.tif": P9C / "radar_mondrian_p95_apparent.tif",
        "phase9c_urban_confidence.tif": P9C / "urban_confidence.tif",
        "phase9c_observability_mask.tif": P9C / "radar_observability_mask.tif",
        "phase9c_physical_complement_not_probability.tif": P9C / "physical_susceptibility_outside_radar.tif",
    }
    for name, source in copies.items():
        dest = OUT / name
        if dest.exists():
            raise FileExistsError(f"refusing to overwrite {dest}")
        if not source.is_file():
            raise FileNotFoundError(f"required source layer missing: {source.relative_to(ROOT)}")
        shutil.copy2(source, dest)
    return {k: v.relative_to(ROOT).as_posix() for k, v in copies.items()}


def collect_db_features() -> tuple[list[tuple[float, float, str]], list[tuple[float, float, float]]]:
    facilities: list[tuple[float, float, str]] = []
    roads: list[tuple[float, float, float]] = []
    with db_connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT ST_X(geom), ST_Y(geom), category FROM twinguard.facilities WHERE in_cma IS TRUE AND geom IS NOT NULL")
        while rows := cur.fetchmany(5000):
            facilities.extend((float(x), float(y), str(category or "unknown")) for x, y, category in rows)
        # Representative point assignment is an explicit approximation: each edge's full length
        # is allocated to its point-on-surface cell, rather than split at class/block boundaries.
        cur.execute("SELECT ST_X(ST_PointOnSurface(geom)), ST_Y(ST_PointOnSurface(geom)), length_m FROM twinguard.road_edges WHERE in_cma IS TRUE AND geom IS NOT NULL AND length_m IS NOT NULL")
        while rows := cur.fetchmany(10000):
            roads.extend((float(x), float(y), float(length)) for x, y, length in rows)
    return facilities, roads


def pixel_for_xy(transform, x: float, y: float, height: int, width: int) -> tuple[int, int] | None:
    r, c = rowcol(transform, x, y)
    if 0 <= r < height and 0 <= c < width:
        return int(r), int(c)
    return None


def zonal_table(product: str, classes: np.ndarray, blocks: np.ndarray, population: np.ndarray,
                pop_nodata: float, facilities: list, roads: list, transform) -> list[dict]:
    h, w = classes.shape
    # Include the whole CMA so missing model coverage and population NoData remain explicit.
    valid = blocks != 0
    keys = set(zip(classes[valid].astype(int).tolist(), blocks[valid].astype(int).tolist()))
    stats: dict[tuple[int, int], dict] = {}
    for risk_class, block_id in keys:
        mask = valid & (classes == risk_class) & (blocks == block_id)
        pop_missing = ~np.isfinite(population[mask]) | (population[mask] == pop_nodata)
        pop_values = population[mask][~pop_missing]
        stats[(risk_class, block_id)] = {
            "product": product, "risk_class": risk_class, "risk_label": CLASS_LABELS[risk_class],
            "block_id": block_id, "cell_count": int(mask.sum()), "area_km2": float(mask.sum() * 0.0009),
            "population_valid_sum_model_estimate": float(pop_values.sum(dtype=np.float64)),
            "population_nodata_cells": int(pop_missing.sum()), "facility_count": 0,
            "road_length_midpoint_allocated_m": 0.0,
        }
    for x, y, _category in facilities:
        rc = pixel_for_xy(transform, x, y, h, w)
        if rc:
            r, c = rc
            key = (int(classes[r, c]), int(blocks[r, c]))
            if key in stats:
                stats[key]["facility_count"] += 1
    for x, y, length in roads:
        rc = pixel_for_xy(transform, x, y, h, w)
        if rc:
            r, c = rc
            key = (int(classes[r, c]), int(blocks[r, c]))
            if key in stats:
                stats[key]["road_length_midpoint_allocated_m"] += length
    return [stats[k] for k in sorted(stats)]


def downsample_mode(values: np.ndarray, factor: int = 4) -> tuple[np.ndarray, rasterio.Affine]:
    h = values.shape[0] // factor * factor
    w = values.shape[1] // factor * factor
    crop = values[:h, :w].reshape(h // factor, factor, w // factor, factor)
    out = np.full((h // factor, w // factor), NODATA_CLASS, dtype=np.uint8)
    for r in range(out.shape[0]):
        for c in range(out.shape[1]):
            cell = crop[r, :, c, :].ravel()
            valid = cell[cell != NODATA_CLASS]
            if valid.size >= (factor * factor // 2):
                counts = np.bincount(valid, minlength=5)[1:5]
                out[r, c] = np.argmax(counts) + 1
    return out, rasterio.Affine(120, 0, 390000, 0, -120, 1471620)


def mvt_geometries(class_rasters: dict[str, np.ndarray], profile: dict) -> list[tuple[str, int, str, bytes]]:
    from rasterio.features import shapes as raster_shapes
    from shapely.geometry import shape as shapely_shape
    from shapely.ops import unary_union
    result = []
    for product, raster in class_rasters.items():
        small, transform = downsample_mode(raster)
        mask = small != NODATA_CLASS
        by_class: dict[int, list] = {i: [] for i in range(1, 5)}
        for geom_json, value in raster_shapes(small, mask=mask, transform=transform, connectivity=8):
            by_class[int(value)].append(shapely_shape(geom_json))
        for risk_class, pieces in by_class.items():
            if pieces:
                geom = unary_union(pieces).simplify(120, preserve_topology=True)
                if not geom.is_empty:
                    result.append((product, risk_class, CLASS_LABELS[risk_class], geom.wkb))
    return result


def tile_xy(lon: float, lat: float, z: int) -> tuple[int, int]:
    n = 2**z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return max(0, min(n - 1, x)), max(0, min(n - 1, y))


def build_mbtiles(geoms: list[tuple[str, int, str, bytes]], grid_bounds: tuple[float, float, float, float]) -> dict:
    tile_path = TILES / "phase10_apparent_risk.mbtiles"
    if tile_path.exists():
        raise FileExistsError(f"refusing to overwrite {tile_path}")
    west, south, east, north = transform_bounds("EPSG:32644", "EPSG:4326", *grid_bounds)
    con = sqlite3.connect(tile_path)
    try:
        con.executescript("CREATE TABLE metadata (name TEXT, value TEXT); CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, tile_row INTEGER, tile_data BLOB); CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row);")
        con.executemany("INSERT INTO metadata VALUES (?,?)", [("name", "TwinGuard Phase 10 apparent susceptibility"), ("format", "pbf"), ("type", "overlay"), ("version", "1"), ("description", "Generalized 120 m apparent single-event risk classes; not forecast or validated")])
        tiles_written = 0
        with db_connect() as conn, conn.cursor() as cur:
            for z in range(8, 13):
                x0, y1 = tile_xy(west, south, z)
                x1, y0 = tile_xy(east, north, z)
                for x in range(min(x0, x1), max(x0, x1) + 1):
                    for y in range(min(y0, y1), max(y0, y1) + 1):
                        values = ",".join(["(%s::text,%s::int,%s::text,%s::bytea)"] * len(geoms))
                        sql = f"WITH src(product,risk_class,risk_label,wkb) AS (VALUES {values}), tile AS (SELECT ST_TileEnvelope(%s,%s,%s) AS bounds), features AS (SELECT product,risk_class,risk_label,ST_AsMVTGeom(ST_Transform(ST_GeomFromWKB(wkb,32644),3857),tile.bounds,4096,64,true) AS geom FROM src CROSS JOIN tile WHERE ST_Intersects(ST_Transform(ST_GeomFromWKB(wkb,32644),3857),tile.bounds)) SELECT ST_AsMVT(features,'risk',4096,'geom') FROM features WHERE geom IS NOT NULL"
                        params = [v for row in geoms for v in row] + [z, x, y]
                        cur.execute(sql, params)
                        blob = cur.fetchone()[0]
                        if blob:
                            tms_y = (2**z - 1) - y
                            con.execute("INSERT INTO tiles VALUES (?,?,?,?)", (z, x, tms_y, blob))
                            tiles_written += 1
            con.commit()
        return {"path": tile_path.relative_to(ROOT).as_posix(), "tiles_written": tiles_written,
                "zoom_range": [8, 12], "generalization_m": 120, "features": len(geoms)}
    finally:
        con.close()


def make_preview(classes_b: np.ndarray, classes_c: np.ndarray, physical: np.ndarray) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap, BoundaryNorm
    from matplotlib.patches import Patch
    fig, axes = plt.subplots(1, 3, figsize=(15, 8), constrained_layout=True)
    colors = ListedColormap(["#d8efb2", "#fee08b", "#fdae61", "#d7191c"])
    norm = BoundaryNorm([0.5, 1.5, 2.5, 3.5, 4.5], colors.N)
    for ax, arr, title in ((axes[0], classes_b, "Phase 9B v2 apparent probability"),
                           (axes[1], classes_c, "Phase 9C radar-observable only")):
        show = np.ma.masked_equal(arr, NODATA_CLASS)
        ax.imshow(show, cmap=colors, norm=norm, interpolation="nearest")
        ax.set_title(title); ax.axis("off")
    physical_show = np.ma.masked_where((physical == -9999) | ~np.isfinite(physical), physical)
    axes[2].imshow(physical_show, cmap="viridis", interpolation="nearest")
    axes[2].set_title("Physical complement outside radar mask\nnot a fitted probability"); axes[2].axis("off")
    handles = [Patch(color=colors(i - 1), label=f"{i}: {CLASS_LABELS[i]}") for i in range(1, 5)]
    fig.legend(handles=handles, loc="lower center", ncol=4, title="Fixed probability classes: <0.05, 0.05–<0.10, 0.10–<0.25, ≥0.25")
    path = ROOT / "docs/figures/phase10_risk_map_cr003_v3.png"
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run() -> dict:
    if OUT.exists() or TILES.exists() or REPORT.exists() or SUMMARY.exists() or (ROOT / "docs/figures/phase10_risk_map_cr003_v3.png").exists():
        raise FileExistsError("Phase 10 output path already exists; refusing overwrite")
    OUT.mkdir(parents=True)
    TILES.mkdir(parents=True)
    (ROOT / "docs/figures").mkdir(parents=True, exist_ok=True)
    with rasterio.open(GRID) as gd:
        profile = gd.profile.copy(); transform = gd.transform; cma = gd.read(1) == 1
        bounds = gd.bounds
    products = {}
    arrays = {}
    for name, path in (("phase9b_v2", P9B / "probability_mean_apparent.tif"),
                       ("phase9c_radar", P9C / "radar_probability_mean_apparent.tif")):
        with rasterio.open(path) as ds:
            if ds.crs != rasterio.crs.CRS.from_epsg(32644) or ds.transform != transform or (ds.width, ds.height) != (profile["width"], profile["height"]):
                raise ValueError(f"probability grid mismatch: {path.relative_to(ROOT)}")
            prob = ds.read(1)
            classes = classify(prob, ds.nodata)
        classes[~cma] = NODATA_CLASS
        out_path = OUT / f"risk_class_{name}_apparent.tif"
        save_class(out_path, classes, profile, name)
        arrays[name] = classes
        products[name] = {"probability_source": path.relative_to(ROOT).as_posix(), "class_raster": out_path.relative_to(ROOT).as_posix(),
                          "valid_cells": int((classes != NODATA_CLASS).sum()), "class_cut_points": list(THRESHOLDS)}
    copied = copy_inputs()
    with rasterio.open(POPULATION) as ds:
        if ds.crs != rasterio.crs.CRS.from_epsg(32644) or ds.transform != transform:
            raise ValueError("population raster does not match master grid")
        population = ds.read(1); pop_nodata = ds.nodata
    with rasterio.open(BLOCKS) as ds:
        if ds.crs != rasterio.crs.CRS.from_epsg(32644) or ds.transform != transform:
            raise ValueError("spatial block raster does not match master grid")
        blocks = ds.read(1)
    facilities, roads = collect_db_features()
    rows = []
    for product, classes in arrays.items():
        rows.extend(zonal_table(product, classes, blocks, population, pop_nodata, facilities, roads, transform))
    csv_path = OUT / "zonal_stats_by_risk_class_and_3km_block.csv"
    if csv_path.exists():
        raise FileExistsError(f"refusing to overwrite {csv_path}")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    with rasterio.open(OUT / "phase9c_physical_complement_not_probability.tif") as ds:
        physical = ds.read(1)
    make_preview(arrays["phase9b_v2"], arrays["phase9c_radar"], physical)
    geoms = mvt_geometries(arrays, profile)
    tile_info = build_mbtiles(geoms, (bounds.left, bounds.bottom, bounds.right, bounds.top))
    point = json.loads(POINT_METRICS.read_text(encoding="utf-8"))["independent_point_validation"]
    summary = {"status": "PILOT; single-event apparent susceptibility; not forecast; out-of-event validation pending digitised labels",
               "grid": {"crs": "EPSG:32644", "pixel_m": 30, "shape": list(cma.shape), "cma_cells": int(cma.sum())},
               "fixed_probability_cut_points": {"low": "<0.05", "moderate": "0.05 to <0.10", "high": "0.10 to <0.25", "very_high": ">=0.25"},
               "products": products, "input_copies": copied,
               "not_assessed_cells_by_product_inside_cma": {k: int(((v == NODATA_CLASS) & cma).sum()) for k, v in arrays.items()},
               "population_nodata_cells_inside_cma": int(((population == pop_nodata) & cma).sum()),
               "zonal_stats_csv": csv_path.relative_to(ROOT).as_posix(), "zonal_rows": len(rows),
               "facilities_in_cma_queried": len(facilities), "road_edges_in_cma_queried": len(roads),
               "road_length_method": "each complete edge length assigned to ST_PointOnSurface raster cell; approximate, not clipped at risk/block boundaries",
               "population_nodata": "counted separately; valid-only population sum is an alpha WorldPop model estimate, not a census count",
               "vector_tiles": tile_info,
               "opencity_point_cross_check": {"source": "existing Phase 9C independent point validation; points are approximate and undated", "scored": point["radar_assessed_points"] + point["physical_only_support_points"], "total": point["source_point_count"], "top_percentile_hits": {k: {"hit_share": v["observed_share"], "ci_95": v["observed_ci_95"], "n": v["n"]} for k, v in point["top_percentile_hits"].items()}, "warning": "rank statistics use the Phase 9C composite ordinal rank surface; physical and radar domains are not probability-comparable"},
               "zonal_class_totals": []}
    for product in arrays:
        for cls, label_name in CLASS_LABELS.items():
            product_rows = [r for r in rows if r["product"] == product and r["risk_class"] == cls]
            summary["zonal_class_totals"].append({"product": product, "risk_class": label_name,
                "cell_count": sum(r["cell_count"] for r in product_rows),
                "population_valid_sum_model_estimate": sum(r["population_valid_sum_model_estimate"] for r in product_rows),
                "population_nodata_cells": sum(r["population_nodata_cells"] for r in product_rows),
                "facility_count": sum(r["facility_count"] for r in product_rows),
                "road_length_midpoint_allocated_m": sum(r["road_length_midpoint_allocated_m"] for r in product_rows)})
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report = ["# Phase 10 apparent risk map", "", "> PILOT: single-event apparent susceptibility only. It is not a forecast, and it is not validated for future events.", "",
              "## Class maps and uncertainty", "",
              "Probability classes use fixed cut-points: low <0.05; moderate 0.05–<0.10; high 0.10–<0.25; very high ≥0.25. These are descriptive probability bins, not emergency thresholds. The Phase 9B v2 apparent map covers its saved prediction domain. The Phase 9C risk map uses radar-observable cells only; cells outside its observation mask are not assessed from radar labels. A physical complement is retained as a separate ordinal layer and is not merged with radar probabilities.", "",
              "Phase 9B's apparent lower/upper interval rasters are copied unchanged; its nominal 90% band covered 85.8% in blocked within-event validation and therefore under-covered. Phase 9C's spatial Mondrian p05/p95 bounds and urban-confidence/observability layers are copied unchanged; Phase 9C reported 93.4% outer-fold coverage for its nominal 90% band. Neither is independent-event coverage. See the model card and Phase 9C report for limits.", "",
              "![Phase 10 apparent risk map](figures/phase10_risk_map_cr003_v3.png)", "",
              "## OpenCity point cross-check", "",
              "The 945 source points are approximate and have unclear dates. Existing Phase 9C checks scored 111 points (99 radar-assessed and 12 physical-only). On its composite ordinal ranking, observed hits were 0/111 in the top 1%, 0/111 in the top 5%, 1/111 (0.90%) in the top 10%, and 3/111 (2.70%) in the top 20%. These were below the land-cover-matched random-cell shares reported by Phase 9C (0.29%, 1.52%, 3.17%, 6.67%). This is a spatial cross-check, not date-matched validation. Radar and physical-only ranks are separate domains, not comparable probabilities.", "",
              "## Zonal summaries", "",
              f"The machine-readable class totals and class-by-3 km block rows are in `{csv_path.relative_to(ROOT).as_posix()}` and `{SUMMARY.relative_to(ROOT).as_posix()}`. Population NoData cells are counted separately; population sums include only valid values and remain model estimates. Facility points are assigned by their containing master-grid cell. Road length is an approximation: each CMA edge's full stored length is assigned to its PostGIS point-on-surface cell, rather than split across risk/block boundaries. Do not interpret it as exact road length within each class.", "",
              "A generalized MVT set is in `data/processed/tiles/phase10_cr003_v3/phase10_apparent_risk.mbtiles` at zooms 8–12. Tile geometries use a 120 m majority-class generalization; the 30 m GeoTIFFs remain the analysis layers. Out-of-event validation is pending digitised official labels.", "",
              "## Files", "",
              "The authoritative outputs are under `data/features/predictions/phase10_cr003_v3/`. Earlier same-session draft products in the unversioned `phase10/` and `phase10_cr003_v2/` folders are superseded; use the v3 report and tiles. Class 255 in the zonal table means not assessed; those cells are excluded from the MVT risk classes, not re-labelled low risk. The complete source list, cell counts, facility/road query counts, point metrics and tile metadata are in the JSON summary. No source raster or raw file was modified.", ""]
    REPORT.write_text("\n".join(report), encoding="utf-8")
    return summary


def main() -> None:
    summary = run()
    print(json.dumps({"status": summary["status"], "products": summary["products"], "zonal_rows": summary["zonal_rows"], "tiles": summary["vector_tiles"]["tiles_written"]}, indent=2))


if __name__ == "__main__":
    main()
