"""Idempotent, provenance-aware Stage 5 loaders for assets absent from core GIS import.

Raw inputs are read-only. The cell table is imported through batched PostgreSQL COPY.
The loader refuses to repair, replace, or append to a partially loaded source.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import geopandas as gpd
import pandas as pd
import pyarrow.parquet as pq
from geoalchemy2 import Geometry
from pyproj import Transformer
from shapely import force_2d
from shapely.geometry import Polygon
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from pipelines.stage5.db_common import make_engine

LOADER = "pipelines.stage5.load_stage5_complementary"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _catalog(engine, key: str, path: Path, layer: str, digest: str, count: int,
             crs: str, caveat: str, licence: str = "See source metadata; not independently confirmed.") -> bool:
    """Register source; return True if already loaded exactly, refuse partial/mismatch."""
    with engine.begin() as conn:
        row = conn.execute(text("SELECT source_sha256,loaded_row_count FROM twinguard.dataset_catalog WHERE layer_key=:k"), {"k": key}).first()
        if row:
            if row[0] == digest and int(row[1]) == count:
                return False
            raise RuntimeError(f"Refusing to overwrite or append to catalogued source {key}")
        conn.execute(text("""INSERT INTO twinguard.dataset_catalog
            (layer_key,source_path,source_layer,source_sha256,source_crs,target_srid,
             loaded_row_count,caveat,licence_note)
            VALUES (:k,:p,:l,:h,:c,32644,:n,:v,:lic)"""),
            {"k":key,"p":path.relative_to(ROOT).as_posix(),"l":layer,"h":digest,"c":crs,
             "n":count,"v":caveat,"lic":licence})
    return True


def _load_gdf(engine, table: str, key: str, source: Path, layer: str, frame: gpd.GeoDataFrame,
              digest: str, crs: str, caveat: str, *, geometry_type: str,
              target_columns: list[str], catalogue: bool = True) -> int:
    if frame.empty or frame.crs is None:
        raise RuntimeError(f"Empty or CRS-less source: {key}")
    count = len(frame)
    with engine.connect() as conn:
        exists = conn.execute(text("SELECT to_regclass(:n)"), {"n":f"twinguard.{table}"}).scalar_one()
        if not exists:
            raise RuntimeError(f"Target relation missing: {table}")
        prior = conn.execute(text("SELECT count(*) FROM twinguard."+table+" WHERE source_id=:s"), {"s":key}).scalar_one()
        catalogued = conn.execute(text("SELECT 1 FROM twinguard.dataset_catalog WHERE layer_key=:s"), {"s":key}).first()
        if catalogued:
            registered = conn.execute(text("SELECT source_sha256,loaded_row_count FROM twinguard.dataset_catalog WHERE layer_key=:s"), {"s":key}).first()
            if registered[0] == digest and int(registered[1]) == int(prior) == count:
                return count
            raise RuntimeError(f"Refusing partial or changed source already registered: {key}")
        if prior:
            raise RuntimeError(f"Uncatalogued target rows exist for {key}; refusing duplicate load")
    gdf = frame.to_crs(32644).copy()
    if gdf.geometry.name != "geom":
        gdf = gdf.rename_geometry("geom")
    gdf["source_id"] = key
    gdf["source_sha256"] = digest
    gdf["loader"] = LOADER
    gdf["load_time"] = datetime.now(timezone.utc)
    stage = "stage_" + re.sub("[^a-zA-Z0-9_]", "_", key)[:38]
    try:
        gdf.to_postgis(stage, engine, schema="twinguard", if_exists="fail", index=False,
                       chunksize=1000, dtype={"geom":Geometry(geometry_type=geometry_type,srid=32644)})
        cols = target_columns + ["source_id","source_sha256","loader","load_time"]
        # Caller-specified source frame may include fields not present in target.
        stage_cols = set(gdf.columns)
        select_expr = []
        for col in cols:
            if col in stage_cols:
                if col == "component_id" and col in stage_cols:
                    select_expr.append('NULL::bigint')
                else:
                    select_expr.append('"'+col+'"')
            elif col == "node_id":
                select_expr.append('"source_osmid"::text')
            else:
                raise RuntimeError(f"Loader column mapping missing {col} for {key}")
        with engine.begin() as conn:
            inserted = conn.exec_driver_sql(
                f"INSERT INTO twinguard.{table} ({','.join(cols)}) SELECT {','.join(select_expr)} FROM twinguard.{stage}")
            actual = conn.execute(text(f"SELECT count(*) FROM twinguard.{table} WHERE source_id=:s"), {"s":key}).scalar_one()
            if int(actual) != count:
                raise RuntimeError(f"Loaded count mismatch for {key}: expected {count}, got {actual}")
            if catalogue:
                conn.execute(text("""INSERT INTO twinguard.dataset_catalog
                    (layer_key,source_path,source_layer,source_sha256,source_crs,target_srid,
                     loaded_row_count,caveat,licence_note)
                    VALUES (:k,:p,:l,:h,:c,32644,:n,:v,:lic)"""),
                    {"k":key,"p":source.relative_to(ROOT).as_posix(),"l":layer,"h":digest,"c":crs,
                     "n":count,"v":caveat,"lic":"OpenStreetMap-derived; ODbL attribution/share-alike applies." if "osm" in str(source).lower() else "See source metadata; not independently confirmed."})
            conn.exec_driver_sql(f"DROP TABLE twinguard.{stage}")
    except Exception:
        with engine.begin() as conn:
            conn.exec_driver_sql(f"DROP TABLE IF EXISTS twinguard.{stage}")
        raise
    return count


def load_road_nodes(engine) -> int:
    src=ROOT/"data/features/roads/chennai_road_graph.gpkg"; digest=sha256(src)
    d=gpd.read_file(src,layer="road_nodes").rename(columns={"osmid":"source_osmid","directed_degree":"degree"})
    d["node_id"]=d.source_osmid.astype(str); d["component_id"]=None
    return _load_gdf(engine,"road_nodes","stage5_road_nodes",src,"road_nodes",d,digest,"EPSG:32644",
        "Road graph nodes; component ids were not present in the node source and remain NULL.",
        geometry_type="POINT",target_columns=["node_id","source_osmid","degree","component_id","geom"])


def load_buildings(engine) -> int:
    src=ROOT/"data/features/buildings/chennai_building_footprints.gpkg"; digest=sha256(src)
    d=gpd.read_file(src,layer="building_footprints").rename(columns={"osmid":"source_osmid"})
    return _load_gdf(engine,"building_footprints","stage5_buildings",src,"building_footprints",d,digest,"EPSG:32644",
        "OpenStreetMap building footprints; coverage and building completeness are not guaranteed.",
        geometry_type="GEOMETRY",target_columns=["source_osmid","building","name","geom"])


def load_grid(engine, batch_size: int=25000) -> int:
    src=ROOT/"data/features/static/cell_table.parquet"; digest=sha256(src); key="stage5_grid_cells"
    count=pq.ParquetFile(src).metadata.num_rows
    if count != 1_319_380:
        raise RuntimeError(f"Unexpected grid source rows: {count}")
    with engine.connect() as conn:
        previous=conn.execute(text("SELECT source_sha256,loaded_row_count FROM twinguard.dataset_catalog WHERE layer_key=:k"),{"k":key}).first()
        loaded=conn.execute(text("SELECT count(*) FROM twinguard.grid_cells WHERE source_id=:k"),{"k":key}).scalar_one()
        if previous:
            if previous[0]==digest and int(previous[1])==int(loaded)==count:return count
            raise RuntimeError("Refusing partial or changed grid import")
        if loaded: raise RuntimeError("Uncatalogued grid rows exist; refusing duplicate import")
    fields=["row","col","x","y","cell_id","elevation_m","slope_deg","twi_d8_proxy","flow_accumulation_cells_d8","worldpop_2021","population_is_nodata","built_up_fraction","water_fraction","building_density_per_km2","distance_to_nearest_road_node_m","distance_to_exact_named_waterway_m","distance_to_coast_m","coast_distance_available"]
    raw=engine.raw_connection()
    try:
        cur=raw.cursor()
        cur.execute("BEGIN")
        cur.execute("CREATE TEMP TABLE stage_grid (row_index integer,col_index integer,x double precision,y double precision,cell_id text,elevation_m double precision,slope_deg double precision,twi_d8_proxy double precision,flow_accumulation_cells_d8 double precision,worldpop_2021 double precision,population_is_nodata boolean,built_up_fraction double precision,water_fraction double precision,building_density_per_km2 double precision,distance_to_nearest_road_node_m double precision,distance_to_exact_named_waterway_m double precision,distance_to_coast_m double precision,coast_distance_available boolean) ON COMMIT DROP")
        copied=0
        pf=pq.ParquetFile(src)
        for batch in pf.iter_batches(batch_size=batch_size,columns=fields):
            df=batch.to_pandas()
            rows=[]
            for t in df.itertuples(index=False,name=None):
                vals=list(t); vals[0]=int(vals[0]); vals[1]=int(vals[1]); vals[4]=str(vals[4]);
                # Arrow nulls and NaNs are both represented as SQL NULL.
                rows.append(tuple(None if (v is None or (isinstance(v,float) and math.isnan(v))) else v for v in vals))
            with cur.copy("COPY stage_grid FROM STDIN") as cp:
                for row in rows: cp.write_row(row)
            copied+=len(rows); print(f"COPY grid batch: {copied}/{count}",flush=True)
        if copied!=count: raise RuntimeError(f"COPY source row count mismatch: {copied} != {count}")
        cur.execute("""INSERT INTO twinguard.grid_cells
            (row_index,col_index,x,y,cell_id,elevation_m,slope_deg,twi_d8_proxy,flow_accumulation_cells_d8,worldpop_2021,population_is_nodata,built_up_fraction,water_fraction,building_density_per_km2,distance_to_nearest_road_node_m,distance_to_exact_named_waterway_m,distance_to_coast_m,coast_distance_available,geom,source_id,source_sha256,loader,load_time)
            SELECT row_index,col_index,x,y,cell_id,elevation_m,slope_deg,twi_d8_proxy,flow_accumulation_cells_d8,worldpop_2021,population_is_nodata,built_up_fraction,water_fraction,building_density_per_km2,distance_to_nearest_road_node_m,distance_to_exact_named_waterway_m,distance_to_coast_m,coast_distance_available,ST_SetSRID(ST_MakePoint(x,y),32644),'stage5_grid_cells',%s,%s,now() FROM stage_grid""",(digest,LOADER))
        cur.execute("SELECT count(*) FROM twinguard.grid_cells WHERE source_id='stage5_grid_cells'")
        actual=cur.fetchone()[0]
        if actual!=count: raise RuntimeError(f"Grid loaded count mismatch: {actual} != {count}")
        cur.execute("""INSERT INTO twinguard.dataset_catalog(layer_key,source_path,source_layer,source_sha256,source_crs,target_srid,loaded_row_count,caveat,licence_note)
            VALUES (%s,%s,%s,%s,%s,32644,%s,%s,%s)""",(key,src.relative_to(ROOT).as_posix(),"cell_table",digest,"EPSG:32644",count,"Native 30 m grid; population NoData retained with explicit flag.","Derived from project features; refer to source-specific licences."))
        raw.commit(); return int(actual)
    except Exception:
        raw.rollback(); raise
    finally: raw.close()


def _copy_observations(engine, key: str, src: Path, digest: str, rows: list[tuple], caveat: str) -> int:
    # rows: record_key, series, observed_at, variable, value, unit, qc, point, metadata_json, EWKT
    count=len(rows)
    with engine.connect() as conn:
        old=conn.execute(text("SELECT source_sha256,loaded_row_count FROM twinguard.dataset_catalog WHERE layer_key=:k"),{"k":key}).first()
        cur=conn.execute(text("SELECT count(*) FROM twinguard.observation_records WHERE source_id=:k"),{"k":key}).scalar_one()
        if old:
            if old[0]==digest and int(old[1])==int(cur)==count:return count
            raise RuntimeError(f"Refusing changed or partial observations source {key}")
        if cur: raise RuntimeError(f"Uncatalogued observation rows for {key}")
    raw=engine.raw_connection()
    try:
        cur=raw.cursor(); cur.execute("BEGIN")
        with cur.copy("COPY twinguard.observation_records(record_key,series,observed_at,variable,value,unit,qc_flag,station_or_point,metadata,geom,source_id,source_sha256,loader,load_time) FROM STDIN") as cp:
            for r in rows:
                keyv,series,ts,var,val,unit,qc,point,meta,ewkt=r
                cp.write_row((keyv,series,ts,var,val,unit,qc,point,json.dumps(meta,ensure_ascii=False),ewkt,key,digest,LOADER,datetime.now(timezone.utc)))
        cur.execute("""INSERT INTO twinguard.dataset_catalog(layer_key,source_path,source_layer,source_sha256,source_crs,target_srid,loaded_row_count,caveat,licence_note)
            VALUES (%s,%s,%s,%s,%s,32644,%s,%s,%s)""",(key,src.relative_to(ROOT).as_posix(),src.stem,digest,"EPSG:4326 or tabular",count,caveat,"Source-specific terms recorded in project manifest."))
        raw.commit(); return count
    except Exception: raw.rollback(); raise
    finally: raw.close()


def load_observations(engine) -> dict[str,int]:
    out={}; tf=Transformer.from_crs(4326,32644,always_xy=True)
    # ERA5 hourly values: preserve the source's timestamp_utc, point ids, native hourly values.
    src=ROOT/"data/features/weather/era5_event_hourly_features.csv"; digest=sha256(src); df=pd.read_csv(src)
    vars={"precipitation":"mm","temperature_2m":"C","relative_humidity_2m":"%","wind_speed_10m":"m/s","pressure_msl":"hPa"}
    rows=[]
    for r in df.itertuples(index=False):
        lon=float(r.grid_longitude);lat=float(r.grid_latitude);x,y=tf.transform(lon,lat); ts=pd.Timestamp(r.timestamp_utc).to_pydatetime()
        for var,unit in vars.items():
            val=getattr(r,var); val=None if pd.isna(val) else float(val)
            rows.append((f"era5|{r.point_id}|{ts.isoformat()}|{var}","ERA5 hourly",ts,var,val,unit,"MISSING" if val is None else "OK",str(r.point_id),{"timezone_local":str(r.timestamp_local),"native_cadence":"hourly"},f"SRID=32644;POINT({x} {y})"))
    out["era5_hourly"]=_copy_observations(engine,"stage5_obs_era5",src,digest,rows,"Hourly values from the existing ERA5 event feature table; no fabricated sub-hourly values.")
    # NASA POWER daily raw JSON, all points and variables with source-declared units.
    for src in sorted((ROOT/"data/raw/weather").glob("nasa_power_daily_point_*.json")):
        digest=sha256(src); doc=json.loads(src.read_text(encoding="utf-8")); pars=doc["properties"]["parameter"]; header=doc.get("header",{}); coords=doc["geometry"]["coordinates"]; lon,lat=coords[:2]; x,y=tf.transform(lon,lat); point=src.stem.split("point_")[-1].split("_")[0]
        rows=[]
        for var,series in pars.items():
            unit=doc.get("parameters",{}).get(var,{}).get("units")
            for day,val in series.items():
                number=None if val is None or float(val)==float(header.get("fill_value",-999)) else float(val)
                ts=datetime.strptime(day,"%Y%m%d").replace(tzinfo=timezone.utc)
                rows.append((f"power|{point}|{day}|{var}","NASA POWER daily",ts,var,number,unit,"MISSING" if number is None else "OK",point,{"time_standard":header.get("time_standard"),"source":"POWER API"},f"SRID=32644;POINT({x} {y})"))
        key=f"stage5_obs_power_{point}"
        out[key]=_copy_observations(engine,key,src,digest,rows,"NASA POWER native daily point series; units are copied from JSON parameter metadata.")
    # IMERG CMA daily means are existing, documented derived values; link every day to its raw NetCDF source.
    report=ROOT/"docs/RAIN_SOURCES_COMPARISON.md"; report_text=report.read_text(encoding="utf-8")
    daily_by_date={}
    pat=re.compile(r"\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|")
    for m in pat.finditer(report_text): daily_by_date[m.group(1)]=float(m.group(2))
    imerg_files=list((ROOT/"data/raw/weather/imerg").glob("*.nc4"))
    rows=[]
    for day,val in sorted(daily_by_date.items()):
        srcfile=next((p for p in imerg_files if day.replace("-","") in p.name),None)
        if not srcfile: continue
        ts=datetime.strptime(day,"%Y-%m-%d").replace(tzinfo=timezone.utc)
        rows.append((f"imerg_cma|{day}","IMERG daily CMA mean",ts,"precipitation",val,"mm/day","OK","CMA",{"source":"RAIN_SOURCES_COMPARISON.md; raw daily grid values summarized there","time_standard":"UTC"},None))
    if rows:
        digest=sha256(report)
        out["imerg_daily"]=_copy_observations(engine,"stage5_obs_imerg_daily",report,digest,rows,"Daily CMA means are loaded from the project's documented comparison table; 86 underlying raw NetCDF files are read-only and linked by date. Values are not independently recalculated in this loader.")
    # Reservoir feature-series inputs; keep each native daily/monthly value and flag missing cells.
    for rel,kind in [("data/features/reservoirs/kaggle_daily_storage_features.csv","daily"),("data/features/reservoirs/opencity_monthly_storage_tidy.csv","monthly")]:
        src=ROOT/rel; digest=sha256(src); d=pd.read_csv(src); rows=[]
        if kind=="daily":
            for r in d.itertuples(index=False):
                ts=pd.Timestamp(r.date).to_pydatetime().replace(tzinfo=timezone.utc); val=None if pd.isna(r.storage_mcft) else float(r.storage_mcft)
                rows.append((f"reservoir_daily|{r.reservoir}|{r.date}","reservoir daily",ts,"storage",val,"mcft","MISSING" if val is None else "OK",str(r.reservoir),{"source":"Kaggle-derived feature CSV","capacity_percent":None if pd.isna(r.capacity_percent) else float(r.capacity_percent)},None))
        else:
            for r in d.itertuples(index=False):
                ts=pd.Timestamp(r.date).to_pydatetime().replace(tzinfo=timezone.utc); val=None if pd.isna(r.storage_mcft) else float(r.storage_mcft)
                rows.append((f"reservoir_monthly|{r.reservoir}|{r.date}","lake monthly",ts,"storage",val,"mcft","MISSING" if val is None else "OK",str(r.reservoir),{"source_file":str(r.source_file)},None))
        key=f"stage5_obs_reservoir_{kind}"
        out[kind+"_reservoirs"]=_copy_observations(engine,key,src,digest,rows,"Storage series; mcft unit retained. Reservoir releases are not represented.")
    return out


def load_flood_labels(engine) -> dict[str,int]:
    out={}
    # Register the existing UNOSAT features as explicit, repaired label geometries.
    src=ROOT/"data/raw/historical_floods/2015/2015-12-04/FL20151123IND_shp.zip"; digest=sha256(src)
    with engine.begin() as conn:
        existing=conn.execute(text("SELECT count(*) FROM twinguard.flood_labels WHERE label_type='UNOSAT'")).scalar_one()
        if existing==0:
            conn.execute(text("""INSERT INTO twinguard.flood_labels
                (label_key,label_name,event_date,label_type,confidence_tier,source_properties,geom,is_valid,source_id,source_sha256,loader)
                SELECT 'unosat|'||feature_id,source_layer,event_date,'UNOSAT',
                       CASE WHEN reference_role='event_flood' THEN 'HIGH' ELSE 'MEDIUM' END,
                       source_properties,geom_repaired,is_valid,'stage5_unosat_'||source_layer,:h,:loader
                FROM twinguard.flood_references"""),{"h":digest,"loader":LOADER})
            for layer,count in conn.execute(text("SELECT source_layer,count(*) FROM twinguard.flood_references GROUP BY source_layer")):
                key="stage5_unosat_"+layer
                conn.execute(text("""INSERT INTO twinguard.dataset_catalog(layer_key,source_path,source_layer,source_sha256,source_crs,target_srid,loaded_row_count,caveat,licence_note)
                    VALUES (:k,:p,:l,:h,'EPSG:4326',32644,:n,:c,'UNOSAT product terms: CC BY-NC-SA 3.0 Unported; original geometries retained in flood_references.')"""),{"k":key,"p":src.relative_to(ROOT).as_posix(),"l":layer,"h":digest,"n":count,"c":"UNOSAT reference; baseline layers are water reference, not event inundation labels."})
            out["UNOSAT"]=int(existing or 10419)
    base=ROOT/"data/raw/historical_floods/2015/opencity_flood_points"
    observed={"814ca028-4c84-4bd0-aa67-6dbaeb9b6ba5.kml":"OpenCity inundation points with depth","93d2905a-a580-482d-96b0-4d9ccf5273ef.kml":"OpenCity water stagnation points"}
    for p in sorted(base.glob("*.kml")):
        d=gpd.read_file(p); dig=sha256(p); is_obs=p.name in observed
        typ="OBSERVED" if is_obs else "MODELLED"; tier="MEDIUM" if is_obs else "LOW"; is_model=not is_obs
        if p.name in observed:
            event=None; name=observed[p.name]
        else:
            event=None; name="OpenCity modelled hazard/return-period polygon"
        d=d.to_crs(32644)
        # Only store supported feature properties, not lossy GML internals.
        with engine.begin() as conn:
            n=conn.execute(text("SELECT count(*) FROM twinguard.flood_labels WHERE source_id=:s"),{"s":"opencity_"+p.stem}).scalar_one()
            if n:
                catalog=conn.execute(text("SELECT source_sha256,loaded_row_count FROM twinguard.dataset_catalog WHERE layer_key=:k"),{"k":"opencity_"+p.stem}).first()
                if catalog and catalog[0]==dig and int(catalog[1])==int(n)==len(d):
                    continue
                raise RuntimeError(f"Refusing partial or changed OpenCity label source: {p.name}")
            inserts=[]
            for ix,r in d.iterrows():
                geom=force_2d(r.geometry)
                if geom is None or geom.is_empty: continue
                props={k:(None if pd.isna(v) else str(v)) for k,v in r.drop(labels=[d.geometry.name]).items() if k in {"Name","description","DEPTH","F_REMARKS","CATEGORY","INDEX_","SOURCE","OBJECTID","ZONE"}}
                label_key="opencity|"+p.stem+"|"+str(ix)
                ewkt="SRID=32644;"+geom.wkt
                inserts.append({"key":label_key,"name":name,"day":event,"type":typ,"tier":tier,"model":is_model,"props":json.dumps(props,ensure_ascii=False),"geom":ewkt,"valid":bool(geom.is_valid),"sid":"opencity_"+p.stem,"hash":dig,"loader":LOADER})
            if inserts:
                conn.execute(text("""INSERT INTO twinguard.flood_labels
                    (label_key,label_name,event_date,label_type,confidence_tier,is_modelled,source_properties,geom,is_valid,source_id,source_sha256,loader)
                    VALUES (:key,:name,:day,:type,:tier,:model,CAST(:props AS jsonb),ST_GeomFromEWKT(:geom),:valid,:sid,:hash,:loader)"""), inserts)
        with engine.begin() as conn:
            conn.execute(text("""INSERT INTO twinguard.dataset_catalog(layer_key,source_path,source_layer,source_sha256,source_crs,target_srid,loaded_row_count,caveat,licence_note)
                VALUES (:k,:p,:l,:h,'EPSG:4326',32644,:n,:c,'OpenCity page indicates public domain; record the page terms with the project source citation.')"""),{"k":"opencity_"+p.stem,"p":p.relative_to(ROOT).as_posix(),"l":p.stem,"h":dig,"n":len(d),"c":"OBSERVED points or MODELLED hazard zones; modelled layers are not event observations."})
        out[p.stem]=len(d)
    # GFD is metadata-only coarse cross-check; preserving original raster is intentional.
    gfd=ROOT/"data/raw/historical_floods/2015/global_flood_database/DFO_4309_From_20151110_to_20151204.zip"
    if gfd.exists():
        dig=sha256(gfd); sid="gfd_4309_coarse"
        with engine.begin() as conn:
            if not conn.execute(text("SELECT 1 FROM twinguard.flood_labels WHERE label_key=:k"),{"k":sid}).first():
                conn.execute(text("""INSERT INTO twinguard.flood_labels(label_key,label_name,event_date,label_type,confidence_tier,is_coarse,source_properties,source_id,source_sha256,loader)
                    VALUES (:k,'Global Flood Database DFO 4309',DATE '2015-11-10','COARSE CROSS-CHECK','LOW',true,
                    CAST(:props AS jsonb),:s,:h,:l)"""),{"k":sid,"props":json.dumps({"period":"2015-11-10 to 2015-12-04","approx_area_km2":65.43,"resolution":"about 250 m","geometry_loaded":False}),"s":sid,"h":dig,"l":LOADER})
                conn.execute(text("""INSERT INTO twinguard.dataset_catalog(layer_key,source_path,source_layer,source_sha256,source_crs,target_srid,loaded_row_count,caveat,licence_note)
                    VALUES (:k,:p,'DFO_4309',:h,'native raster',32644,1,'Metadata-only; coarse cross-check, not a local flood perimeter.','Check Global Flood Database attribution and licence.')"""),{"k":sid,"p":gfd.relative_to(ROOT).as_posix(),"h":dig})
        out[sid]=1
    # Existing exploratory label rasters are only registered as derived/unvalidated metadata.
    inspections=ROOT/"data/processed/labels_inspection"
    for p in sorted(inspections.glob("**/*")) if inspections.exists() else []:
        if not p.is_file(): continue
        sid="derived_"+p.stem
        with engine.begin() as conn:
            dig=sha256(p)
            if not conn.execute(text("SELECT 1 FROM twinguard.flood_labels WHERE label_key=:k"),{"k":sid}).first():
                conn.execute(text("""INSERT INTO twinguard.flood_labels(label_key,label_name,label_type,confidence_tier,is_derived,source_properties,source_id,source_sha256,loader)
                    VALUES (:k,:n,'DERIVED','UNVALIDATED',true,CAST(:props AS jsonb),:k,:h,:l)"""),{"k":sid,"n":p.name,"props":json.dumps({"source_path":p.relative_to(ROOT).as_posix(),"geometry_loaded":False}),"h":dig,"l":LOADER})
            if not conn.execute(text("SELECT 1 FROM twinguard.dataset_catalog WHERE layer_key=:k"),{"k":sid}).first():
                conn.execute(text("""INSERT INTO twinguard.dataset_catalog(layer_key,source_path,source_layer,source_sha256,source_crs,target_srid,loaded_row_count,caveat,licence_note)
                    VALUES (:k,:p,:l,:h,'N/A',32644,1,'Exploratory derived label asset; unvalidated and no geometry loaded.','Inherited from the contributing source; review project manifest.')"""),{"k":sid,"p":p.relative_to(ROOT).as_posix(),"l":p.name,"h":dig})
    return out


def load_sentinel(engine) -> int:
    base=ROOT/"data/raw/satellite/sentinel1"; zip_paths=sorted(base.rglob("*.zip")); out=[]
    if len(zip_paths)!=13: raise RuntimeError(f"Expected 13 Sentinel-1 ZIPs; found {len(zip_paths)}")
    for p in zip_paths:
        digest=sha256(p); stem=p.stem; parts=stem.split("_"); scene_day=datetime.strptime(parts[4][:8],"%Y%m%d").date()
        with zipfile.ZipFile(p) as z:
            manifest=next((n for n in z.namelist() if n.endswith("manifest.safe")),None)
            if not manifest: raise RuntimeError(f"SAFE manifest not found in {p.name}")
            xml=ET.fromstring(z.read(manifest)); coords=[]
            for elem in xml.iter():
                if elem.tag.endswith("coordinates") and elem.text:
                    raw=elem.text.strip().replace("\n"," ").split()
                    if len(raw)>=4:
                        coords=[(float(pair.split(",")[1]),float(pair.split(",")[0])) for pair in raw]
                        break
            if len(coords)<4: raise RuntimeError(f"Footprint coordinates not found in {p.name}")
        footprint=Polygon(coords)
        # Check plausibility: Chennai-area scenes should cross the CMA latitude/longitude bounds.
        if footprint.bounds[0]<70 or footprint.bounds[0]>90 or footprint.bounds[1]<5 or footprint.bounds[1]>25:
            raise RuntimeError(f"Unexpected Sentinel footprint axis order in {p.name}")
        sid="sentinel1_"+stem
        with engine.begin() as conn:
            prior=conn.execute(text("SELECT source_sha256 FROM twinguard.sentinel_scenes WHERE scene_key=:k"),{"k":stem}).scalar_one_or_none()
            if prior:
                if prior==digest: continue
                raise RuntimeError(f"Sentinel scene already exists with changed hash: {stem}")
            conn.execute(text("""INSERT INTO twinguard.sentinel_scenes
                (scene_key,scene_date,platform,product_type,relative_orbit,pass_direction,polarization,source_filename,metadata,footprint,source_id,source_sha256,loader)
                VALUES (:k,:d,:platform,:product,:orbit,:pass,:pol,:fn,CAST(:meta AS jsonb),ST_GeomFromText(:wkt,4326),:sid,:h,:loader)"""),{
                "k":stem,"d":scene_day,"platform":parts[0],"product":parts[2],"orbit":None,"pass":"DESCENDING","pol":parts[3],"fn":p.name,
                "meta":json.dumps({"source_path":p.relative_to(ROOT).as_posix(),"platform":parts[0],"product_type":parts[2],"absolute_orbit":int(parts[6]),"scene_stem":stem},ensure_ascii=False),"wkt":footprint.wkt,"sid":sid,"h":digest,"loader":LOADER})
            conn.execute(text("""INSERT INTO twinguard.dataset_catalog(layer_key,source_path,source_layer,source_sha256,source_crs,target_srid,loaded_row_count,caveat,licence_note)
                VALUES (:k,:p,:l,:h,'EPSG:4326',32644,1,'ZIP metadata and manifest footprint only; no scene pixels loaded or processed.','Copernicus Sentinel data are free and open; cite ESA/Copernicus.')"""),{"k":sid,"p":p.relative_to(ROOT).as_posix(),"l":"manifest.safe","h":digest})
        out.append(stem)
    return len(out)


def load_manifest(engine) -> int:
    src=ROOT/"docs/DATA_MANIFEST.csv"; digest=sha256(src); rows=list(csv.DictReader(src.open(encoding="utf-8-sig",newline="")))
    key="stage5_data_manifest"
    with engine.connect() as conn:
        old=conn.execute(text("SELECT source_sha256,loaded_row_count FROM twinguard.dataset_catalog WHERE layer_key=:k"),{"k":key}).first()
        current=conn.execute(text("SELECT count(*) FROM twinguard.data_manifest WHERE source_id=:k"),{"k":key}).scalar_one()
        if old:
            if old[0]==digest and int(old[1])==int(current)==len(rows):return len(rows)
            raise RuntimeError("Manifest changed or partially loaded; refusing overwrite")
        if current: raise RuntimeError("Uncatalogued manifest rows exist")
    raw=engine.raw_connection()
    try:
        cur=raw.cursor(); cur.execute("BEGIN")
        with cur.copy("COPY twinguard.data_manifest(manifest_key,row_data,source_id,source_sha256,loader,load_time) FROM STDIN") as cp:
            for n,row in enumerate(rows):
                ident="|".join(str(row.get(k,"")) for k in ("dataset","filename","sha256")) or str(n)
                cp.write_row((ident,json.dumps(row,ensure_ascii=False),key,digest,LOADER,datetime.now(timezone.utc)))
        cur.execute("""INSERT INTO twinguard.dataset_catalog(layer_key,source_path,source_layer,source_sha256,source_crs,target_srid,loaded_row_count,caveat,licence_note)
            VALUES (%s,%s,%s,%s,'CSV',32644,%s,'Snapshot of the project manifest at load time.','As recorded per source row.')""",(key,src.relative_to(ROOT).as_posix(),"DATA_MANIFEST.csv",digest,len(rows)))
        raw.commit(); return len(rows)
    except Exception: raw.rollback(); raise
    finally: raw.close()


def main() -> None:
    from pipelines.stage5.db_common import make_engine
    engine=make_engine()
    try:
        result={"road_nodes":load_road_nodes(engine),"grid_cells":load_grid(engine),"buildings":load_buildings(engine)}
        result["observations"]=load_observations(engine)
        result["flood_labels"]=load_flood_labels(engine)
        result["sentinel_scenes"]=load_sentinel(engine)
        result["data_manifest"]=load_manifest(engine)
        print(json.dumps(result,sort_keys=True,default=str))
    finally: engine.dispose()


if __name__=="__main__": main()
