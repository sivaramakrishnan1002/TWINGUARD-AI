#!/usr/bin/env python
"""Extract local roads, amenities, buildings and waterways from the immutable PBF."""
from __future__ import annotations
import json, math
from collections import defaultdict
from pathlib import Path
import geopandas as gpd
import numpy as np
import osmium
import rasterio
from shapely.geometry import LineString,Point,Polygon
from shapely.ops import transform as geom_transform
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[2]; RAW=ROOT/'data/raw'; OUT=ROOT/'data/features/osm'; GRID=ROOT/'data/processed/grid/grid_definition.json'
PBF=RAW/'roads/southern-zone-latest.osm.pbf'
ROAD_CLASSES={'motorway','motorway_link','trunk','trunk_link','primary','primary_link','secondary','secondary_link','tertiary','tertiary_link','unclassified','residential','living_street','service','road','track','path','footway','cycleway','pedestrian','bridleway','steps'}
FACILITY_TAGS={'amenity','emergency','healthcare','shop','tourism','public_transport','social_facility'}
TARGET_WATER_NAMES={'adyar','adyar river','cooum','cooum river','kosasthalaiyar','kosasthalaiyar river','buckingham canal','otteri nala'}

def main():
    existing=OUT/'chennai_osm_features.gpkg'
    if existing.exists():
        raise FileExistsError(f'Refusing to rescan PBF or overwrite existing OSM GeoPackage: {existing}. Use the existing-file summary tools instead.')
    grid=json.loads(GRID.read_text()); boundary=gpd.read_file(RAW/'boundary/chennai_cma_boundary.geojson').to_crs(32644)
    buffered=boundary.geometry.union_all().buffer(2000); buffer4326=gpd.GeoSeries([buffered],crs=32644).to_crs(4326).iloc[0]
    xmin,ymin,xmax,ymax=buffer4326.bounds; margin=.08; bbox=(xmin-margin,ymin-margin,xmax+margin,ymax+margin)
    to_utm=Transformer.from_crs(4326,32644,always_xy=True).transform
    node_xy={}; node_fac=[]; edges=[]; buildings=[]; facilities=[]; waterways=[]; counts=defaultdict(int)
    class Extract(osmium.SimpleHandler):
        def __init__(self):
            super().__init__(); self.n_total=0; self.w_total=0
        def node(self,n):
            self.n_total+=1
            if self.n_total%10000000==0: print(f'PBF nodes scanned: {self.n_total:,}',flush=True)
            if not n.location.valid(): return
            x,y=n.location.lon,n.location.lat
            if bbox[0]<=x<=bbox[2] and bbox[1]<=y<=bbox[3]:
                node_xy[n.id]=(x,y); counts['local_nodes_seen']+=1
                tags={t.k:t.v for t in n.tags}
                if any(k in tags for k in FACILITY_TAGS): node_fac.append((n.id,x,y,tags))
        def way(self,w):
            self.w_total+=1
            if self.w_total%1000000==0: print(f'PBF ways scanned: {self.w_total:,}',flush=True)
            tags={t.k:t.v for t in w.tags}
            has_road=tags.get('highway') in ROAD_CLASSES
            has_building=bool(tags.get('building'))
            has_water=tags.get('waterway') in ('river','stream','canal','drain','ditch','riverbank','tidal_channel')
            has_facility=any(k in tags for k in FACILITY_TAGS)
            if not (has_road or has_building or has_water or has_facility): return
            nodes=[(n.ref,node_xy.get(n.ref)) for n in w.nodes]
            runs=[]; run=[]
            for node in nodes:
                if node[1] is None:
                    if len(run)>1:runs.append(run)
                    run=[]
                else:run.append(node)
            if len(run)>1:runs.append(run)
            if has_road:
                for run in runs:
                    for (id_a,a),(id_b,b) in zip(run,run[1:]):
                        line=LineString([a,b]); projected=geom_transform(to_utm,line)
                        if not projected.intersects(buffered): continue
                        inter=projected.intersection(buffered)
                        if inter.is_empty:continue
                        parts=[inter] if inter.geom_type=='LineString' else [g for g in getattr(inter,'geoms',[]) if g.geom_type=='LineString']
                        for part in parts:
                            if part.length<=0:continue
                            # Keep OSM segment endpoint IDs/geometry; clip is for study extent only.
                            oneway=tags.get('oneway','no')
                            item={'osmid':int(w.id),'node_a':int(id_a),'node_b':int(id_b),'highway':tags.get('highway'),'name':tags.get('name'),'oneway':oneway,'access':tags.get('access'),'bridge':tags.get('bridge'),'tunnel':tags.get('tunnel'),'maxspeed':tags.get('maxspeed'),'length_m':float(part.length),'geometry':part}
                            edges.append(item); counts['road_segments']+=1
            coords=[n[1] for n in nodes]
            if has_building and len(coords)>=4 and coords[0] and coords[-1] and coords[0]==coords[-1]:
                try:
                    poly=Polygon(coords)
                    if poly.is_valid and geom_transform(to_utm,poly).intersects(buffered):
                        cp=geom_transform(to_utm,poly).intersection(buffered)
                        if cp.geom_type in ('Polygon','MultiPolygon') and not cp.is_empty:
                            buildings.append({'osmid':int(w.id),'building':tags.get('building'),'name':tags.get('name'),'levels':tags.get('building:levels'),'geometry':cp,'area_m2':float(cp.area)})
                except Exception:counts['invalid_buildings']+=1
            if has_water:
                for run in runs:
                    if len(run)<2:continue
                    geom=geom_transform(to_utm,LineString([node[1] for node in run]))
                    if geom.intersects(buffered):
                        clip=geom.intersection(buffered)
                        if clip.geom_type=='LineString':
                            name=tags.get('name') or tags.get('name:en') or tags.get('alt_name')
                            waterways.append({'osmid':int(w.id),'waterway':tags.get('waterway'),'name':name,'exact_target_name_match':bool(name and name.strip().casefold() in TARGET_WATER_NAMES),'geometry':clip})
            if has_facility and len(coords)>=4 and coords[0] and coords[-1] and coords[0]==coords[-1]:
                try:
                    pp=Polygon(coords); pt=geom_transform(to_utm,pp).representative_point()
                    if buffered.covers(pt): facilities.append({'osmid':int(w.id),'source_type':'way','category':next((tags[k] for k in FACILITY_TAGS if k in tags),''),'name':tags.get('name'),'geometry':pt})
                except Exception:counts['invalid_facilities']+=1
    handler=Extract(); handler.apply_file(str(PBF),locations=False)
    counts['indexed_local_node_coordinates']=len(node_xy)
    for oid,x,y,tags in node_fac:
        point=geom_transform(to_utm,Point(x,y))
        if buffered.covers(point): facilities.append({'osmid':int(oid),'source_type':'node','category':next((tags[k] for k in FACILITY_TAGS if k in tags),''),'name':tags.get('name'),'geometry':point})
    edge=gpd.GeoDataFrame(edges,geometry='geometry',crs=32644) if edges else gpd.GeoDataFrame(columns=['osmid','node_a','node_b','highway','geometry'],crs=32644)
    if edge.empty: raise RuntimeError('No road segments extracted; check pyosmium node ordering/location coverage')
    # Expand into directed arcs. A direction of -1 reverses the stored geometry.
    arcs=[]
    for row in edge.itertuples():
        if str(row.oneway).lower() in ('yes','1','true'):
            arcs.append({'osmid':row.osmid,'from_node':row.node_a,'to_node':row.node_b,'direction':'forward','geometry':row.geometry})
        elif str(row.oneway)=='-1':
            arcs.append({'osmid':row.osmid,'from_node':row.node_b,'to_node':row.node_a,'direction':'reverse','geometry':LineString(list(row.geometry.coords)[::-1])})
        else:
            arcs.extend([{'osmid':row.osmid,'from_node':row.node_a,'to_node':row.node_b,'direction':'forward','geometry':row.geometry},{'osmid':row.osmid,'from_node':row.node_b,'to_node':row.node_a,'direction':'reverse','geometry':LineString(list(row.geometry.coords)[::-1])}])
    arc=gpd.GeoDataFrame(arcs,geometry='geometry',crs=32644)
    # Weakly connected components via union-find; SCC via iterative Kosaraju.
    parent={}; rank={}
    def find(x):
        parent.setdefault(x,x)
        while parent[x]!=x: parent[x]=parent[parent[x]];x=parent[x]
        return x
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra==rb:return
        if rank.get(ra,0)<rank.get(rb,0):ra,rb=rb,ra
        parent[rb]=ra
        if rank.get(ra,0)==rank.get(rb,0):rank[ra]=rank.get(ra,0)+1
    adj=defaultdict(list); rev=defaultdict(list); edge_lengths=defaultdict(float)
    for r in arcs:
        a,b=r['from_node'],r['to_node']; union(a,b); adj[a].append(b); rev[b].append(a); edge_lengths[(a,b)]+=r['geometry'].length
    comps=defaultdict(list)
    for n in parent:comps[find(n)].append(n)
    largest_weak=max(comps.values(),key=len) if comps else []
    seen=set(); order=[]
    for root in parent:
        if root in seen:continue
        seen.add(root); stack=[(root,iter(adj.get(root,[])))]
        while stack:
            v,nbrs=stack[-1]
            try:u=next(nbrs)
            except StopIteration:order.append(v);stack.pop();continue
            if u not in seen:seen.add(u);stack.append((u,iter(adj.get(u,[]))))
    seen.clear(); largest_scc=[]
    for root in reversed(order):
        if root in seen:continue
        comp=[]; stack=[root];seen.add(root)
        while stack:
            v=stack.pop();comp.append(v)
            for u in rev.get(v,[]):
                if u not in seen:seen.add(u);stack.append(u)
        if len(comp)>len(largest_scc):largest_scc=comp
    total_len=float(edge.length_m.sum()); weak_len=float(edge.loc[edge.node_a.map(find)==find(largest_weak[0]),'length_m'].sum()) if largest_weak else 0
    sccset=set(largest_scc); scc_len=float(edge.loc[edge.node_a.isin(sccset)&edge.node_b.isin(sccset),'length_m'].sum())
    counts.update({'road_nodes':len(parent),'directed_arcs':len(arcs),'weak_component_count':len(comps),'largest_weak_component_nodes':len(largest_weak),'largest_weak_component_length_share':weak_len/total_len if total_len else 0,'largest_strong_component_nodes':len(largest_scc),'largest_strong_component_length_share':scc_len/total_len if total_len else 0,'road_length_m':total_len})
    # Intersections/vertices as nodes; sample DEM elevation at local OSM node coordinates.
    node_rows=[]; elevpath=ROOT/'data/features/terrain/elevation_m.tif'
    if elevpath.exists(): elev=rasterio.open(elevpath); sampler=elev.sample
    else: sampler=None
    sample_pts=[]
    for nid in parent:
        xy=node_xy.get(nid)
        if xy: sample_pts.append((nid,geom_transform(to_utm,Point(xy))))
    if sampler:
        coords=[(p.x,p.y) for _,p in sample_pts]; vals=[float(v[0]) for v in sampler(coords)]
    else: vals=[float('nan')]*len(sample_pts)
    deg=defaultdict(int)
    for a,b in ((x['from_node'],x['to_node']) for x in arcs):deg[a]+=1;deg[b]+=1
    for (nid,pt),z in zip(sample_pts,vals):node_rows.append({'osmid':int(nid),'directed_degree':int(deg[nid]),'dem_elevation_m':z,'geometry':pt})
    node_gdf=gpd.GeoDataFrame(node_rows,geometry='geometry',crs=32644)
    fac=gpd.GeoDataFrame(facilities,geometry='geometry',crs=32644).drop_duplicates(['osmid','source_type']) if facilities else gpd.GeoDataFrame(columns=['osmid','geometry'],crs=32644)
    if not fac.empty:
        from shapely import STRtree
        tree=STRtree(edge.geometry.values); nearest=[]
        for p in fac.geometry:
            idx=tree.nearest(p); nearest.append(float(p.distance(edge.geometry.iloc[int(idx)])))
        fac['nearest_road_distance_m']=nearest
    bld=gpd.GeoDataFrame(buildings,geometry='geometry',crs=32644) if buildings else gpd.GeoDataFrame(columns=['osmid','area_m2','geometry'],crs=32644)
    water=gpd.GeoDataFrame(waterways,geometry='geometry',crs=32644) if waterways else gpd.GeoDataFrame(columns=['osmid','waterway','name','geometry'],crs=32644)
    OUT.mkdir(parents=True,exist_ok=True); gpkg=OUT/'chennai_osm_features.gpkg'
    if gpkg.exists(): raise FileExistsError(f'Refusing to overwrite existing OSM GeoPackage: {gpkg}')
    for gdf,layer in [(edge,'road_segments'),(arc,'directed_road_arcs'),(node_gdf,'road_nodes'),(fac,'facilities'),(bld,'building_footprints'),(water,'waterways')]:
        if not gdf.empty:gdf.to_file(gpkg,layer=layer,driver='GPKG',engine='pyogrio')
    # Built-up proxy agreement: presence of an OSM building centroid by 30 m cell vs WorldCover class 50.
    corr=None; built_count=0
    if not bld.empty:
        with rasterio.open(ROOT/'data/features/landcover/worldcover_2021_class.tif') as src:
            wc=src.read(1); centers=[]
            rr,cc=np.where((wc==50)&(wc!=src.nodata)); built_count=len(rr)
            # OSM polygons rasterized to 30 m cell presence.
            from rasterio.features import rasterize
            bmask=rasterize(((g,1) for g in bld.geometry),out_shape=wc.shape,transform=src.transform,fill=0,dtype='uint8',all_touched=False)
            cma=rasterio.open(ROOT/'data/processed/grid/cma_mask.tif').read(1)==1
            valid=cma & (wc!=src.nodata); x=(wc[valid]==50).astype(float); y=bmask[valid].astype(float)
            corr=float(np.corrcoef(x,y)[0,1]) if len(x)>1 and x.std()>0 and y.std()>0 else None
            write_corr={'worldcover_built_cells':built_count,'osm_building_cells':int(y.sum()),'pearson_binary_presence_r':corr,'caveat':'association only; OSM footprint completeness and class/cell support differ'}
    else: write_corr={'warning':'No local OSM building footprints extracted; correlation unavailable.'}
    water_summary={}
    if not water.empty:
        for name,group in water[water.exact_target_name_match].groupby('name'):
            water_summary[str(name)]={'segments':int(len(group)),'length_km':float(group.geometry.length.sum()/1000)}
    (OUT/'osm_graph_summary.json').write_text(json.dumps({'counts':dict(counts),'builtup_comparison':write_corr,'named_target_waterways':water_summary,'extent':'CMA polygon plus 2 km; OSM local data filtered from Southern Zone extract','graph_method':'custom directed adjacency and Kosaraju SCC (NetworkX unavailable); largest component shares use segment length','note':'Road ways with missing local node locations may be omitted or split; review the buffered boundary and compare object counts with docs/OSM_COUNTS.md.'},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'counts':dict(counts),'builtup_comparison':write_corr,'gpkg_bytes':gpkg.stat().st_size},indent=2))

if __name__=='__main__': main()
