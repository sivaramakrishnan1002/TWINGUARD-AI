"""Accelerated replay from local historical Track B observations.

Outputs historical replay alerts as JSONL. No live ingestion or source writes occur.
"""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from .analysis import RuleThresholds, load_observations, rule_alert


def rows_from_sources(repo_root:Path,start:str,end:str):
    df,_,_=load_observations(repo_root)
    archive=repo_root/'data/raw/reservoirs/kaggle_chennai_water_management/archive.zip'
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    subset=df[(df.date>=start)&(df.date<=end)].sort_values(['date','reservoir'])
    for row in subset.itertuples(index=False):
        local_midnight=datetime.combine(pd.Timestamp(row.date).date(),time.min,tzinfo=ZoneInfo('Asia/Kolkata'))
        yield {
            'observed_at':local_midnight.isoformat(), 'reservoir_key':row.reservoir,
            'storage_pct':float(row.storage_pct),'rise_1d_pct':None if pd.isna(row.rise_1d_pct) else float(row.rise_1d_pct),
            'rise_3d_pct':None if pd.isna(row.rise_3d_pct) else float(row.rise_3d_pct),
            'rain_3d_mm':None if pd.isna(row.rain_3d_mm) else float(row.rain_3d_mm),
            'provenance':{'source_id':'Kaggle Chennai Water Management','source_file':'data/raw/reservoirs/kaggle_chennai_water_management/archive.zip',
                          'source_sha256':digest,'date_timezone':'Asia/Kolkata','timezone_status':'DEFAULT, to confirm',
                          'rainfall_unit_status':'INFERRED; original unit unspecified'},
        }


def replay_rows(rows, output_path:Path, start:str, end:str, thresholds_by_reservoir:dict[str,dict])->int:
    ordered=sorted(rows,key=lambda r:(r['observed_at'],r['reservoir_key']))
    events=[]
    for row in ordered:
        date=row['observed_at'][:10]
        if date<start or date>end or row.get('storage_pct') is None: continue
        key=row['reservoir_key'].upper()
        if key not in thresholds_by_reservoir: raise ValueError(f'missing trained thresholds for {key}')
        t=RuleThresholds(**thresholds_by_reservoir[key])
        feature=pd.DataFrame([{'storage_pct':float(row['storage_pct']),
            'rise_1d_pct':float(row.get('rise_1d_pct') or 0),
            'rise_3d_pct':float(row.get('rise_3d_pct') or 0),
            'rain_3d_mm':float(row.get('rain_3d_mm') or 0)}])
        alert,level,confidence=rule_alert(feature,t)
        if not alert[0]: continue
        observed=datetime.fromisoformat(row['observed_at'].replace('Z','+00:00'))
        events.append({'schema':'trackb.alert.v1','event_id':f"replay:{key}:{row['observed_at']}",
            'observed_at':row['observed_at'],'received_at':datetime.now().astimezone().isoformat(),
            'source':'replay','provenance':row.get('provenance',{}),'reservoir_key':key,
            'level':('Normal','Watch','Warning','Critical')[int(level[0])],'confidence':float(confidence[0]),
            'valid_from':observed.isoformat(),'valid_to':(observed+timedelta(days=1)).isoformat(),
            'rule_version':'trackb-rule-v1','trigger_inputs':{
                'storage_pct':feature.storage_pct.iloc[0],'rise_1d_pct':feature.rise_1d_pct.iloc[0],
                'rise_3d_pct':feature.rise_3d_pct.iloc[0],'rain_3d_mm':feature.rain_3d_mm.iloc[0]},
            'target':{'horizon_days':7,'capacity_fraction':0.8,'status':'DEFAULT, to confirm'}})
    output_path.write_text(''.join(json.dumps(e,separators=(',',':'))+'\n' for e in events),encoding='utf-8')
    return len(events)


def _dotenv_connect(repo_root:Path):
    import psycopg
    env={}
    for raw in (repo_root/'.env').read_text(encoding='utf-8').splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        key,value=line.split('=',1); env[key.strip()]=value.strip().strip('"\'')
    names={'host':'POSTGRES_HOST','port':'POSTGRES_PORT','dbname':'POSTGRES_DB','user':'POSTGRES_USER','password':'POSTGRES_PASSWORD'}
    params={dst:env[src] for dst,src in names.items() if env.get(src)}
    return psycopg.connect(**params)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path,help='output alert JSONL')
    parser.add_argument('--start',required=True,help='inclusive YYYY-MM-DD local date')
    parser.add_argument('--end',required=True,help='inclusive YYYY-MM-DD local date')
    parser.add_argument('--write-db',action='store_true',help='persist alerts; requires migration 100 already applied')
    args=parser.parse_args(); root=Path(__file__).resolve().parents[2]
    results=json.loads((root/'docs/trackb/BACKTEST_RESULTS.json').read_text(encoding='utf-8'))
    thresholds={key:value['rule_thresholds'] for key,value in results['per_reservoir'].items()}
    count=replay_rows(rows_from_sources(root,args.start,args.end),args.output,args.start,args.end,thresholds)
    if args.write_db:
        from .persistence import write_alert
        with _dotenv_connect(root) as conn:
            for line in args.output.read_text(encoding='utf-8').splitlines(): write_alert(conn,json.loads(line))
    print(f"replay alert events written: {count}; source=replay")

if __name__=='__main__': main()
