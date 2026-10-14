#!/usr/bin/env python
"""Build a small inventory summary from the existing OSM GeoPackage without changing it."""
from __future__ import annotations
import json
from pathlib import Path
import pyogrio

ROOT=Path(__file__).resolve().parents[2]
GPKG=ROOT/'data/features/osm/chennai_osm_features.gpkg'
OUT=ROOT/'data/features/osm/osm_graph_summary.json'

def main():
    if not GPKG.exists(): raise FileNotFoundError(GPKG)
    if OUT.exists(): raise FileExistsError(f'Refusing to overwrite {OUT}')
    layers={}
    for name,_ in pyogrio.list_layers(GPKG):
        info=pyogrio.read_info(GPKG,layer=name)
        layers[name]={'features':int(info['features']),'geometry_type':str(info['geometry_type']),'crs':str(info['crs'])}
    roads=pyogrio.read_dataframe(GPKG,layer='road_segments',columns=['highway','length_m'],read_geometry=False)
    facilities=pyogrio.read_dataframe(GPKG,layer='facilities',columns=['category'],read_geometry=False)
    waterways=pyogrio.read_dataframe(GPKG,layer='waterways',columns=['name'],read_geometry=False)
    targets={'adyar','adyar river','cooum','cooum river','kosasthalaiyar','kosasthalaiyar river','buckingham canal','otteri nala'}
    exact=waterways.name.fillna('').str.strip().str.casefold().isin(targets)
    payload={'source':'Existing extracted GeoPackage; raw OSM PBF was not reread or modified','gpkg':'data/features/osm/chennai_osm_features.gpkg','extent':'CMA polygon plus 2 km; extracted from Southern Zone OSM snapshot','crs':'EPSG:32644','layers':layers,'road_length_m_sum':float(roads.length_m.sum()),'road_segment_counts_by_highway':{str(k):int(v) for k,v in roads.groupby('highway',dropna=False).size().items()},'facility_counts_by_category':{str(k):int(v) for k,v in facilities.groupby('category',dropna=False).size().items()},'waterway_segments':int(len(waterways)),'exact_target_waterway_segments':int(exact.sum()),'graph_connectivity':'Not recomputed in this inventory-only summary; validate component/connectivity and dangling-edge behavior before routing.','caveats':['OSM mapping completeness is unknown; absence is not evidence of real-world absence.','Road segments and directed arcs are derived vector features, not a validated routable network.','Facility and building tags vary in completeness.','Follow ODbL attribution/share-alike obligations for qualifying derived databases.']}
    OUT.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'summary':str(OUT.relative_to(ROOT)),'layers':layers,'road_length_m_sum':payload['road_length_m_sum']},indent=2))

if __name__=='__main__':main()
