"""Accelerated replay from local historical Track B observations.

Outputs historical replay alerts as JSONL. No live ingestion or source writes occur.
"""
from __future__ import annotations
import argparse, hashlib, json
from datetime import date, datetime, timedelta
from pathlib import Path
import pandas as pd
from .analysis import RuleThresholds, load_observations, rule_alert


def rows_from_sources(repo_root:Path,start:str,end:str):
    df,_,_=load_observations(repo_root)
    archive=repo_root/'data/raw/reservoirs/kaggle_chennai_water_management/archive.zip'
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    subset=df[(df.date>=start)&(df.date<=end)].sort_values(['date','reservoir'])
    for row in subset.itertuples(index=False):
        source_date=pd.Timestamp(row.date).date().isoformat()
        yield {
            'source_date':source_date,'time_precision':'date','observation_timezone':'unknown','observed_at':None,
            'reservoir_key':row.reservoir,
            'storage_pct':float(row.storage_pct),'rise_1d_pct':None if pd.isna(row.rise_1d_pct) else float(row.rise_1d_pct),
            'rise_3d_pct':None if pd.isna(row.rise_3d_pct) else float(row.rise_3d_pct),
            'rain_3d_mm':None if pd.isna(row.rain_3d_mm) else float(row.rain_3d_mm),
            'provenance':{'source_id':'Kaggle Chennai Water Management','source_file':'data/raw/reservoirs/kaggle_chennai_water_management/archive.zip',
                          'source_sha256':digest,'timezone_status':'unknown; source provides date only',
                          'rainfall_unit_status':'INFERRED; original unit unspecified'},
        }


def replay_rows(rows, output_path:Path, start:str, end:str, thresholds_by_reservoir:dict[str,dict])->int:
    def day_key(row):
        if row.get('source_date') is not None:return row['source_date']
        return str(row['observed_at'])[:10]
    ordered=sorted(rows,key=lambda r:(day_key(r),r['reservoir_key']))
    events=[]
    for row in ordered:
        source_date=day_key(row)
        if source_date<start or source_date>end or row.get('storage_pct') is None: continue
        key=row['reservoir_key'].upper()
        if key not in thresholds_by_reservoir: raise ValueError(f'missing trained thresholds for {key}')
        t=RuleThresholds(**thresholds_by_reservoir[key])
        feature=pd.DataFrame([{'storage_pct':float(row['storage_pct']),
            'rise_1d_pct':None if row.get('rise_1d_pct') is None else float(row['rise_1d_pct']),
            'rise_3d_pct':None if row.get('rise_3d_pct') is None else float(row['rise_3d_pct']),
            'rain_3d_mm':None if row.get('rain_3d_mm') is None else float(row['rain_3d_mm'])}]).astype(float)
        alert,level,confidence=rule_alert(feature,t)
        if not alert[0]: continue
        precision=row.get('time_precision','instant')
        observed_at=row.get('observed_at')
        identity=f'date:{source_date}' if precision=='date' else f'instant:{observed_at}'
        event={'schema':'trackb.alert.v1','event_id':f"replay:{key}:{identity}",'source_date':source_date,
            'time_precision':precision,'observation_timezone':row.get('observation_timezone'),
            'observed_at':observed_at,'received_at':datetime.now().astimezone().isoformat(),
            'source':'replay','provenance':row.get('provenance',{}),'reservoir_key':key,
            'level':('Normal','Watch','Warning','Critical')[int(level[0])],'confidence':float(confidence[0]),
            'valid_from':None,'valid_to':None,
            'rule_version':'trackb-rule-v1','trigger_inputs':{
                'storage_pct':float(feature.storage_pct.iloc[0]),
                'rise_1d_pct':None if pd.isna(feature.rise_1d_pct.iloc[0]) else float(feature.rise_1d_pct.iloc[0]),
                'rise_3d_pct':None if pd.isna(feature.rise_3d_pct.iloc[0]) else float(feature.rise_3d_pct.iloc[0]),
                'rain_3d_mm':None if pd.isna(feature.rain_3d_mm.iloc[0]) else float(feature.rain_3d_mm.iloc[0])},
            'target':{'horizon_days':7,'capacity_fraction':0.8,'status':'DEFAULT, to confirm'}}
        if precision=='instant':
            observed=datetime.fromisoformat(observed_at.replace('Z','+00:00'))
            event['valid_from']=observed_at
            event['valid_to']=(observed+timedelta(days=1)).isoformat()
        events.append(event)
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
