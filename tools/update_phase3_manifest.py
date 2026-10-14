"""Refresh the derived Phase 3 output rows in docs/DATA_MANIFEST.csv."""
from __future__ import annotations
import csv,hashlib
from pathlib import Path
import rasterio

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'docs/DATA_MANIFEST.csv'
DIRS=[ROOT/'data/processed/grid',ROOT/'data/processed/labels_inspection',ROOT/'data/processed/exposure',ROOT/'data/features']
FIELDS=['dataset','category','source name','source URL','retrieval date','time period covered','spatial resolution','temporal resolution','CRS','coverage of CMA','size','licence','status','filename','sha256','verification']
def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()
def main():
    with MANIFEST.open('r',encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f); rows=list(reader)
    rows=[r for r in rows if r.get('category')!='phase3_derived']
    derived=[]
    for folder in DIRS:
        if not folder.exists():continue
        for p in sorted(x for x in folder.rglob('*') if x.is_file() and x.suffix.lower() in ('.tif','.gpkg','.csv','.json')):
            relative=p.relative_to(ROOT).as_posix(); crs='not applicable'
            if p.suffix.lower() in ('.tif','.gpkg'):
                try:
                    with rasterio.open(p) as ds: crs=ds.crs.to_string() if ds.crs else 'not set'
                except rasterio.errors.RasterioIOError:crs='EPSG:32644; GeoPackage vector'
            derived.append({'dataset':f"Phase 3 derived: {p.name}",'category':'phase3_derived','source name':'TwinGuard Phase 3 pipeline; see docs/FEATURE_DICTIONARY.md','source URL':'','retrieval date':'2026-10-14 (derived output)','time period covered':'See docs/FEATURE_DICTIONARY.md','spatial resolution':'30 m grid' if p.suffix.lower()=='.tif' else 'Vector/table; see feature dictionary','temporal resolution':'See docs/FEATURE_DICTIONARY.md','CRS':crs,'coverage of CMA':'CMA and 2 km context grid; statistics are CMA-only','size':str(p.stat().st_size),'licence':'Derived; upstream source licence/attribution applies; no new licence asserted','status':'derived','filename':relative,'sha256':sha(p),'verification':'See docs/PHASE3_LOG.md and docs/PHASE3_VALIDATION.json'})
    rows.extend(derived)
    with MANIFEST.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    print(f'Preserved {len(rows)-len(derived)} source rows; refreshed {len(derived)} derived Phase 3 rows.')
if __name__=='__main__':main()
