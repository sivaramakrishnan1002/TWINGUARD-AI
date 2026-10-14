#!/usr/bin/env python
"""Summarize event-window rolling rainfall from the already-derived hourly CSV."""
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'data/features/weather/era5_event_hourly_features.csv'
OUTPUT=ROOT/'data/features/weather/event_peak_rainfall.json'

def main():
    if OUTPUT.exists(): raise FileExistsError(f'Refusing to overwrite {OUTPUT}')
    frame=pd.read_csv(SOURCE)
    frame['event_year']=frame.timestamp_utc.astype(str).str[:4]
    peaks={}
    for year,group in frame.groupby('event_year'):
        peaks[str(year)]={}
        for col in ('rain_mm_roll_1h','rain_mm_roll_3h','rain_mm_roll_24h'):
            values=pd.to_numeric(group[col],errors='coerce')
            idx=values.idxmax()
            peaks[str(year)][col]={'maximum_mm':float(frame.loc[idx,col]),'point_id':str(frame.loc[idx,'point_id']),'timestamp_utc':str(frame.loc[idx,'timestamp_utc']),'timestamp_local':str(frame.loc[idx,'timestamp_local'])}
    OUTPUT.write_text(json.dumps({'source':SOURCE.relative_to(ROOT).as_posix(),'method':'Maximum existing rolling accumulation per event-year and point; no raw source changed.','peaks':peaks},indent=2)+'\n',encoding='utf-8')
    print(f'Wrote {OUTPUT.relative_to(ROOT)}')

if __name__=='__main__':main()
