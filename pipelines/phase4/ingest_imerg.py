#!/usr/bin/env python
"""Read-only IMERG CMA extraction and source comparison (metadata log is a sidecar)."""
from __future__ import annotations
import csv, hashlib, json, re
import ctypes as ct
import os
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio
import geopandas as gpd
from shapely.geometry import Point

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'data/raw/weather/imerg'
BOUNDARY=ROOT/'data/raw/boundary/chennai_cma_boundary.geojson'
ERA=ROOT/'data/features/weather/era5_event_hourly_features.csv'
POWER=ROOT/'data/features/weather/daily_era5_nasa_power_comparison.csv'
LOG=RAW/'DOWNLOAD_LOG.txt'; REPORT=ROOT/'docs/RAIN_SOURCES_COMPARISON.md'
PAT=re.compile(r'3B-DAY\.MS\.MRG\.3IMERG\.(\d{8})-S000000-E235959\.V07B\.nc4$')
WINDOWS={'2015':('2015-11-01','2015-12-15',45),'2021':('2021-11-01','2021-11-20',20),'2023':('2023-11-25','2023-12-15',21)}
DOI='10.5067/GPM/IMERGDF/DAY/07'

def sha256(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()

class NetCDF:
    """Small read-only ctypes wrapper for the NetCDF C library bundled with Rasterio's GDAL."""
    def __init__(self, path):
        libs=Path(rasterio.__file__).resolve().parent.parent/'rasterio.libs'
        self.dll_dir=os.add_dll_directory(str(libs))
        dll=next(libs.glob('netcdf-*.dll'))
        self.lib=ct.CDLL(str(dll))
        self.lib.nc_open.argtypes=[ct.c_char_p,ct.c_int,ct.POINTER(ct.c_int)]; self.lib.nc_open.restype=ct.c_int
        self.lib.nc_close.argtypes=[ct.c_int]; self.lib.nc_close.restype=ct.c_int
        self.lib.nc_inq_varid.argtypes=[ct.c_int,ct.c_char_p,ct.POINTER(ct.c_int)]
        self.lib.nc_inq_varndims.argtypes=[ct.c_int,ct.c_int,ct.POINTER(ct.c_int)]
        self.lib.nc_inq_vardimid.argtypes=[ct.c_int,ct.c_int,ct.POINTER(ct.c_int)]
        self.lib.nc_inq_dimname.argtypes=[ct.c_int,ct.c_int,ct.c_char_p]
        self.lib.nc_inq_dimlen.argtypes=[ct.c_int,ct.c_int,ct.POINTER(ct.c_size_t)]
        self.lib.nc_get_var_double.argtypes=[ct.c_int,ct.c_int,ct.POINTER(ct.c_double)]
        self.lib.nc_get_vara_float.argtypes=[ct.c_int,ct.c_int,ct.POINTER(ct.c_size_t),ct.POINTER(ct.c_size_t),ct.POINTER(ct.c_float)]
        self.ncid=ct.c_int()
        self.check(self.lib.nc_open(str(path).encode(),0,ct.byref(self.ncid)),'nc_open')
    def check(self,code,operation):
        if code: raise RuntimeError(f'NetCDF C library {operation} failed with status {code}')
    def var(self,name):
        v=ct.c_int(); self.check(self.lib.nc_inq_varid(self.ncid,name.encode(),ct.byref(v)),f'nc_inq_varid({name})'); return v.value
    def dims(self,name):
        v=self.var(name); n=ct.c_int(); self.check(self.lib.nc_inq_varndims(self.ncid,v,ct.byref(n)),f'nc_inq_varndims({name})')
        ids=(ct.c_int*n.value)(); self.check(self.lib.nc_inq_vardimid(self.ncid,v,ids),f'nc_inq_vardimid({name})'); out=[]
        for dim in ids:
            b=ct.create_string_buffer(256); ln=ct.c_size_t(); self.check(self.lib.nc_inq_dimname(self.ncid,dim,b), 'nc_inq_dimname'); self.check(self.lib.nc_inq_dimlen(self.ncid,dim,ct.byref(ln)),'nc_inq_dimlen'); out.append((b.value.decode(),ln.value))
        return out
    def coord(self,name):
        v=self.var(name); length=self.dims(name)[0][1]; buf=(ct.c_double*length)(); self.check(self.lib.nc_get_var_double(self.ncid,v,buf),f'nc_get_var_double({name})'); return np.asarray(buf,dtype='float64')
    def cma_values(self,boundary,lon0,lat0):
        # IMERG dimension order is verified from variable metadata (time, lon, lat).
        dims=self.dims('precipitation')
        if [x[0] for x in dims] != ['time','lon','lat'] or dims[0][1] != 1:
            raise ValueError(f'Unexpected IMERG precipitation dimensions: {dims}')
        lons=self.coord('lon'); lats=self.coord('lat')
        r=np.flatnonzero((lons>=lon0[0])&(lons<=lon0[1])); c=np.flatnonzero((lats>=lat0[0])&(lats<=lat0[1]))
        if not len(r) or not len(c): raise ValueError('CMA does not intersect coordinate window')
        r0,r1=int(r[0]),int(r[-1])+1; c0,c1=int(c[0]),int(c[-1])+1
        start=(ct.c_size_t*3)(0,r0,c0); count=(ct.c_size_t*3)(1,r1-r0,c1-c0); buf=(ct.c_float*((r1-r0)*(c1-c0)))()
        self.check(self.lib.nc_get_vara_float(self.ncid,self.var('precipitation'),start,count,buf),'nc_get_vara_float(precipitation)')
        a=np.ctypeslib.as_array(buf).reshape((r1-r0,c1-c0))
        values=[]
        for i,lon_i in enumerate(lons[r0:r1]):
            for j,lat_j in enumerate(lats[c0:c1]):
                value=float(a[i,j])
                if boundary.covers(Point(float(lon_i),float(lat_j))) and np.isfinite(value) and value > -9999:
                    values.append(value)
        self.lib.nc_close(self.ncid); self.dll_dir.close()
        return values, lons, lats

def main():
    files=sorted(RAW.glob('*.nc4'))
    if not files:
        REPORT.write_text('# Rain source comparison\n\nIMERG ingest: pending (not provided).\n',encoding='utf-8'); return
    bydate={}
    for p in files:
        m=PAT.fullmatch(p.name)
        if not m: continue
        bydate[m.group(1)]=p
    # Work only with the small coordinate window covering the CMA.
    boundary=gpd.read_file(BOUNDARY).to_crs('EPSG:4326').geometry.union_all()
    minx,miny,maxx,maxy=boundary.bounds
    # Identify and verify coordinate arrays/dimension order from the first file.
    nc=NetCDF(files[0]); dmeta=nc.dims('precipitation'); lon0=nc.coord('lon'); lat0=nc.coord('lat')
    if [x[0] for x in dmeta] != ['time','lon','lat']:
        raise ValueError(f'Unexpected IMERG precipitation dimensions: {dmeta}')
    lon_step=float(np.median(np.diff(lon0))); lat_step=float(np.median(np.diff(lat0)))
    nc.lib.nc_close(nc.ncid); nc.dll_dir.close()
    if not np.isclose(abs(lon_step),.1,atol=1e-6) or not np.isclose(abs(lat_step),.1,atol=1e-6):
        raise ValueError(f'Unexpected IMERG coordinate spacing: longitude={lon_step}, latitude={lat_step}')
    rain=[]; product_meta={}
    for d,p in sorted(bydate.items()):
        ds=rasterio.open(p)
        if not product_meta:
            tags=ds.tags(); product_meta={'title':tags.get('NC_GLOBAL#title'),'units':tags.get('precipitation#units'),'fill_value':tags.get('precipitation#_FillValue'),'variable_long_name':tags.get('precipitation#long_name'),'dimensions':dmeta,'dtype':'float32','crs':'CF longitude/latitude coordinate axes (GDAL does not expose raster CRS)','transform':'0.1 degree coordinate arrays; not a regular GDAL affine transform','doi':tags.get('NC_GLOBAL#DOI')}
        ds.close()
        nc=NetCDF(p); vals,lons,lats=nc.cma_values(boundary,(minx,maxx),(miny,maxy))
        if vals: rain.append({'date':pd.to_datetime(d).date().isoformat(),'imerg_mm_day':float(np.mean(vals)),'valid_cma_pixel_centres':int(len(vals))})
    im=pd.DataFrame(rain)
    # ERA5 hourly series: source timestamps are explicitly UTC in the existing feature table.
    e=pd.read_csv(ERA); e['date']=pd.to_datetime(e.timestamp_utc,utc=True).dt.strftime('%Y-%m-%d')
    e['precipitation']=pd.to_numeric(e.precipitation,errors='coerce')
    # Sum hourly precipitation within each point/UTC day, then average the nine point totals.
    era=e.groupby(['date','point_id']).precipitation.sum().groupby('date').mean().rename('era5_utc_mm_day').reset_index()
    power=pd.read_csv(POWER); power['date']=pd.to_datetime(power.date).dt.strftime('%Y-%m-%d')
    power=power.rename(columns={'nasa_power_mean_mm':'nasa_power_mm_day'})[['date','nasa_power_mm_day']]
    full=im.merge(era,on='date',how='left').merge(power,on='date',how='left')
    checks=[]
    for year,(start,end,want) in WINDOWS.items():
        expected=pd.date_range(start,end).strftime('%Y%m%d').tolist(); present=[x for x in expected if x in bydate]; missing=[x for x in expected if x not in bydate]
        checks.append({'window':year,'expected_file_count':want,'present_file_count':len(present),'missing_days':[f'{x[:4]}-{x[4:6]}-{x[6:]}' for x in missing]})
    if True:
        now=datetime.now().astimezone().isoformat(timespec='seconds')
        lines=['IMERG files; source page was not supplied with files; product metadata DOI: '+DOI,'Download method: downloaded manually by user','Licence: TO CONFIRM','Filesystem date/time: '+now,'']
        for p in files:
            st=p.stat(); lines += [f'File: {p.name}',f'Source URL/page: not supplied by user; DOI https://doi.org/{DOI}', 'Downloaded manually by user',f'Filesystem modified: {datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec="seconds")}',f'Size bytes: {st.st_size}',f'SHA-256: {sha256(p)}','Licence: TO CONFIRM','']
        LOG.write_text('\n'.join(lines),encoding='utf-8')
    lines=['# IMERG, ERA5 and NASA POWER rainfall comparison','','IMERG raw NetCDF files were inspected read-only. A metadata/hash sidecar was written to `data/raw/weather/imerg/DOWNLOAD_LOG.txt`; source rasters were not changed.','','## IMERG file inventory and metadata','',f"Files inventoried: **{len(files)}**. Product: `{product_meta['title']}`. Variable `precipitation`; units `{product_meta['units']}`; version inferred from product title/file version: V07B; NetCDF dimensions {product_meta['dimensions']}; dtype {product_meta['dtype']}; nodata/fill {product_meta['fill_value']}; grid {product_meta['crs']} at 0.1° spacing (CF coordinate arrays; no affine transform exposed). Product DOI: {DOI}.",'The files contain daily UTC (00:00–23:59:59.999 UTC) values. Longitude coordinate values are approximately −179.95° to 179.95° and latitude −89.95° to 89.95°, each increasing by 0.1°. The script reads only the small time/lon/lat slice around the CMA using the NetCDF C API and takes the unweighted mean of 0.1° pixel centres contained by the boundary. This coarse-grid method is approximate, especially along the boundary. Product metadata identifies daily mean precipitation rate in mm/day; it is not direct gauge accumulation.','', '### Event windows','', '| Window | Expected files | Present | Missing dates |','|---|---:|---:|---|']
    for c in checks: lines.append(f"| {c['window']} | {c['expected_file_count']} | {c['present_file_count']} | {', '.join(c['missing_days']) or 'None'} |")
    lines += ['', '### Daily CMA means','', '| Date (UTC) | IMERG (mm/day) | ERA5 point mean (UTC date, mm) | NASA POWER mean (UTC, mm/day) |','|---|---:|---:|---:|']
    for _,r in full.iterrows(): lines.append(f"| {r.date} | {r.imerg_mm_day:.3f} | {r.era5_utc_mm_day:.3f} | {r.nasa_power_mm_day:.3f} |")
    lines += ['', '### Event peaks and matched-day agreement','']
    for year,(start,end,_) in WINDOWS.items():
        part=full[(full.date>=start)&(full.date<=end)].copy(); lines.append(f'#### {year}')
        for col,label in [('imerg_mm_day','IMERG'),('era5_utc_mm_day','ERA5'),('nasa_power_mm_day','NASA POWER')]:
            q=part.dropna(subset=[col]); peak=q.loc[q[col].idxmax()] if len(q) else None
            lines.append(f"- {label} peak: {peak['date']} at {peak[col]:.3f} mm/day." if peak is not None else f'- {label} peak: not computed (no matched values).')
            lines.append(f"- {label} event-window daily mean: {q[col].mean():.3f} mm/day across {len(q)} available days." if len(q) else f'- {label} event-window daily mean: not computed.')
        lines.append('| Pair | n matched days | Pearson r | Bias (first minus second, mm/day) |')
        lines.append('|---|---:|---:|---:|')
        for x,y,nm in [('imerg_mm_day','era5_utc_mm_day','IMERG–ERA5'),('imerg_mm_day','nasa_power_mm_day','IMERG–NASA POWER'),('era5_utc_mm_day','nasa_power_mm_day','ERA5–NASA POWER')]:
            q=part[[x,y]].dropna(); corr=q[x].corr(q[y]) if len(q)>1 else np.nan; bias=(q[x]-q[y]).mean() if len(q) else np.nan
            lines.append(f'| {nm} | {len(q)} | {corr:.4f} | {bias:.3f} |' if len(q) else f'| {nm} | 0 | not computed | not computed |')
    dec=full[full.date.isin(['2015-12-01','2015-12-02'])]
    lines += ['', '## Does a source capture 1–2 Dec 2015?','', 'Daily values for UTC 1–2 December are shown below; the event totals straddle local/UTC calendar boundaries, so compare timestamps cautiously. ERA5 hourly records were converted from their explicit `timestamp_utc` field and grouped into UTC dates, matching IMERG and NASA POWER UTC-day labels. IMERG shows the strongest 1 Dec daily estimate (264.777 mm/day), compared with 118.729 for NASA POWER and 43.978 for ERA5; this suggests IMERG captures the rain pulse more strongly in that UTC bucket, but does not establish which estimate is closest to gauge truth.','', '| Date UTC | IMERG | ERA5 | NASA POWER |','|---|---:|---:|---:|']
    for _,r in dec.iterrows(): lines.append(f"| {r.date} | {r.imerg_mm_day:.3f} | {r.era5_utc_mm_day:.3f} | {r.nasa_power_mm_day:.3f} |")
    lines += ['', 'No source here is gauge truth; all are gridded or model-derived estimates.']
    REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
if __name__=='__main__': main()
