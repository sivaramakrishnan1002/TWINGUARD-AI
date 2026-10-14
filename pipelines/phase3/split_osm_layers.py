#!/usr/bin/env python
"""Organize the extracted OSM GeoPackage layers into standard feature folders."""
from pathlib import Path
import shutil
import geopandas as gpd

ROOT=Path(__file__).resolve().parents[2]; SOURCE=ROOT/'data/features/osm/chennai_osm_features.gpkg'
TARGETS={
 'roads/chennai_road_graph.gpkg':['road_segments','directed_road_arcs','road_nodes'],
 'facilities/chennai_facilities.gpkg':['facilities'],
 'buildings/chennai_building_footprints.gpkg':['building_footprints'],
 'hydrology/chennai_waterways.gpkg':['waterways'],
}
def main():
    if not SOURCE.exists():raise FileNotFoundError(f'OSM source GeoPackage missing: {SOURCE}')
    for rel,layers in TARGETS.items():
        dest=ROOT/'data/features'/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():raise FileExistsError(f'Refusing to overwrite existing derived feature output: {dest}')
        for i,layer in enumerate(layers):
            frame=gpd.read_file(SOURCE,layer=layer)
            mode='w' if i==0 else 'a'
            frame.to_file(dest,layer=layer,driver='GPKG',engine='pyogrio',mode=mode)
    print('Created separate roads, facilities, buildings, and hydrology GeoPackages from the local OSM extraction.')
if __name__=='__main__':main()
