"""Deterministic crossed event/OD-cluster intervals for registered A21 route metrics."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SEED=21031
REPLICATES=2000


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def bootstrap_intervals(routes: pd.DataFrame, truth: pd.DataFrame, pairs: pd.DataFrame,
                        replicates: int=REPLICATES, seed: int=SEED) -> dict:
    """Percentile intervals from crossed event resampling and within-stratum OD resampling.

    The 120 primary directed pairs are sampled with replacement, 10 per registered
    sector × distance stratum; the three event windows are sampled with replacement.
    Snapshot/member/scenario cases stay intact within each event/OD cluster.
    """
    primary=pairs[pairs.sampling_class=="PRIMARY"][["od_id","sector","distance_band"]]
    join_frame=primary.rename(columns={"sector":"registered_sector","distance_band":"registered_distance_band"})
    r=routes.merge(join_frame,on="od_id",how="inner",validate="many_to_one")
    if (len(primary)!=120 or r.event_key.nunique()!=3 or
            not (r.sector==r.registered_sector).all() or
            not (r.distance_band==r.registered_distance_band).all() or
            r.groupby(["sector","distance_band"]).od_id.nunique().ne(10).any()):
        raise ValueError("BOOTSTRAP_PRIMARY_FRAME_MISMATCH")
    events=sorted(r.event_key.unique().tolist())
    strata=[g.od_id.astype(int).tolist() for _,g in primary.groupby(["sector","distance_band"],sort=True)]
    cluster_keys=["event_key","od_id"]
    has_path=lambda value: value is not None and len(value)>0
    route_cluster=r.assign(
        denominator=1,
        baseline_available=r.baseline_arc_indices.map(has_path).astype(int),
        proposed_available=r.proposed_arc_indices.map(has_path).astype(int),
        conditional=(r.proposed_status=="CONDITIONAL_NEEDS_VERIFICATION").astype(int),
    ).groupby(cluster_keys,as_index=False)[["denominator","baseline_available","proposed_available","conditional"]].sum()
    t=truth.merge(primary[["od_id"]],on="od_id",how="inner",validate="many_to_one")
    t["truth_assessed"]=t.outcome.isin(["SIMULATED_BLOCKED","SIMULATED_PASSABLE_UNDER_A08_RULE"]).astype(int)
    t["truth_failed"]=(t.outcome=="SIMULATED_BLOCKED").astype(int)
    truth_cluster=t.groupby(cluster_keys+['method'],as_index=False)[['truth_assessed','truth_failed']].sum()
    rc={(str(x.event_key),int(x.od_id)):x for x in route_cluster.itertuples(index=False)}
    tc={(str(x.event_key),int(x.od_id),str(x.method)):x for x in truth_cluster.itertuples(index=False)}
    rng=np.random.Generator(np.random.PCG64(seed))
    names=["baseline_route_availability","three_state_route_availability","availability_gain",
           "conditional_route_share","fail_closed_osse_failure_rate","three_state_osse_failure_rate"]
    draws={name:[] for name in names}
    for _ in range(replicates):
        sample_events=rng.choice(events,size=len(events),replace=True)
        selected=[]
        for ids in strata: selected.extend(rng.choice(ids,size=len(ids),replace=True).tolist())
        den=base=proposed=conditional=0
        fail={"fail_closed":0,"three_state":0}; assessed={"fail_closed":0,"three_state":0}
        for event in sample_events:
            for od in selected:
                x=rc[(str(event),int(od))]
                den+=int(x.denominator); base+=int(x.baseline_available); proposed+=int(x.proposed_available); conditional+=int(x.conditional)
                for method,key in (("fail_closed","fail_closed"),("three_state","three_state")):
                    y=tc.get((str(event),int(od),method))
                    if y is not None:
                        assessed[key]+=int(y.truth_assessed); fail[key]+=int(y.truth_failed)
        if not den: continue
        draws["baseline_route_availability"].append(base/den)
        draws["three_state_route_availability"].append(proposed/den)
        draws["availability_gain"].append((proposed-base)/den)
        draws["conditional_route_share"].append(conditional/den)
        for key,name in (("fail_closed","fail_closed_osse_failure_rate"),("three_state","three_state_osse_failure_rate")):
            if assessed[key]: draws[name].append(fail[key]/assessed[key])
    return {"method":"crossed event-cluster bootstrap and within-sector-distance-stratum OD-cluster bootstrap; percentile 95% interval",
        "replicates_requested":replicates,"seed":seed,"event_cluster_count":len(events),"primary_OD_cluster_count":len(primary),
        "od_strata_count":len(strata),"case_grain":"all saved scenario/horizon/member cases remain together within an event × OD cluster",
        "limitations":["Only three event clusters; intervals are descriptive and unstable with so few event windows.",
            "Simulated route outcomes are not observational validation."],
        "metrics":{name:{"valid_replicates":len(values),"percentile_2_5":float(np.quantile(values,.025)) if values else None,
                          "percentile_97_5":float(np.quantile(values,.975)) if values else None}
                   for name,values in draws.items()}}


def main(out: Path) -> None:
    target=out/"cluster_bootstrap_intervals.json"
    if target.exists(): raise RuntimeError(f"REFUSE_EXISTING_BOOTSTRAP_OUTPUT: {target}")
    routes=pd.read_parquet(out/"route_cases.parquet")
    truth=pd.read_parquet(out/"heldout_member20_osse.parquet")
    pairs=pd.read_parquet(out/"sampled_od_pairs.parquet")
    result=bootstrap_intervals(routes,truth,pairs)
    target.write_text(json.dumps(result,indent=2),encoding="utf-8")
    summary_path=out/"run_summary.json"; summary=json.loads(summary_path.read_text(encoding="utf-8"))
    summary["cluster_bootstrap_intervals"]=result
    summary_path.write_text(json.dumps(summary,indent=2,allow_nan=False),encoding="utf-8")
    manifest_path=out/"manifest.json"; manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["supplemental_analysis_scripts"]={"cluster_bootstrap.py":sha256_file(Path(__file__))}
    manifest["output_hashes_before_manifest"]={p.relative_to(out).as_posix():sha256_file(p)
        for p in sorted(out.rglob("*")) if p.is_file() and p!=manifest_path}
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    import sys
    main(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[3]/"data/features/routing/three_state_batch3_v1")
