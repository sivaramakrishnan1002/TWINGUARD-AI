"""Reservoir storage target, transparent rule, and time-split comparator.

All targets refer only to future storage fraction, not floods or releases.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score, average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

CAPACITY_MCFT = {"POONDI":3231.0,"CHOLAVARAM":1081.0,"REDHILLS":3300.0,"CHEMBARAMBAKKAM":3645.0}
RESERVOIRS = tuple(CAPACITY_MCFT)
FEATURES = ("storage_pct","rise_1d_pct","rise_3d_pct","rain_1d_mm","rain_3d_mm","rain_7d_mm","doy_sin","doy_cos")

@dataclass(frozen=True)
class RuleThresholds:
    rise_1d_pct: float
    rise_3d_pct: float
    rain_3d_p75_mm: float
    rain_3d_p90_mm: float


def load_observations(repo_root: Path) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    """Read source archive in place (read-only) plus existing daily weather comparison."""
    archive=repo_root/'data/raw/reservoirs/kaggle_chennai_water_management/archive.zip'
    with ZipFile(archive) as z:
        storage=pd.read_csv(z.open('chennai_reservoir_levels.csv'),parse_dates=['Date'],dayfirst=True)
        rain=pd.read_csv(z.open('chennai_reservoir_rainfall.csv'),parse_dates=['Date'],dayfirst=True)
    weather=pd.read_csv(repo_root/'data/features/weather/daily_era5_nasa_power_comparison.csv',parse_dates=['date'])
    storage=storage.rename(columns={'Date':'date'}).melt('date',var_name='reservoir',value_name='storage_mcft')
    rain=rain.rename(columns={'Date':'date'}).melt('date',var_name='reservoir',value_name='rain_kaggle_raw')
    df=storage.merge(rain,on=['date','reservoir'],validate='one_to_one')
    df['capacity_mcft']=df.reservoir.map(CAPACITY_MCFT)
    df['storage_pct']=100*df.storage_mcft/df.capacity_mcft
    df=df.sort_values(['reservoir','date']).reset_index(drop=True)
    g=df.groupby('reservoir',sort=False)
    df['rise_1d_pct']=g.storage_pct.diff()
    df['rise_3d_pct']=g.storage_pct.diff(3)
    df['rain_1d_mm']=df.rain_kaggle_raw
    df['rain_3d_mm']=df.groupby('reservoir',sort=False).rain_kaggle_raw.transform(lambda s:s.rolling(3,min_periods=3).sum())
    df['rain_7d_mm']=df.groupby('reservoir',sort=False).rain_kaggle_raw.transform(lambda s:s.rolling(7,min_periods=7).sum())
    doy=df.date.dt.dayofyear.to_numpy()*2*np.pi/365.25
    df['doy_sin']=np.sin(doy); df['doy_cos']=np.cos(doy)
    return df,weather,storage


def future_target(frame: pd.DataFrame,horizon: int,fraction: float) -> pd.Series:
    if horizon<1 or not 0<fraction<=1: raise ValueError('horizon>=1 and 0<fraction<=1 required')
    values=frame.storage_pct.to_numpy()
    future=np.column_stack([pd.Series(values).shift(-i).to_numpy() for i in range(1,horizon+1)])
    future_max=np.max(np.where(np.isnan(future),-np.inf,future),axis=1)
    target=future_max>=fraction*100
    valid=~np.isnan(future).any(axis=1)
    return pd.Series(target,index=frame.index).where(valid).astype('boolean')


def learn_rule_thresholds(train: pd.DataFrame) -> RuleThresholds:
    positive_1=train.loc[train.rise_1d_pct>0,'rise_1d_pct'].dropna()
    positive_3=train.loc[train.rise_3d_pct>0,'rise_3d_pct'].dropna()
    return RuleThresholds(float(positive_1.quantile(.5)) if len(positive_1) else 0.,float(positive_3.quantile(.5)) if len(positive_3) else 0.,float(train.rain_3d_mm.quantile(.75)),float(train.rain_3d_mm.quantile(.90)))


def rule_alert(frame: pd.DataFrame,t: RuleThresholds) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    sp=frame.storage_pct.to_numpy(); r1=frame.rise_1d_pct.to_numpy(); r3=frame.rise_3d_pct.to_numpy(); rain=frame.rain_3d_mm.to_numpy()
    critical=sp>=90
    warning=(sp>=80)&((r3>=t.rise_3d_pct)|(rain>=t.rain_3d_p90_mm))
    watch=(sp>=70)|((r1>=t.rise_1d_pct)&(rain>=t.rain_3d_p75_mm))
    level=np.where(critical,3,np.where(warning,2,np.where(watch,1,0)))
    # A transparent rule-evidence score, expressly not a calibrated probability.
    confidence=np.clip((sp>=70).astype(float)+(r1>=t.rise_1d_pct)+(r3>=t.rise_3d_pct)+(rain>=t.rain_3d_p75_mm),0,4)/4
    return level>0,level,confidence


def confusion(y: np.ndarray,pred: np.ndarray) -> dict:
    tp=int(np.sum(y&pred)); fp=int(np.sum(~y&pred)); fn=int(np.sum(y&~pred)); tn=int(np.sum(~y&~pred))
    return {'tp':tp,'fp':fp,'fn':fn,'tn':tn,'pod':tp/(tp+fn) if tp+fn else None,'false_alarm_ratio':fp/(tp+fp) if tp+fp else None,'csi':tp/(tp+fp+fn) if tp+fp+fn else None}


def _calibrate_scores(y: np.ndarray,prob: np.ndarray,cal_y: np.ndarray,cal_prob: np.ndarray) -> tuple[np.ndarray,bool]:
    if len(np.unique(cal_y))<2: return np.clip(prob,1e-6,1-1e-6),False
    def logits(p):
        p=np.clip(p,1e-6,1-1e-6); return np.log(p/(1-p)).reshape(-1,1)
    calibrator=LogisticRegression(C=1e3,random_state=17).fit(logits(cal_prob),cal_y)
    return calibrator.predict_proba(logits(prob))[:,1],True


def reliability(y: np.ndarray,p: np.ndarray,bins:int=10)->list[dict]:
    edges=np.linspace(0,1,bins+1); out=[]
    for i in range(bins):
        mask=(p>=edges[i])&((p<edges[i+1]) if i<bins-1 else (p<=edges[i+1]))
        if mask.any():out.append({'bin_low':float(edges[i]),'bin_high':float(edges[i+1]),'n':int(mask.sum()),'mean_probability':float(p[mask].mean()),'observed_frequency':float(y[mask].mean())})
    return out


def _metrics(y:np.ndarray,p:np.ndarray,prob:np.ndarray)->dict:
    result=confusion(y,p)
    result.update({'brier':float(brier_score_loss(y,prob)),'log_loss':float(log_loss(y,np.clip(prob,1e-6,1-1e-6),labels=[0,1])),'roc_auc':float(roc_auc_score(y,prob)) if len(np.unique(y))>1 else None,'pr_auc':float(average_precision_score(y,prob)) if len(np.unique(y))>1 else None,'reliability':reliability(y,prob)})
    return result


def _train_test(frame:pd.DataFrame,horizon:int,fraction:float,seed:int=29,bootstrap_reps:int=300)->dict:
    f=frame.copy(); f['target']=future_target(f,horizon,fraction)
    f=f.dropna(subset=[*FEATURES,'target']).copy(); f['target']=f.target.astype(int)
    # Purge horizon days at each boundary so labels cannot look into the next split.
    train=f[f.date<pd.Timestamp('2015-01-01')-pd.Timedelta(days=horizon)]
    cal=f[(f.date>='2015-01-01')&(f.date<pd.Timestamp('2018-01-01')-pd.Timedelta(days=horizon))]
    test=f[f.date>='2018-01-01']
    if min(len(train),len(cal),len(test))==0: raise ValueError('temporal split has empty partition')
    ytr=train.target.to_numpy(); ycal=cal.target.to_numpy(); ytest=test.target.to_numpy()
    thresholds=learn_rule_thresholds(train)
    rule_pred,rule_level,rule_conf=rule_alert(test,thresholds)
    results={'n':len(test),'train_start':str(train.date.min().date()),'train_end':str(train.date.max().date()),'calibration_start':str(cal.date.min().date()),'calibration_end':str(cal.date.max().date()),'test_start':str(test.date.min().date()),'test_end':str(test.date.max().date()),'prevalence':float(ytest.mean()),'rule_thresholds':thresholds.__dict__,'rule':confusion(ytest,rule_pred),'rule_confidence_semantics':'fraction of four transparent rule indicators; not a calibrated probability'}
    # Baseline uses only currently observed storage: a persistence forecast.
    persistence=test.storage_pct.to_numpy()>=fraction*100
    results['persistence_baseline']=confusion(ytest,persistence)
    results['bootstrap_ci']={'rule':bootstrap_ci(ytest,rule_pred,test.date,bootstrap_reps=bootstrap_reps),'persistence_baseline':bootstrap_ci(ytest,persistence,test.date,bootstrap_reps=bootstrap_reps)}
    results['event_lead_days']={'rule':event_leads(test,rule_pred,fraction,horizon),'persistence_baseline':event_leads(test,persistence,fraction,horizon)}
    # Rainfall-only comparator is the requested rainfall baseline.
    rain_features=['rain_1d_mm','rain_3d_mm','rain_7d_mm']
    for name,features,model in [('rainfall_only',rain_features,make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000,C=1.0,random_state=seed))),('logistic',list(FEATURES),make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000,C=1.0,random_state=seed))),('gradient_boosting',list(FEATURES),HistGradientBoostingClassifier(max_iter=120,learning_rate=.06,max_leaf_nodes=15,l2_regularization=1.,random_state=seed))]:
        model.fit(train[features],ytr)
        cal_prob=model.predict_proba(cal[features])[:,1]; raw=model.predict_proba(test[features])[:,1]
        prob,calibrated=_calibrate_scores(ytest,raw,ycal,cal_prob)
        pred=prob>=.5
        results[name]=_metrics(ytest,pred,prob)
        results[name]['platt_calibration_applied']=calibrated
        results['bootstrap_ci'][name]=bootstrap_ci(ytest,pred,test.date,bootstrap_reps=bootstrap_reps,seed=seed)
        results['event_lead_days'][name]=event_leads(test,pred,fraction,horizon)
    return results


def bootstrap_ci(y:np.ndarray,pred:np.ndarray,dates:pd.Series,bootstrap_reps:int=300,seed:int=29)->dict:
    years=pd.to_datetime(dates).dt.year.to_numpy()
    unique_years=np.unique(years); rng=np.random.default_rng(seed)
    samples={'pod':[],'false_alarm_ratio':[],'csi':[]}
    for _ in range(bootstrap_reps):
        picked=rng.choice(unique_years,size=len(unique_years),replace=True)
        idx=np.concatenate([np.flatnonzero(years==year) for year in picked])
        metric=confusion(y[idx],pred[idx])
        for key in samples:
            if metric[key] is not None: samples[key].append(metric[key])
    return {key:([float(np.quantile(vals,.025)),float(np.quantile(vals,.975))] if vals else None) for key,vals in samples.items()}


def event_leads(frame:pd.DataFrame,pred:np.ndarray,fraction:float,horizon:int)->dict:
    storage=frame.storage_pct.to_numpy()
    dates=pd.to_datetime(frame.date).dt.normalize().to_numpy()
    crossing=np.flatnonzero((storage>=fraction*100)&(np.r_[False,storage[:-1]<fraction*100]))
    leads=[]
    for event_i in crossing:
        begin=max(0,event_i-horizon)
        alerts=np.flatnonzero(pred[begin:event_i])+begin
        if len(alerts): leads.append(int((dates[event_i]-dates[alerts[0]]).astype('timedelta64[D]').astype(int)))
    return {'observed_threshold_crossings':int(len(crossing)),'detected_crossings':len(leads),'median_lead_days':float(np.median(leads)) if leads else None,'lead_days':leads}


def run_analysis(repo_root:Path,bootstrap_reps:int=300)->dict:
    df,weather,_=load_observations(repo_root)
    outputs={'provenance':{'class':'DERIVED','target':'future storage fraction threshold; not flood occurrence or release decision','train':'2004-01-04 through 2014-12-31','calibration':'2015-01-01 through 2017-12-31','test':'2018-01-01 through 2020-12-03','seed':29,'bootstrap_reps':bootstrap_reps,'compute':'CPU (scikit-learn; GPU runtime not used)'},'rainfall_comparison':{},'sensitivity':[],'per_reservoir':{},'combined':{}}
    # Daily rainfall units are source-unspecified; this comparison is a scale/association audit only.
    rainwide=df.pivot(index='date',columns='reservoir',values='rain_kaggle_raw').mean(axis=1).rename('kaggle_raw')
    cmp=weather.set_index('date').join(rainwide,how='inner').loc['2015-01-01':'2020-12-03'].dropna()
    outputs['rainfall_comparison']={'n_days':len(cmp),'start':str(cmp.index.min().date()),'end':str(cmp.index.max().date()),'kaggle_raw_mean':float(cmp.kaggle_raw.mean()),'kaggle_raw_p95':float(cmp.kaggle_raw.quantile(.95)),'kaggle_raw_max':float(cmp.kaggle_raw.max()),'era5_mean_mm_day':float(cmp.era5_mean_mm.mean()),'nasa_power_mean_mm_day':float(cmp.nasa_power_mean_mm.mean()),'corr_kaggle_era5':float(cmp.kaggle_raw.corr(cmp.era5_mean_mm)),'corr_kaggle_nasa_power':float(cmp.kaggle_raw.corr(cmp.nasa_power_mean_mm)),'unit_interpretation':'INFERRED: daily rainfall values are on a depth-like scale comparable in order to mm/day products; source unit is unspecified; correlations and disagreement do not establish gauge truth.'}
    # Sensitivity target prevalence across every requested horizon/fraction and entity.
    for reservoir in [*RESERVOIRS,'COMBINED']:
        if reservoir=='COMBINED':
            pieces=[]
            for date,g in df.groupby('date'):
                row={'date':date,'storage_mcft':g.storage_mcft.sum(),'capacity_mcft':g.capacity_mcft.sum(),'storage_pct':100*g.storage_mcft.sum()/g.capacity_mcft.sum(),'rain_kaggle_raw':g.rain_kaggle_raw.mean()}
                pieces.append(row)
            f=pd.DataFrame(pieces).sort_values('date').reset_index(drop=True)
            f['rise_1d_pct']=f.storage_pct.diff(); f['rise_3d_pct']=f.storage_pct.diff(3)
            for n in (1,3,7):f[f'rain_{n}d_mm']=f.rain_kaggle_raw.rolling(n,min_periods=n).sum()
            theta=f.date.dt.dayofyear.to_numpy()*2*np.pi/365.25; f['doy_sin']=np.sin(theta); f['doy_cos']=np.cos(theta)
        else:f=df[df.reservoir==reservoir].copy().reset_index(drop=True)
        for horizon in (3,7,14):
            for fraction in (.7,.8,.9):
                y=future_target(f,horizon,fraction)
                eval_frame=f.copy(); eval_frame['target']=y
                usable=eval_frame.dropna(subset=[*FEATURES,'target']).copy()
                train=usable[usable.date<pd.Timestamp('2015-01-01')-pd.Timedelta(days=horizon)]
                test=usable[usable.date>='2018-01-01']
                row={'entity':reservoir,'horizon_days':horizon,'capacity_fraction':fraction,'n_labeled':int(y.notna().sum()),'target_prevalence':float(y.dropna().mean()),'test_n':int(len(test)),'test_prevalence':float(test.target.mean()) if len(test) else None}
                if len(train) and len(test):
                    th=learn_rule_thresholds(train)
                    rule_pred,_,_=rule_alert(test,th)
                    persistence=test.storage_pct.to_numpy()>=fraction*100
                    row['rule_test']=confusion(test.target.to_numpy().astype(bool),rule_pred)
                    row['persistence_test']=confusion(test.target.to_numpy().astype(bool),persistence)
                    row['rule_thresholds']=th.__dict__
                outputs['sensitivity'].append(row)
        if reservoir=='COMBINED':
            outputs['combined']=_train_test(f,7,.8,bootstrap_reps=bootstrap_reps)
        else:
            outputs['per_reservoir'][reservoir]=_train_test(f,7,.8,bootstrap_reps=bootstrap_reps)
    return outputs

if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    result=run_analysis(root)
    target=root/'docs/trackb/BACKTEST_RESULTS.json'
    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(f"wrote DERIVED results to {target.relative_to(root)}")



