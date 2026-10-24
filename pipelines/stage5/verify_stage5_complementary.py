"""Read-only Stage 5 reconciliation, topology, area, and query-plan audit."""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

from sqlalchemy import text

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from pipelines.stage5.db_common import make_engine


def main() -> None:
    engine=make_engine(); out={"tables":{},"groups":{},"areas":{},"reconciliation":{},"plans":{},"tiles":{}}
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SET statement_timeout='8min'")
            tables=["study_area","road_edges","facilities","waterways","flood_references","road_nodes","grid_cells","building_footprints","observation_records","flood_labels","sentinel_scenes","data_manifest","dataset_catalog"]
            for table in tables:
                start=time.perf_counter(); n=conn.execute(text(f"SELECT count(*) FROM twinguard.{table}")).scalar_one()
                out["tables"][table]={"rows":int(n),"seconds":round(time.perf_counter()-start,3)}
            queries={
              "facility_category":"SELECT category, count(*) AS n FROM twinguard.facilities GROUP BY category ORDER BY category",
              "waterway_type":"SELECT waterway, count(*) AS n FROM twinguard.waterways GROUP BY waterway ORDER BY waterway",
              "flood_source_layer":"SELECT source_layer,count(*) AS n FROM twinguard.flood_references GROUP BY source_layer ORDER BY source_layer",
              "flood_validity_reasons":"SELECT source_layer,split_part(ST_IsValidReason(geom),'[',1) AS reason,count(*) AS n FROM twinguard.flood_references WHERE NOT ST_IsValid(geom) GROUP BY source_layer,reason ORDER BY source_layer,reason",
              "repaired_validity":"SELECT count(*) FILTER (WHERE NOT is_valid OR geom_repaired IS NULL OR ST_IsEmpty(geom_repaired)) AS bad,count(*) AS total FROM twinguard.flood_references",
              "label_types":"SELECT label_type,confidence_tier,count(*) AS n FROM twinguard.flood_labels GROUP BY label_type,confidence_tier ORDER BY label_type,confidence_tier",
              "observation_series":"SELECT series,variable,unit,qc_flag,count(*) AS n FROM twinguard.observation_records GROUP BY series,variable,unit,qc_flag ORDER BY series,variable,unit,qc_flag",
              "sources_by_table":"SELECT table_name,source_id,count(*) n FROM (SELECT 'road_nodes' table_name,source_id FROM twinguard.road_nodes UNION ALL SELECT 'grid_cells',source_id FROM twinguard.grid_cells UNION ALL SELECT 'building_footprints',source_id FROM twinguard.building_footprints UNION ALL SELECT 'observation_records',source_id FROM twinguard.observation_records UNION ALL SELECT 'flood_labels',source_id FROM twinguard.flood_labels UNION ALL SELECT 'sentinel_scenes',source_id FROM twinguard.sentinel_scenes UNION ALL SELECT 'data_manifest',source_id FROM twinguard.data_manifest UNION ALL SELECT 'road_edges',source_id FROM twinguard.road_edges UNION ALL SELECT 'facilities',source_id FROM twinguard.facilities UNION ALL SELECT 'waterways',source_id FROM twinguard.waterways UNION ALL SELECT 'flood_references',source_id FROM twinguard.flood_references UNION ALL SELECT 'study_area',source_id FROM twinguard.study_area) x GROUP BY table_name,source_id ORDER BY table_name,source_id",
            }
            for k,q in queries.items():out["groups"][k]=[dict(r._mapping) for r in conn.execute(text(q))]
            out["reconciliation"]["osm_graph_sources"]={
              "road_segments":int(conn.execute(text("SELECT count(*) FROM twinguard."+"road_edges")).scalar_one()),
              "directed_arcs":1071656,"vehicle_edges":455285,
              "facility_counts_manifest":[dict(r._mapping) for r in conn.execute(text("SELECT category,count(*) n FROM twinguard.facilities GROUP BY category ORDER BY category"))],
              "waterways_loaded":int(conn.execute(text("SELECT count(*) FROM twinguard.waterways")).scalar_one()),"waterways_bbox_source":816}
            # Compare raw and repaired area by source layer; aggregate in projected CRS 32644.
            q="""SELECT source_layer,count(*) AS features,
                round((sum(ST_Area(geom))/1e6)::numeric,4) AS raw_sum_area_km2,
                round((sum(ST_Area(geom_repaired))/1e6)::numeric,4) AS repaired_sum_area_km2,
                round(((sum(ST_Area(geom_repaired))-sum(ST_Area(geom)))/1e6)::numeric,4) AS sum_area_delta_km2
                FROM twinguard.flood_references GROUP BY source_layer ORDER BY source_layer"""
            out["areas"]["by_source_layer"]=[dict(r._mapping) for r in conn.execute(text(q))]
            for layer in ("S1_20151112_Flood","S1_20151124_Flood"):
                start=time.perf_counter()
                r=conn.execute(text("""WITH dissolved AS (
                    SELECT ST_UnaryUnion(ST_Collect(geom_repaired)) AS geom
                    FROM twinguard.flood_references WHERE source_layer=:layer
                    ), clipped AS (
                    SELECT ST_Intersection(d.geom,s.geom) AS geom FROM dissolved d CROSS JOIN twinguard.study_area s)
                    SELECT ST_Area(geom)/1000000.0 FROM clipped"""),{"layer":layer}).scalar_one()
                out["areas"][layer]={"area_km2":float(r),"seconds":round(time.perf_counter()-start,3),"reference_km2":84.78 if layer == "S1_20151112_Flood" else 98.16}
            checks={
              "outside_road_edges":"SELECT count(*) FROM twinguard.road_edges WHERE NOT in_cma",
              "outside_facilities":"SELECT count(*) FROM twinguard.facilities WHERE NOT in_cma",
              "outside_buildings":"SELECT count(*) FROM twinguard.building_footprints WHERE NOT in_cma",
              "outside_grid":"SELECT count(*) FROM twinguard.grid_cells g,twinguard.study_area s WHERE NOT ST_CoveredBy(g.geom,s.geom)",
              "outside_road_nodes":"SELECT count(*) FROM twinguard.road_nodes WHERE NOT in_cma",
              "outside_waterways":"SELECT count(*) FROM twinguard.waterways WHERE NOT in_cma",
              "invalid_label_geometries_original":"SELECT count(*) FROM twinguard.flood_labels WHERE geom IS NOT NULL AND NOT ST_IsValid(geom)",
              "invalid_label_geometries_repaired":"SELECT count(*) FROM twinguard.flood_labels WHERE geom_repaired IS NOT NULL AND (NOT geometry_valid_after_repair OR NOT ST_IsValid(geom_repaired))",
              "sentinel_footprints_intersect_cma":"SELECT count(*) FROM twinguard.sentinel_scenes a,twinguard.study_area s WHERE ST_Intersects(ST_Transform(a.footprint,32644),s.geom)",
              "catalog_count_mismatches":"WITH allrows AS (SELECT source_id,count(*) n FROM (SELECT source_id FROM twinguard.study_area UNION ALL SELECT source_id FROM twinguard.road_edges UNION ALL SELECT source_id FROM twinguard.facilities UNION ALL SELECT source_id FROM twinguard.waterways UNION ALL SELECT source_id FROM twinguard.flood_references UNION ALL SELECT source_id FROM twinguard.road_nodes UNION ALL SELECT source_id FROM twinguard.grid_cells UNION ALL SELECT source_id FROM twinguard.building_footprints UNION ALL SELECT source_id FROM twinguard.observation_records UNION ALL SELECT source_id FROM twinguard.flood_labels UNION ALL SELECT source_id FROM twinguard.sentinel_scenes UNION ALL SELECT source_id FROM twinguard.data_manifest) x GROUP BY source_id) SELECT count(*) FROM allrows a JOIN twinguard.dataset_catalog c ON c.layer_key=a.source_id WHERE a.n<>c.loaded_row_count",
              "orphan_catalog_provenance":"SELECT count(*) FROM (SELECT source_id FROM twinguard.study_area UNION ALL SELECT source_id FROM twinguard.road_edges UNION ALL SELECT source_id FROM twinguard.facilities UNION ALL SELECT source_id FROM twinguard.waterways UNION ALL SELECT source_id FROM twinguard.flood_references UNION ALL SELECT source_id FROM twinguard.road_nodes UNION ALL SELECT source_id FROM twinguard.grid_cells UNION ALL SELECT source_id FROM twinguard.building_footprints UNION ALL SELECT source_id FROM twinguard.observation_records UNION ALL SELECT source_id FROM twinguard.flood_labels UNION ALL SELECT source_id FROM twinguard.sentinel_scenes UNION ALL SELECT source_id FROM twinguard.data_manifest) d LEFT JOIN twinguard.dataset_catalog c ON c.layer_key=d.source_id WHERE c.layer_key IS NULL"
            }
            out["checks"]={k:int(conn.execute(text(q)).scalar_one()) for k,q in checks.items()}
            geometry_columns={
              "study_area":"geom","road_edges":"geom","facilities":"geom","waterways":"geom",
              "flood_references":"geom","flood_references_repaired":"geom_repaired","road_nodes":"geom",
              "grid_cells":"geom","building_footprints":"geom","observation_records":"geom",
              "flood_labels":"geom","flood_labels_repaired":"geom_repaired","sentinel_scenes":"footprint"}
            out["geometry"]={}
            for key,col in geometry_columns.items():
                table="flood_references" if key=="flood_references_repaired" else ("flood_labels" if key=="flood_labels_repaired" else key)
                row=conn.execute(text(f"SELECT count(*) FILTER (WHERE {col} IS NOT NULL) n, string_agg(DISTINCT ST_SRID({col})::text, ',') srids, count(*) FILTER (WHERE {col} IS NOT NULL AND NOT ST_IsValid({col})) invalid FROM twinguard.{table}")).first()
                out["geometry"][key]={"non_null":int(row[0]),"srids":row[1],"invalid":int(row[2])}
            # Representative indexed query plans with actual execution times.
            params={"lon":80.25,"lat":13.05}
            plan_queries={
              "nearest_hospital_knn":"SELECT f.feature_id FROM twinguard.facilities f WHERE f.category='hospital' ORDER BY f.geom <-> (SELECT ST_Transform(ST_SetSRID(ST_MakePoint(:lon,:lat),4326),32644)) LIMIT 1",
              "roads_intersect_flood":"WITH f AS MATERIALIZED (SELECT geom_repaired AS geom FROM twinguard.flood_references WHERE feature_id=11064) SELECT r.feature_id FROM twinguard.road_edges r CROSS JOIN f WHERE r.geom && f.geom AND ST_Intersects(r.geom,f.geom) LIMIT 50",
              "buildings_intersect_flood":"WITH f AS MATERIALIZED (SELECT geom_repaired AS geom FROM twinguard.flood_references WHERE feature_id=11064) SELECT b.feature_id FROM twinguard.building_footprints b CROSS JOIN f WHERE b.geom && f.geom AND ST_Intersects(b.geom,f.geom) LIMIT 50",
              "cells_intersect_flood":"WITH f AS MATERIALIZED (SELECT geom_repaired AS geom FROM twinguard.flood_references WHERE feature_id=11064) SELECT g.cell_id FROM twinguard.grid_cells g CROSS JOIN f WHERE g.geom && f.geom AND ST_Intersects(g.geom,f.geom) LIMIT 50"
            }
            for k,q in plan_queries.items():
                out["plans"][k]=[r[0] for r in conn.execute(text("EXPLAIN (ANALYZE,BUFFERS,FORMAT TEXT) "+q),params)]
            z=12;x=math.floor((80.25+180)/360*(2**z));lat=math.radians(13.05);y=math.floor((1-math.asinh(math.tan(lat))/math.pi)/2*(2**z))
            for fn in ("mvt_study_area","mvt_roads","mvt_facilities","mvt_waterways","mvt_flood_references"):
                t=time.perf_counter();n=conn.execute(text(f"SELECT octet_length(twinguard.{fn}(:z,:x,:y))"),{"z":z,"x":x,"y":y}).scalar_one()
                out["tiles"][fn]={"bytes":int(n or 0),"seconds":round(time.perf_counter()-t,3)}
        print(json.dumps(out,default=str,indent=2))
    finally: engine.dispose()

if __name__=="__main__":main()
