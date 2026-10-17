#!/usr/bin/env python
"""Build an assumed vehicle-routing profile as new Phase 4 outputs."""
from __future__ import annotations
import argparse, heapq, json, math, random, re, uuid
from pathlib import Path
import geopandas as gpd
import numpy as np
import rasterio
from shapely.geometry import LineString
from shapely.strtree import STRtree

ROOT=Path(__file__).resolve().parents[2]
OSM=ROOT/'data/features/osm/chennai_osm_features.gpkg'
TARGET=ROOT/'data/processed/routing'
DEM=ROOT/'data/processed/terrain_cleaned/cleaned_elevation_m.tif'
REPORT=ROOT/'docs/ROUTING_PROFILE.md'
INCLUDE={'motorway','motorway_link','trunk','trunk_link','primary','primary_link','secondary','secondary_link','tertiary','tertiary_link','unclassified','residential','living_street','service','road'}
SPEED={'motorway':100,'motorway_link':50,'trunk':80,'trunk_link':40,'primary':50,'primary_link':40,'secondary':40,'secondary_link':30,'tertiary':30,'tertiary_link':25,'unclassified':25,'residential':25,'living_street':15,'service':15,'road':25}

def blocked_by_depth(predicted_depth_m, threshold_m=0.3):
    """Return True at/above threshold; threshold is an assumption pending literature review."""
    return predicted_depth_m is not None and np.asarray(predicted_depth_m) >= threshold_m

def parse_speed(value, highway):
    if value:
        m=re.search(r'\d+(?:\.\d+)?',str(value))
        if m:
            v=float(m.group())
            if 'mph' in str(value).lower(): v*=1.609344
            if v>0: return v,False
    return SPEED.get(highway,25),True

def dijkstra(adj, targets):
    dist={}; q=[]
    for n in targets:
        if n not in dist: dist[n]=0.; heapq.heappush(q,(0.,n))
    while q:
        d,u=heapq.heappop(q)
        if d!=dist[u]: continue
        for v,w in adj.get(u,[]):
            nd=d+w
            if nd<dist.get(v,float('inf')): dist[v]=nd; heapq.heappush(q,(nd,v))
    return dist

def sample_dem(line, src, raster):
    # Sample at vertices plus interpolated positions every <=30 m.
    pts=[]
    for geom in (line.geoms if line.geom_type=='MultiLineString' else [line]):
        n=max(1,math.ceil(geom.length/30))
        pts.extend(geom.interpolate(i/n,normalized=True) for i in range(n+1))
    vals=[]
    for p in pts:
        try:
            r,c=src.index(p.x,p.y); v=float(raster[r,c])
            if src.nodata is None or v!=src.nodata: vals.append(v)
        except Exception: pass
    return ([min(vals),float(np.mean(vals)),max(vals)] if vals else [None,None,None])

def audit_unreachable(seed=42, sample_count=200):
    """Explain why the deterministic sample origins lack directed paths to facilities."""
    audit_path=TARGET/'routing_unreachable_audit.json'
    if audit_path.exists(): raise FileExistsError(f'Refusing to overwrite {audit_path}')
    seg=gpd.read_file(OSM,layer='road_segments'); nodes=gpd.read_file(OSM,layer='road_nodes'); fac=gpd.read_file(OSM,layer='facilities')
    seg=seg[seg.highway.astype(str).isin(INCLUDE)].copy()
    if 'access' in seg: seg=seg[~seg.access.astype(str).str.lower().isin(['no','private'])]
    ids=nodes.osmid.astype(int).to_list(); parent={n:n for n in ids}; rank={n:0 for n in ids}
    def find(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def union(x,y):
        x,y=find(x),find(y)
        if x==y:return
        if rank[x]<rank[y]:x,y=y,x
        parent[y]=x
        if rank[x]==rank[y]:rank[x]+=1
    adj={n:[] for n in ids}; rev={n:[] for n in ids}
    for _,e in seg.iterrows():
        u,v=int(e.node_a),int(e.node_b); union(u,v)
        h=str(e.highway); speed,_=parse_speed(e.get('maxspeed'),h); tm=float(e.length_m or e.geometry.length)/1000/speed*60; ow=str(e.get('oneway','')).lower()
        arcs=[(u,v)] if ow in ('yes','1','true') else ([(v,u)] if ow=='-1' else [(u,v),(v,u)])
        for x,y in arcs: adj[x].append((y,tm)); rev[y].append((x,tm))
    tree=STRtree(nodes.geometry.to_list()); node_geoms=nodes.geometry.to_list()
    targets={'hospital':[],'shelter':[]}
    for _,f in fac.iterrows():
        c=str(f.category).lower(); k='hospital' if 'hospital' in c else ('shelter' if 'shelter' in c else None)
        if k:
            ix=int(tree.nearest(f.geometry)); targets[k].append(ids[ix])
    rng=random.Random(seed); origins=rng.sample(ids,min(sample_count,len(ids)))
    result={'seed':seed,'sampled_origins':len(origins),'reasons':{},'unreachable_origin_nodes':{}}
    for k,ts in targets.items():
        reachable=set(dijkstra(rev,ts)); target_roots={find(t) for t in ts}
        missing=[n for n in origins if n not in reachable]; bins={'no_destination_in_same_weak_component':[],'same_weak_component_but_no_directed_path':[]}
        for n in missing:
            reason='same_weak_component_but_no_directed_path' if find(n) in target_roots else 'no_destination_in_same_weak_component'
            bins[reason].append(n)
        result['reasons'][k]={name:len(ns) for name,ns in bins.items()}
        result['unreachable_origin_nodes'][k]={name:ns for name,ns in bins.items()}
    audit_path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    lines=['','## Unreachable-origin cause audit','',f"With the same 200-origin seed ({seed}), the graph components separate unreachable origins as follows:"]
    for k in targets:
        r=result['reasons'][k]
        lines.append(f"- {k}: {r['no_destination_in_same_weak_component']} in a weak component with no destination; {r['same_weak_component_but_no_directed_path']} share a weak component with a destination but have no directed path (one-way/topology). Origin node IDs are in `data/processed/routing/routing_unreachable_audit.json`.")
    with REPORT.open('a',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
    print(json.dumps(result['reasons'],indent=2))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--seed',type=int,default=42); ap.add_argument('--origins',type=int,default=200); ap.add_argument('--audit-unreachable',action='store_true'); a=ap.parse_args()
    if a.audit_unreachable:
        if not TARGET.exists() or not REPORT.exists(): raise FileNotFoundError('Initial routing profile outputs are required before the unreachable audit')
        audit_unreachable(a.seed,a.origins); return
    if TARGET.exists() or REPORT.exists(): raise FileExistsError('Refusing to overwrite existing routing outputs/report')
    seg=gpd.read_file(OSM,layer='road_segments'); nodes=gpd.read_file(OSM,layer='road_nodes'); fac=gpd.read_file(OSM,layer='facilities')
    seg=seg[seg.highway.astype(str).isin(INCLUDE)].copy()
    if 'access' in seg: seg=seg[~seg.access.astype(str).str.lower().isin(['no','private'])]
    with rasterio.open(DEM) as dem:
        dem_array=dem.read(1)
        rows=[]; adj={int(n):[] for n in nodes.osmid}; rev={int(n):[] for n in nodes.osmid}; node_coord={int(r.osmid):(r.geometry.x,r.geometry.y) for _,r in nodes.iterrows()}
        for _,e in seg.iterrows():
            u,v=int(e.node_a),int(e.node_b); length=float(e.length_m or e.geometry.length); speed,assumed=parse_speed(e.get('maxspeed'),str(e.highway)); minutes=length/1000/speed*60
            elev=sample_dem(e.geometry,dem,dem_array); oneway=str(e.get('oneway','')).lower()
            arcs=[(u,v)] if oneway in ('yes','1','true') else ([(v,u)] if oneway=='-1' else [(u,v),(v,u)])
            for x,y in arcs: adj.setdefault(x,[]).append((y,minutes)); rev.setdefault(y,[]).append((x,minutes))
            rows.append({'osmid':e.osmid,'node_a':u,'node_b':v,'highway':e.highway,'length_m':length,'speed_kmh':speed,'speed_assumed':assumed,'travel_time_min':minutes,'bridge':str(e.get('bridge','')).lower() in ('yes','true','1'),'tunnel':str(e.get('tunnel','')).lower() in ('yes','true','1'),'elev_min_m':elev[0],'elev_mean_m':elev[1],'elev_max_m':elev[2],'geometry':e.geometry})
    prof=gpd.GeoDataFrame(rows,geometry='geometry',crs=seg.crs)
    # Map categories using established OSM feature categories, then nearest graph node by projected distance.
    cat=fac.category.astype(str).str.lower(); destinations={k:[] for k in ('hospital','shelter','candidate_shelter')}; snap_dist={k:[] for k in ('hospital','shelter','candidate_shelter')}; snapped_counts={k:0 for k in destinations}; within500={k:0 for k in destinations}
    node_geom=nodes.geometry.to_list(); node_ids=nodes.osmid.astype(int).to_list(); tree=STRtree(node_geom)
    def nearest(p):
        # Spatial index avoids a facilities-by-all-nodes distance scan.
        i=int(tree.nearest(p)); return node_ids[i],p.distance(node_geom[i])
    for i,row in fac.iterrows():
        c=str(row.category).lower(); typ=str(row.get('source_type','')).lower()
        if 'hospital' in c: k='hospital'
        elif 'shelter' in c: k='shelter'
        elif any(x in c for x in ('school','college')): k='candidate_shelter'
        else: continue
        n,d=nearest(row.geometry); snap_dist[k].append(float(d));
        if n in adj: destinations[k].append(n); snapped_counts[k]+=1; within500[k]+=d<=500
    # Include candidate shelters as separate reported set; main shelter set is OSM shelters only.
    hospital_rev=dijkstra(rev,destinations['hospital']); shelter_rev=dijkstra(rev,destinations['shelter'])
    rng=random.Random(a.seed); origin_ids=rng.sample(node_ids,min(a.origins,len(node_ids)))
    ht=[hospital_rev.get(n) for n in origin_ids]; st=[shelter_rev.get(n) for n in origin_ids]
    reachable=[x for x in ht if x is not None]; rs=[x for x in st if x is not None]
    stats={'input_segments':int(len(seg)),'profiled_edges':int(len(rows)),'included_highway_classes':sorted(INCLUDE),'excluded_classes_note':'All other classes, including footway, path, pedestrian, steps, cycleway, bridleway and track, plus access=no/private.','default_speed_kmh_assumptions':SPEED,'assumed_speed_edge_count':sum(r['speed_assumed'] for r in rows),'oneway_arcs':sum(len(v) for v in adj.values()),'facility_counts_snapped_to_graph_node':snapped_counts,'facility_within_500m_of_road_node':within500,'snap_distance_m':{k:({'min':min(v),'median':float(np.median(v)),'p90':float(np.percentile(v,90)),'max':max(v)} if v else None) for k,v in snap_dist.items()},'origins_requested':a.origins,'origins_sampled':len(origin_ids),'hospital_travel_time_min':{'reachable':len(reachable),'median':float(np.median(reachable)) if reachable else None,'p90':float(np.percentile(reachable,90)) if reachable else None,'within_30_min_share_all_origins':sum(x is not None and x<=30 for x in ht)/len(ht) if ht else None,'unreachable':sum(x is None for x in ht)},'shelter_travel_time_min':{'reachable':len(rs),'median':float(np.median(rs)) if rs else None,'p90':float(np.percentile(rs,90)) if rs else None,'unreachable':sum(x is None for x in st)},'cleaned_dem_sample_method':'edge vertices and interpolated points at intervals no greater than 30 m','flood_passability':'blocked when predicted depth >= threshold; threshold 0.3 m is an assumption to confirm from literature; function defined but not applied to flood data'}
    stage=TARGET.parent/f'.routing_build_{uuid.uuid4().hex}'; stage.mkdir(); prof.to_file(stage/'vehicle_edges.gpkg',layer='vehicle_edges',driver='GPKG'); (stage/'routing_metrics.json').write_text(json.dumps(stats,indent=2)+'\n',encoding='utf-8'); stage.rename(TARGET)
    lines=['# Routing profile — Phase 4 Part 1','','This is a planning and baseline profile. The graph uses assumed default speeds when maxspeed is absent; it does not include flood closures.','','## Graph definition','',f"Included highway classes: {', '.join(sorted(INCLUDE))}.",'Excluded: every other class (including footway, path, pedestrian, steps, cycleway, bridleway and track), and roads tagged access=no/private.',f"Default speed assumptions (km/h): {json.dumps(SPEED,sort_keys=True)}. Missing or unparsable maxspeed uses these assumptions.",'','Per edge fields include length, travel time, bridge/tunnel flags and cleaned-DEM minimum/mean/maximum sampled at vertices and <=30 m intervals.','','## Facilities and routing','',f"Snapped facilities: {json.dumps(snapped_counts)}. Facilities within 500 m of a road node: {json.dumps(within500)}.",f"Snap distance summaries (m): {json.dumps(stats['snap_distance_m'],sort_keys=True)}.",f"200-origin hospital routes: {json.dumps(stats['hospital_travel_time_min'],sort_keys=True)}.",f"200-origin shelter routes: {json.dumps(stats['shelter_travel_time_min'],sort_keys=True)}.",'Schools and colleges are reported separately as candidate shelters, an assumption; they are not counted as actual shelters. Unreachable origins can reflect one-way directionality, disconnected components, no snapped destination, or missing graph links; this script does not distinguish all causes individually.', 'Flood passability function is defined but not run on observed or predicted flood data. It marks an edge blocked at predicted depth >=0.3 m; that threshold is an assumption to confirm from literature.', '', 'Outputs: `data/processed/routing/vehicle_edges.gpkg` and `routing_metrics.json`.']
    REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
if __name__=='__main__': main()
