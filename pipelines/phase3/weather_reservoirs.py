#!/usr/bin/env python
"""Prepare documented weather and reservoir tables from immutable raw inputs."""
import json, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]; RAW=ROOT/'data/raw'; FEAT=ROOT/'data/features'

def open_meteo():
    frames=[]
    for year in (2015,2021,2023):
        path=RAW/'weather'/f'open_meteo_era5_{year}_hourly.json'
        records=json.loads(path.read_text(encoding='utf-8'))
        for i,obj in enumerate(records,1):
            hourly=obj['hourly']; n=len(hourly['time'])
            frame=pd.DataFrame({k:v for k,v in hourly.items()})
            frame['point_id']=f'era5_{i:02d}'; frame['source']='Open-Meteo ERA5'; frame['source_timezone']=obj.get('timezone','unknown')
            local=pd.to_datetime(frame.pop('time'),errors='coerce').dt.tz_localize(obj.get('timezone','UTC'),ambiguous='NaT',nonexistent='NaT')
            frame['timestamp_local']=local.astype(str); frame['timestamp_utc']=local.dt.tz_convert('UTC').astype(str)
            frame['grid_latitude']=obj.get('latitude'); frame['grid_longitude']=obj.get('longitude')
            if len(frame)!=n: raise ValueError(f'Hourly column length mismatch: {path}')
            frame=frame.sort_values('timestamp_utc')
            rain=pd.to_numeric(frame['precipitation'],errors='coerce')
            for hours in (1,3,6,12,24,48,72,168):
                frame[f'rain_mm_roll_{hours}h']=rain.rolling(hours,min_periods=hours).sum()
            frame['rain_mm_max_1h']=frame['rain_mm_roll_1h']
            frame['rain_mm_max_3h']=frame['rain_mm_roll_3h']
            frames.append(frame)
    out=pd.concat(frames,ignore_index=True)
    dest=FEAT/'weather'; dest.mkdir(parents=True,exist_ok=True)
    # Parquet output requested in plan, but pyarrow/fastparquet are not installed; do not install packages or fake format.
    out.to_csv(dest/'era5_event_hourly_features.csv',index=False)
    peaks={}
    out['event_year']=out.timestamp_utc.str[:4]
    for year,frame in out.groupby('event_year'):
        peaks[year]={}
        for field in ('rain_mm_roll_1h','rain_mm_roll_3h','rain_mm_roll_24h'):
            ix=frame[field].idxmax()
            if pd.notna(ix):
                row=out.loc[ix]
                peaks[year][field]={'maximum_mm':float(row[field]),'point_id':row.point_id,'timestamp_utc':row.timestamp_utc,'timestamp_local':row.timestamp_local}
    (dest/'event_peak_rainfall.json').write_text(json.dumps(peaks,indent=2)+'\n',encoding='utf-8')
    baseline=[]
    recs=json.loads((RAW/'weather'/'open_meteo_era5_2015-2023_daily_baseline.json').read_text(encoding='utf-8'))
    for i,obj in enumerate(recs,1):
        for t,val in zip(obj['daily']['time'],obj['daily']['precipitation_sum']): baseline.append({'date':t,'point_id':f'era5_{i:02d}','precipitation_mm':val})
    era=pd.DataFrame(baseline).groupby('date',as_index=False).precipitation_mm.mean().rename(columns={'precipitation_mm':'era5_mean_mm'})
    nasa=[]
    for p in sorted((RAW/'weather').glob('nasa_power_daily_point_*.json')):
        obj=json.loads(p.read_text(encoding='utf-8')); coords=obj['geometry']['coordinates']; props=obj['properties']['parameter']
        precip=props.get('PRECTOTCORR',{})
        for d,val in precip.items():
            nasa.append({'date':f'{d[:4]}-{d[4:6]}-{d[6:]}','point_id':p.stem.split('_')[4], 'precipitation_mm':val if isinstance(val,(int,float)) and val>=0 else np.nan,'longitude':coords[0],'latitude':coords[1]})
    ns=pd.DataFrame(nasa).groupby('date',as_index=False).precipitation_mm.mean().rename(columns={'precipitation_mm':'nasa_power_mean_mm'})
    comp=era.merge(ns,on='date',how='inner').dropna(); comp.to_csv(dest/'daily_era5_nasa_power_comparison.csv',index=False)
    if len(comp)>1:
        x=comp.era5_mean_mm.astype(float); y=comp.nasa_power_mean_mm.astype(float)
        corr=float(x.corr(y)); bias=float((x-y).mean()); rmse=float(np.sqrt(((x-y)**2).mean()))
    else: corr=bias=rmse=None
    metrics={'matched_days':int(len(comp)),'pearson_r':corr,'mean_bias_era5_minus_nasa_mm_day':bias,'rmse_mm_day':rmse,'comparison':'daily 9-point spatial means; ERA5 reanalysis and NASA POWER model estimates are not gauge truth','units_note':'ERA5 precipitation field reported in mm; NASA PRECTOTCORR treated as mm/day per NASA POWER variable definition; verify raw metadata before publication.'}
    (dest/'daily_source_comparison.json').write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf-8')
    gaps=0
    for year,frame in out.assign(event_year=out.timestamp_utc.str[:4]).groupby('event_year'):
        for _,series in frame.groupby('point_id'):
            gaps += int(pd.to_datetime(series.timestamp_utc).diff().dropna().dt.total_seconds().ne(3600).sum())
    return {'hourly_rows':int(len(out)),'within_event_hourly_gaps':gaps,'event_peak_rainfall':peaks,'rows_daily_comparison':int(len(comp)),**metrics}

def reservoir():
    dest=FEAT/'reservoirs'; dest.mkdir(parents=True,exist_ok=True)
    zpath=RAW/'reservoirs'/'kaggle_chennai_water_management'/'archive.zip'
    with zipfile.ZipFile(zpath) as z:
        daily=pd.read_csv(z.open('chennai_reservoir_levels.csv'))
        rain=pd.read_csv(z.open('chennai_reservoir_rainfall.csv'))
    daily['date']=pd.to_datetime(daily['Date'],format='%d-%m-%Y',errors='coerce')
    cols=[c for c in daily.columns if c not in ('Date','date')]
    tidy=daily.melt(id_vars=['date'],value_vars=cols,var_name='reservoir',value_name='storage_mcft')
    tidy['storage_mcft']=pd.to_numeric(tidy.storage_mcft,errors='coerce')
    tidy=tidy.sort_values(['reservoir','date']); g=tidy.groupby('reservoir',group_keys=False)
    tidy['storage_change_mcft']=g.storage_mcft.diff(); tidy['change_3day_mcft']=g.storage_mcft.diff(3); tidy['change_7day_mcft']=g.storage_mcft.diff(7)
    tidy['days_since_storage_increase']=np.nan
    for _,idx in tidy.groupby('reservoir').groups.items():
        days=0; vals=[]
        for change in tidy.loc[idx,'storage_change_mcft']:
            days=0 if pd.notna(change) and change>0 else days+1; vals.append(days)
        tidy.loc[idx,'days_since_storage_increase']=vals
    capacity_reference={'POONDI':3231.0,'CHOLAVARAM':1081.0,'REDHILLS':3300.0,'CHEMBARAMBAKKAM':3645.0}
    tidy['capacity_mcft']=tidy.reservoir.map(capacity_reference)
    tidy['capacity_percent']=tidy.storage_mcft/tidy.capacity_mcft*100
    tidy['capacity_note']='percent uses present-day published capacity, not independently verified historical capacity'
    tidy.to_csv(dest/'kaggle_daily_storage_features.csv',index=False)
    manifest=pd.read_csv(ROOT/'docs'/'DATA_MANIFEST.csv',encoding='utf-8-sig')
    lake_names={Path(str(row['filename'])).name:str(row['dataset']).replace('OpenCity lake storage — ','') for _,row in manifest.iterrows() if str(row.get('filename','')).startswith('reservoirs/opencity_lake_levels/')}
    monthly=[]
    for p in sorted((RAW/'reservoirs'/'opencity_lake_levels').glob('*.csv')):
        df=pd.read_csv(p); monthcols=[c for c in df.columns if c.lower().startswith(('jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'))]
        for _,row in df.iterrows():
            for month,col in enumerate(monthcols,1): monthly.append({'reservoir':lake_names.get(p.name,'unmapped'),'source_file':p.name,'year':row.get('Year'),'month':month,'date':f"{int(row['Year']):04d}-{month:02d}-01",'storage_mcft':pd.to_numeric(row[col],errors='coerce')})
    m=pd.DataFrame(monthly); m.to_csv(dest/'opencity_monthly_storage_tidy.csv',index=False)
    # A transparent illustrative storage/rain rule, not a validated warning model.
    capacities={'POONDI':3231.0,'CHOLAVARAM':1081.0,'REDHILLS':3300.0,'CHEMBARAMBAKKAM':3645.0}
    source='https://beta-tnsmart.rimes.int/index.php/Reservoir/basin_wise (current published capacities; historical capacity changes not established)'
    capacity_total=sum(capacities.values())
    wide=daily.set_index('date')[cols].apply(pd.to_numeric,errors='coerce')
    wide['total_storage_mcft']=sum(wide[c]*1 for c in cols)
    wide['storage_percent_current_capacity']=wide.total_storage_mcft/capacity_total*100
    wide['storage_rising_3day']=wide.total_storage_mcft>wide.total_storage_mcft.shift(3)
    base=json.loads((RAW/'weather'/'open_meteo_era5_2015-2023_daily_baseline.json').read_text(encoding='utf-8'))
    rains=pd.concat([pd.DataFrame({'date':o['daily']['time'],'rain':o['daily']['precipitation_sum']}) for o in base],ignore_index=True).groupby('date',as_index=False).rain.mean()
    rains['date']=pd.to_datetime(rains.date); rains['rain_3day_mm']=rains.rain.rolling(3,min_periods=3).sum()
    # Threshold is estimated from 2015 dates strictly before the target day to avoid future leakage.
    rain_cut=float(rains.loc[rains.date<pd.Timestamp('2015-12-01'),'rain_3day_mm'].quantile(.90))
    wide=wide.reset_index().merge(rains[['date','rain_3day_mm']],on='date',how='left')
    wide['alarm_rule_storage80_rising3d_rainP90']=(wide.storage_percent_current_capacity>=80)&wide.storage_rising_3day&(wide.rain_3day_mm>=rain_cut)
    wide.to_csv(dest/'illustrative_track_b_backtest.csv',index=False)
    alarm_dates=wide.loc[wide.alarm_rule_storage80_rising3d_rainP90,'date']
    nov=wide[(wide.date>=pd.Timestamp('2015-11-01'))&(wide.date<pd.Timestamp('2015-12-01'))]
    nov_alarms=nov[nov.alarm_rule_storage80_rising3d_rainP90]
    backtest={'rule':'combined storage >=80% of present-day public total capacity AND total storage higher than three days earlier AND 3-day mean ERA5 rainfall >= its 90th percentile using only 2015 dates before 2015-12-01','capacities_mcft':capacities,'capacity_total_mcft':capacity_total,'capacity_source':source,'rain_threshold_mm_3day_P90_pre_target':rain_cut,'evaluation_start':str(wide.date.min().date()),'evaluation_end':str(wide.date.max().date()),'rainfall_overlap_days':int(wide.rain_3day_mm.notna().sum()),'all_alarm_days':int(len(alarm_dates)),'all_alarm_dates':[str(x.date()) for x in alarm_dates],'target_pre_event_window':'2015-11-01 through 2015-11-30; target reference 2015-12-01','target_window_alarm_days':[str(x.date()) for x in nov_alarms.date],'lead_days_to_2015_12_01':int((pd.Timestamp('2015-12-01')-nov_alarms.date.min()).days) if len(nov_alarms) else None,'out_of_target_alarm_days':int(len(alarm_dates)-len(nov_alarms)),'interpretation':'exploratory retrospective screening only; outside-target alarms cannot be called validated false alarms because daily flood outcomes are unavailable across the full series; current capacities are not verified historical capacities; this is not a release model.'}
    (dest/'illustrative_track_b_backtest.json').write_text(json.dumps(backtest,indent=2)+'\n',encoding='utf-8')
    start=tidy.date.min(); end=tidy.date.max()
    return {'daily_rows':int(len(tidy)),'reservoir_names':sorted(tidy.reservoir.unique().tolist()),'date_start':str(start.date()),'date_end':str(end.date()),'invalid_dates':int(daily.date.isna().sum()),'daily_rainfall_rows':int(len(rain)),'monthly_rows':int(len(m)),'track_b_backtest':backtest,'warnings':['Daily storage unit is mcft by dataset context; Kaggle rainfall units require source-specific interpretation.','Capacity percentages/backtest use present-day published capacities; historical values are unverified.','No release or gate data are present in this storage table; storage change is not a release estimate.']}

if __name__=='__main__': print(json.dumps({'weather':open_meteo(),'reservoirs':reservoir()},indent=2))
