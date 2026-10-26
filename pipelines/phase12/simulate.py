#!/usr/bin/env python
"""NumPy local-inertial shallow-water simulation pilot (all outputs DERIVED)."""
from __future__ import annotations
import argparse, hashlib, json, math, re
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import rasterio
from rasterio.features import rasterize
from rasterio.transform import Affine

ROOT=Path(__file__).resolve().parents[2]
FACTOR=20
CELL_M=30*FACTOR
SEED=20261026
G=9.80665
OUTPUT=ROOT/'data/features/simulation/batch2_v1'

@dataclass(frozen=True)
class Member:
    member_id:int
    manning_multiplier:float
    infiltration_multiplier:float

def parameter_members():
    return [Member(i+1,n,f) for i,(n,f) in enumerate((n,f) for f in (.5,.75,1.,1.5) for n in (.75,1.,1.25,1.5,2.))]

def step(z,h,qx,qy,active,drain,mann,porosity,infiltration_m_s,rain_m_s,dx,dt):
    """One local-inertial step. qx/qy are face discharges per width (m2/s)."""
    if dx<=0 or dt<=0: raise ValueError('dx and dt must be positive')
    valid=active|drain; eta=z+h
    hx=np.maximum(h[:,:-1],h[:,1:]); hy=np.maximum(h[:-1,:],h[1:,:])
    nx=.5*(mann[:,:-1]+mann[:,1:]); ny=.5*(mann[:-1,:]+mann[1:,:])
    with np.errstate(divide='ignore',invalid='ignore',over='ignore'):
        ax=(qx-G*hx*dt*(eta[:,1:]-eta[:,:-1])/dx)/(1+G*nx**2*np.abs(qx)*dt/np.maximum(hx,1e-5)**(7/3))
        ay=(qy-G*hy*dt*(eta[1:,:]-eta[:-1,:])/dx)/(1+G*ny**2*np.abs(qy)*dt/np.maximum(hy,1e-5)**(7/3))
    ax[~(valid[:,:-1]&valid[:,1:])]=0; ay[~(valid[:-1,:]&valid[1:,:])]=0
    # Channels/open water drain; their boundary cannot inject water back to land.
    ax[(drain[:,:-1]&active[:,1:])&(ax>0)]=0
    ax[(active[:,:-1]&drain[:,1:])&(ax<0)]=0
    ay[(drain[:-1,:]&active[1:,:])&(ay>0)]=0
    ay[(active[:-1,:]&drain[1:,:])&(ay<0)]=0
    # Limit each face to one quarter of the donor's available water volume.
    # Four faces can leave a cell in a step; this prevents dry-cell velocity
    # spikes and keeps the explicit update non-negative without clipping mass.
    capx_l=np.maximum(h[:,:-1],0)*porosity[:,:-1]*dx/(4*dt)
    capx_r=np.maximum(h[:,1:],0)*porosity[:,1:]*dx/(4*dt)
    ax=np.where(ax>0,np.minimum(ax,capx_l),np.maximum(ax,-capx_r))
    capy_u=np.maximum(h[:-1,:],0)*porosity[:-1,:]*dx/(4*dt)
    capy_d=np.maximum(h[1:,:],0)*porosity[1:,:]*dx/(4*dt)
    ay=np.where(ay>0,np.minimum(ay,capy_u),np.maximum(ay,-capy_d))
    div=np.zeros_like(h)
    div[:,:-1]+=ax/dx; div[:,1:]-=ax/dx; div[:-1,:]+=ay/dx; div[1:,:]-=ay/dx
    p=np.maximum(porosity,1e-6); rain_depth=rain_m_s*dt
    infil_depth=np.minimum(h+rain_depth,infiltration_m_s*dt/p)
    hn=h.copy()
    hn[active]=np.maximum(0,h[active]+rain_depth/p[active]-infil_depth[active]-dt*div[active]/p[active])
    hn[drain|~valid]=0
    area=dx*dx
    rain_volume=rain_depth*np.count_nonzero(active)*area
    infiltration_volume=float(np.sum(infil_depth[active]*p[active])*area)
    out=0.
    for q,aa,bb in ((ax,active[:,:-1],drain[:,1:]),(-ax,drain[:,:-1],active[:,1:]),(ay,active[:-1,:],drain[1:,:]),(-ay,drain[:-1,:],active[1:,:])):
        out+=float(np.sum(np.maximum(q[aa&bb],0))*dx*dt)
    return hn,ax,ay,{'rain_m3':rain_volume,'infiltration_m3':infiltration_volume,'outflow_m3':out,'storage_m3':float(np.sum(hn[active]*p[active])*area)}

def stable_dt(h,qx,qy,active,dx):
    maxh=float(np.max(h[active])) if active.any() else 0.
    # The local-inertial scheme uses the gravity-wave CFL bound. Dry-cell
    # velocities are not used here because q/h is undefined as h approaches 0.
    return min(300.,.45*dx/max(math.sqrt(G*max(maxh,1e-4)),.01))

def simulate(z,active,drain,mann,porosity,infiltration,hourly_mm,dx):
    h=np.zeros_like(z,dtype=np.float64); qx=np.zeros((z.shape[0],z.shape[1]-1)); qy=np.zeros((z.shape[0]-1,z.shape[1]))
    total={'rain_m3':0.,'infiltration_m3':0.,'outflow_m3':0.}; snaps=[]; steps=0
    for mm in hourly_mm:
        rem=3600.
        while rem>1e-6:
            stable=stable_dt(h,qx,qy,active,dx)
            if stable<0.1: raise RuntimeError(f'local-inertial stability step below 0.1 seconds: {stable:.6g}')
            # A final sub-second remainder closes the one-hour forcing interval;
            # it is not a stability violation.
            dt=min(rem,stable)
            h,qx,qy,d=step(z,h,qx,qy,active,drain,mann,porosity,np.maximum(0,infiltration),max(0,float(mm))/1000/3600,dx,dt)
            for k in total: total[k]+=d[k]
            rem-=dt; steps+=1
            if steps>1_000_000: raise RuntimeError('simulation exceeded 1,000,000 time steps')
        snaps.append(h.astype(np.float32,copy=True))
    total['final_storage_m3']=float(np.sum(h[active]*porosity[active])*dx*dx)
    total['mass_balance_relative_error']=abs(total['rain_m3']-total['infiltration_m3']-total['outflow_m3']-total['final_storage_m3'])/max(total['rain_m3'],1e-9)
    return np.stack(snaps),total,steps

def _sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def _coarse(a,factor,valid=None,mode=False):
    ny,nx=a.shape; cy,cx=math.ceil(ny/factor),math.ceil(nx/factor); pad=((0,cy*factor-ny),(0,cx*factor-nx))
    v=np.isfinite(a) if valid is None else valid
    ap=np.pad(np.asarray(a),pad,constant_values=0); vp=np.pad(v.astype(np.uint8),pad,constant_values=0)
    aa=ap.reshape(cy,factor,cx,factor).transpose(0,2,1,3).reshape(cy,cx,-1)
    vv=vp.reshape(cy,factor,cx,factor).transpose(0,2,1,3).reshape(cy,cx,-1).astype(bool)
    if mode:
        out=np.zeros((cy,cx),dtype=aa.dtype)
        for y in range(cy):
            for x in range(cx):
                vals=aa[y,x,vv[y,x]]
                if vals.size: out[y,x]=np.bincount(vals.astype(int)).argmax()
        return out
    sums=np.where(vv,aa,0).sum(axis=2,dtype=np.float64); counts=vv.sum(axis=2)
    return np.divide(sums,counts,out=np.full((cy,cx),np.nan),where=counts>0)

def load_static():
    paths={'dem':ROOT/'data/processed/terrain_cleaned/cleaned_elevation_m.tif','worldcover':ROOT/'data/features/landcover/worldcover_2021_class.tif','waterways':ROOT/'data/features/hydrology/chennai_waterways.gpkg','blocks':ROOT/'data/processed/alignment/spatial_blocks.tif','labels':ROOT/'data/features/predictions/labels_nov2015.parquet','cells':ROOT/'data/features/static/cell_table.parquet'}
    with rasterio.open(paths['dem']) as ds: dem=ds.read(1); profile=ds.profile.copy(); transform=ds.transform; nodata=ds.nodata; crs=ds.crs
    valid=np.isfinite(dem)&(dem!=nodata)
    with rasterio.open(paths['worldcover']) as ds: wc=ds.read(1)
    if wc.shape!=dem.shape: raise ValueError('WorldCover and cleaned DEM grids differ')
    ct=pq.read_table(paths['cells'],columns=['row','col']); rows=ct['row'].to_numpy(); cols=ct['col'].to_numpy()
    cma=np.zeros(dem.shape,dtype=bool); cma[rows,cols]=True
    label=pq.read_table(paths['labels'],columns=['row','col','target_2015_11_12','target_2015_11_24','eligible_for_model'])
    lr=label['row'].to_numpy(); lc=label['col'].to_numpy(); eligible30=np.zeros(dem.shape,dtype=bool); eligible30[lr,lc]=label['eligible_for_model'].to_numpy().astype(bool)
    labels={}
    for col in ('target_2015_11_12','target_2015_11_24'):
        a=np.zeros(dem.shape,dtype=np.uint8); a[lr,lc]=label[col].to_numpy().astype(np.uint8); labels[col]=a
    import geopandas as gpd
    lines=gpd.read_file(paths['waterways']); lines=lines[lines.geometry.notna()].to_crs(crs)
    river=rasterize([(g,1) for g in lines.geometry],out_shape=dem.shape,transform=transform,fill=0,all_touched=True).astype(bool)
    water=(wc==80)|river
    nmap={10:.12,20:.10,30:.035,40:.08,50:.06,60:.03,70:.035,80:.03,90:.08,95:.10,100:.04}
    rough30=np.full(dem.shape,.06,dtype=np.float32)
    for code,n in nmap.items():rough30[wc==code]=n
    factor=FACTOR; z=_coarse(dem,factor,valid); cmaf=_coarse(cma.astype(np.float32),factor,np.ones_like(cma)); active=np.isfinite(z)&(cmaf>=.10)
    drainfrac=_coarse(water.astype(np.float32),factor,np.ones_like(cma)); drain=active&(drainfrac>=.05); active &= ~drain
    rough=_coarse(rough30,factor,valid); landcover=_coarse(wc.astype(np.uint8),factor,valid,mode=True).astype(np.int16)
    built=_coarse((wc==50).astype(np.float32),factor,np.ones_like(cma)); porosity=np.where(built>=.5,.70,1.)
    ec=_coarse(eligible30.astype(np.float32),factor,np.ones_like(cma))*factor**2
    labfrac={k:np.divide(_coarse((a*eligible30).astype(np.float32),factor,np.ones_like(cma))*factor**2,ec,out=np.zeros_like(ec),where=ec>0) for k,a in labels.items()}
    with rasterio.open(paths['blocks']) as ds: block30=ds.read(1)
    rr=np.minimum(np.arange(z.shape[0])*factor+factor//2,block30.shape[0]-1); cc=np.minimum(np.arange(z.shape[1])*factor+factor//2,block30.shape[1]-1); blocks=block30[np.ix_(rr,cc)]
    return {'z':z,'active':active,'drain':drain,'mann':rough,'porosity':porosity,'landcover':landcover,'labels':labfrac,'eligible':(ec>0)&active,'blocks':blocks,'ec':ec,'transform':transform*Affine.scale(factor,factor),'crs':crs,'profile':profile,'hashes':{str(p.relative_to(ROOT)):_sha(p) for p in paths.values()}}

def rainfall_daily():
    report=(ROOT/'docs/RAIN_SOURCES_COMPARISON.md').read_text(encoding='utf-8'); out={}
    for line in report.splitlines():
        m=re.match(r'\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([-0-9.]+)\s*\|',line)
        if m: out[m.group(1)]=float(m.group(2))
    if not out: raise ValueError('IMERG daily CMA means missing from rainfall comparison report')
    return out

def rainfall_72h(event):
    end=date.fromisoformat(event); start=end-timedelta(days=2); rain=rainfall_daily()
    era=pd.read_csv(ROOT/'data/features/weather/era5_event_hourly_features.csv',usecols=['timestamp_utc','precipitation'])
    era['timestamp_utc']=pd.to_datetime(era.timestamp_utc,utc=True); era['precipitation']=pd.to_numeric(era.precipitation,errors='coerce')
    era=era.groupby('timestamp_utc',as_index=False).precipitation.mean(); out=[]; d=start
    while d<=end:
        day=d.isoformat()
        if day not in rain: raise ValueError(f'IMERG CMA mean missing on {day}')
        e=era[era.timestamp_utc.dt.date==d]
        if len(e)!=24 or e.precipitation.isna().any():raise ValueError(f'ERA5 UTC profile has {len(e)} records for {day}; expected 24')
        shape=np.maximum(e.precipitation.to_numpy(float),0); total=shape.sum()
        if total<=0 and rain[day]>0:raise ValueError(f'ERA5 profile is zero but IMERG reports rain on {day}')
        out.extend((shape*(rain[day]/total if total else 0)).tolist()); d+=timedelta(days=1)
    return np.asarray(out)

def infiltration_rate(landcover,multiplier):
    # Fixed mm/hour assumptions by WorldCover class; calibrated multiplier is a scenario parameter.
    rates={10:1.4,20:1.2,30:1.,40:1.4,50:.25,60:.4,70:.5,80:0.,90:.8,95:.8,100:.5}
    mm=np.full(landcover.shape,.8)
    for cls,val in rates.items():mm[landcover==cls]=val
    return mm*multiplier/1000/3600

def folds(blocks,eligible,nfold=5,buffer_cells=5):
    from scipy.ndimage import binary_dilation
    ids=np.unique(blocks[eligible]); ids=ids[ids>0]
    rng=np.random.default_rng(SEED); order=rng.permutation(ids); assign={int(b):i%nfold for i,b in enumerate(order)}; result=[]
    for k in range(nfold):
        test=eligible&np.isin(blocks,[b for b,f in assign.items() if f==k]); train=eligible&~binary_dilation(test,iterations=buffer_cells)
        if not test.any() or not train.any():raise ValueError(f'empty split in fold {k+1}')
        result.append((train,test))
    return result

def metrics(y,score,probability=None):
    from sklearn.metrics import average_precision_score,roc_auc_score,brier_score_loss
    y=np.asarray(y,dtype=np.uint8); score=np.asarray(score,dtype=float)
    p=np.clip(score if probability is None else np.asarray(probability,dtype=float),0,1)
    if len(np.unique(y))<2:return {k:float('nan') for k in ('roc_auc','pr_auc','brier','ece','prevalence')}
    ece=0.; edges=np.linspace(0,1,11)
    for lo,hi in zip(edges[:-1],edges[1:]):
        m=(p>=lo)&(p<(hi if hi<1 else hi+1e-9))
        if m.any():ece+=float(m.mean()*abs(y[m].mean()-p[m].mean()))
    return {'roc_auc':float(roc_auc_score(y,p)),'pr_auc':float(average_precision_score(y,p)),'brier':float(brier_score_loss(y,p)),'ece':ece,'prevalence':float(y.mean())}

def cv_member(depth,eligible,yfraction,foldset):
    from sklearn.isotonic import IsotonicRegression
    y=(yfraction>=.10).astype(np.uint8); rows=[]; thresholds=[]
    for k,(train,test) in enumerate(foldset):
        best=(-1.,.05)
        for th in (.01,.03,.05,.10,.15,.30,.50):
            p=depth>=th; tp=int(np.sum(p&y&train)); fp=int(np.sum(p&~y.astype(bool)&train)); fn=int(np.sum(~p&y&train)); iou=tp/max(tp+fp+fn,1)
            if iou>best[0]:best=(iou,th)
        th=best[1]; thresholds.append(th); m=test&eligible; train_m=train&eligible; yy=y[m]
        calibrator=IsotonicRegression(out_of_bounds='clip').fit(depth[train_m],y[train_m])
        probabilities=calibrator.predict(depth[m]); met=metrics(yy,depth[m],probabilities); pred=depth[m]>=th
        tp=int(np.sum(pred&(yy==1))); fp=int(np.sum(pred&(yy==0))); fn=int(np.sum(~pred&(yy==1)))
        met.update({'fold':k+1,'threshold_m':th,'f1':2*tp/max(2*tp+fp+fn,1),'iou':tp/max(tp+fp+fn,1),'test_cells':int(m.sum())}); rows.append(met)
    return rows,float(np.median(thresholds))

def write_tif(path,a,transform,crs):
    out=np.where(np.isfinite(a),a,-9999).astype('float32')
    profile={'driver':'GTiff','height':out.shape[0],'width':out.shape[1],'count':1,'dtype':'float32','crs':crs,'transform':transform,'nodata':-9999,'compress':'deflate','predictor':3}
    with rasterio.open(path,'w',**profile) as ds:
        ds.write(out,1); ds.update_tags(STATUS='DERIVED_ASSUMPTION_BASED_PILOT',CELL_SIZE_M=str(CELL_M),NODATA='outside assessed CMA; not dry')

def run(output=OUTPUT):
    if output.exists() and any(output.iterdir()):raise FileExistsError(f'refusing to overwrite output: {output}')
    output.mkdir(parents=True,exist_ok=True); data=load_static(); foldset=folds(data['blocks'],data['eligible']); members=parameter_members(); events={}
    for event,key in [('2015-11-12','target_2015_11_12'),('2015-11-24','target_2015_11_24')]:
        rain=rainfall_72h(event); all_depth=[]; details=[]
        for member in members:
            import time
            t0=time.perf_counter(); states,diag,nsteps=simulate(data['z'],data['active'],data['drain'],data['mann']*member.manning_multiplier,data['porosity'],infiltration_rate(data['landcover'],member.infiltration_multiplier),rain,CELL_M)
            if not np.isfinite(states).all() or states.min()<-1e-6:raise RuntimeError(f'invalid depths for member {member.member_id}')
            if diag['mass_balance_relative_error']>.01:raise RuntimeError(f'mass balance >1% for member {member.member_id}: {diag["mass_balance_relative_error"]:.6g}')
            all_depth.append(states); details.append({**asdict(member),**diag,'steps':nsteps,'runtime_seconds':time.perf_counter()-t0})
        arr=np.stack(all_depth) # members,hours,y,x
        avg_volume=np.mean(arr*data['porosity'][None,None],axis=(0,2,3)); peak_hour=int(np.argmax(avg_volume)); selected=arr[:,peak_hour]; peak=arr.max(axis=1)
        member_cv=[]
        for j in range(len(members)): member_cv.append(cv_member(peak[j],data['eligible'],data['labels'][key],foldset))
        med_threshold=float(np.median([x[1] for x in member_cv])); fold_rows=[]
        for f in range(5):fold_rows.append({m:float(np.nanmean([member_cv[j][0][f][m] for j in range(len(members))])) for m in ('roc_auc','pr_auc','brier','ece','f1','iou','prevalence')}|{'fold':f+1})
        valid=data['eligible']; stem=f'{event}_DERIVED'
        for label,values in [('selected_mean',selected.mean(axis=0)),('selected_p05',np.percentile(selected,5,axis=0)),('selected_p95',np.percentile(selected,95,axis=0)),('peak_mean',peak.mean(axis=0)),('peak_p05',np.percentile(peak,5,axis=0)),('peak_p95',np.percentile(peak,95,axis=0))]:
            write_tif(output/f'depth_{label}_{stem}.tif',np.where(valid,values,np.nan),data['transform'],data['crs'])
        np.savez_compressed(output/f'member_peak_depth_{stem}.npz',depth_m=peak.astype('float32'),member_ids=np.arange(1,len(members)+1),seed=SEED)
        events[event]={'rainfall_utc_mm':rain.tolist(),'rainfall_total_mm':float(rain.sum()),'peak_hour_index':peak_hour,'members':details,'cross_validation':fold_rows,'median_training_threshold_m':med_threshold,'member_iou_mean':float(np.mean([np.mean([q['iou'] for q in x[0]]) for x in member_cv])),'member_iou_sd':float(np.std([np.mean([q['iou'] for q in x[0]]) for x in member_cv],ddof=1)),'label_positive_area_fraction':float(np.mean(data['labels'][key][valid]>=.10))}
    # Select a member and threshold on training blocks in each fold. The final
    # apparent map remains the full-data ensemble summary; its threshold is
    # the median of the training-fold selections.
    from .select_fold_models import run as select_fold_models
    selected_cv=select_fold_models(output)
    for event,ev in events.items():
        cv=selected_cv['events'][event]
        ev['cross_validation']=cv['folds']
        ev['median_training_threshold_m']=cv['median_training_threshold_m']
        ev['selected_members_by_fold']=cv['selected_members']
        values=[row['iou'] for row in cv['folds']]
        ev['holdout_iou_mean']=float(np.mean(values));ev['holdout_iou_sd']=float(np.std(values,ddof=1))
        ev['cross_validation_status']='member and threshold selected on training blocks; isotonic calibrated on training blocks; metrics are held-out fold results'
    summary={'name':'Phase 12 local-inertial simulation','status':'DERIVED_ASSUMPTION_BASED_PILOT','seed':SEED,'grid_cell_size_m':CELL_M,'crs':str(data['crs']),'model_cells':int(data['eligible'].sum()),'parameters':[asdict(m) for m in members],'events':events,'source_sha256':data['hashes'],'assumptions':{'rainfall':'IMERG daily CMA means scaled to the existing nine-point ERA5 mean hourly UTC pattern. No within-day or sub-grid rainfall is invented or downscaled.','time_basis':'72 UTC hours ending on each UNOSAT map date; each hourly profile is scaled so its daily sum equals the IMERG daily CMA mean.','manning':'WorldCover-class Manning n defaults are assumptions and varied by the listed ensemble multiplier.','buildings':'WorldCover built-up fraction >=0.5 is represented by 0.70 plan-area porosity; building obstacles are not inferred from GLO-30.','infiltration':'WorldCover-class infiltration defaults varied by ensemble multiplier; no observed soil infiltration measurements.','drainage':'No storm-drain network. Mapped open water and waterways are simplified free-drain sinks.','boundaries':'No-flow at outer and CMA land edges; mapped open water/waterways free-drain at zero stage. No external catchment inflow or reservoir releases are imposed.','labels':'UNOSAT map extents are calibration references, not depth observations or field truth.'},'limitations':['GLO-30 is a surface model, not bare-earth terrain or a building DSM.','600 m coarse scenario grid; labels use a 10% flooded subcell area rule.','Only two November 2015 snapshots; no out-of-event map labels accepted.','No drainage network, surveyed channel sections, stage hydrographs, gauge depths or external catchment inflows.','Ensemble quantiles are parameter spread, not calibrated statistical confidence intervals. No hydraulic-accuracy claim.','GFD is a coarse 10 Nov–4 Dec cross-check; OpenCity points are approximate and dates unclear; 2021 CRS conflict unresolved and 2023 map preliminary/unaccepted.'],'validation_available':{'gfd':'coarse event cross-check only; not independent pixel truth','opencity':'approximate, date-unclear point cross-check only','accepted_out_of_event_map':'none'}}
    import time
    summary['runtime_seconds_total']=float(sum(m['runtime_seconds'] for e in events.values() for m in e['members']))
    (output/'simulation_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
    return summary

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output-dir',type=Path,default=OUTPUT); args=ap.parse_args()
    path=args.output_dir if args.output_dir.is_absolute() else ROOT/args.output_dir; result=run(path)
    print(json.dumps({'status':result['status'],'grid_cell_size_m':result['grid_cell_size_m'],'runtime_seconds_total':result['runtime_seconds_total'],'outputs':len(list(path.iterdir()))},indent=2))
if __name__=='__main__':main()
