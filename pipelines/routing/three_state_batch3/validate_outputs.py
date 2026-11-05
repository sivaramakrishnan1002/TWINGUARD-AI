"""Deterministic validation for generated A21 three-state output version."""
from __future__ import annotations

import json
import hashlib
import sqlite3
from pathlib import Path

import pandas as pd


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def validate_output_dir(out: Path) -> dict:
    summary=json.loads((out/"run_summary.json").read_text(encoding="utf-8"))
    manifest=json.loads((out/"manifest.json").read_text(encoding="utf-8"))
    routes=pd.read_parquet(out/"route_cases.parquet")
    pairs=pd.read_parquet(out/"sampled_od_pairs.parquet")
    coverage=pd.read_parquet(out/"coverage_cases.parquet")
    snapshots=pd.read_parquet(out/"snapshot_edge_counts.parquet")
    priority=pd.read_parquet(out/"unknown_verification_priority.parquet")
    shelter=pd.read_parquet(out/"shelter_choice_by_case.parquet")
    shelter_changes=pd.read_parquet(out/"shelter_choice_changes.parquet")
    input_priority=pd.read_parquet(out/"unknown_input_decision_priority.parquet")
    stability_strata=pd.read_parquet(out/"decision_stability_by_stratum.parquet")
    for rel,expected_hash in manifest["output_hashes_before_manifest"].items():
        h=sha256_file(out/rel)
        assert h==expected_hash,(rel,h,expected_hash)
    checkpoint=sqlite3.connect(out/"checkpoint.sqlite")
    try:
        assert checkpoint.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
        assert int(checkpoint.execute("SELECT count(*) FROM snapshots").fetchone()[0])==900
    finally:
        checkpoint.close()
    expected=(int(summary["sampling"]["primary_od_count"])+int(summary["sampling"]["supplement_count"]))*900
    assert len(routes)==expected,(len(routes),expected)
    assert len(set(zip(routes.event_key,routes.scenario_key,routes.horizon_hours,routes.member_id,routes.od_id)))==len(routes)
    assert int(summary["sampling"]["primary_od_count"])==120
    assert len(set(zip(pairs.loc[pairs.sampling_class=="PRIMARY","origin_osmid"],
                       pairs.loc[pairs.sampling_class=="PRIMARY","destination_osmid"])))==120
    assert len(snapshots)==900
    assert len(coverage)==120*900
    assert set(routes.proposed_status)<= {"CONDITIONAL_NEEDS_VERIFICATION","ASSESSED_PASSABLE_UNDER_A08_ASSUMPTIONS","NO_PATH"}
    conditional=routes[routes.proposed_status=="CONDITIONAL_NEEDS_VERIFICATION"]
    assert (conditional.unknown_edge_count>0).all()
    assert (conditional.unknown_distance_m>0).all()
    assessed=routes[routes.proposed_status=="ASSESSED_PASSABLE_UNDER_A08_ASSUMPTIONS"]
    assert (assessed.unknown_edge_count==0).all()
    assert (assessed.unknown_distance_m==0).all()
    assert (routes.loc[routes.baseline_status=="NO_ASSESSED_PATH","baseline_arc_indices"].map(len)==0).all()
    allowed={"ASSESSED_PASSABLE","ASSESSED_BLOCKED","UNKNOWN"}
    for _,row in routes.iterrows():
        for prefix in ("proposed","baseline"):
            states=row[f"{prefix}_edge_states"]; reasons=row[f"{prefix}_edge_reasons"]; path=row[f"{prefix}_arc_indices"]
            assert len(states)==len(reasons)==len(path)
            assert set(states)<=allowed
            if prefix=="baseline": assert set(states)<={"ASSESSED_PASSABLE"}
            else:
                assert "ASSESSED_BLOCKED" not in states
                n_unknown=sum(x=="UNKNOWN" for x in states)
                if row.proposed_status=="CONDITIONAL_NEEDS_VERIFICATION": assert n_unknown==row.unknown_edge_count and n_unknown>0
                if row.proposed_status=="ASSESSED_PASSABLE_UNDER_A08_ASSUMPTIONS": assert n_unknown==0
        assert len(set(row.unknown_arc_indices))==len(row.unknown_arc_indices)
    assert shelter.duplicated(["event_key","scenario_key","horizon_hours","valid_at_utc","member_id","capacity_factor"]).sum()==0
    assert len(shelter_changes)==int(summary["route_decision_stability"]["shelters"]["member12_comparison"]["changed_numerator"])
    assert set(input_priority.input_type)<={"ROAD_EDGE","A10_RECORDED_MISSING_INPUT"}
    assert set(stability_strata.decision_type)<={"ROUTE","SHELTER_ALLOCATION_CANDIDATE"}
    assert ((stability_strata.stability_denominator.fillna(0)<=stability_strata.matched_decisions.fillna(0)) | stability_strata.matched_decisions.isna()).all()
    assert int(summary["route_cases"]["eligible_cases"])==len(routes)
    assert len(priority)==int(summary["unknown_priority_edge_count"])
    if len(priority)>1:
        assert priority["rank"].tolist()==list(range(1,len(priority)+1))
    return {"route_cases":len(routes),"primary_pairs":120,"supplement_pairs":int(summary["sampling"]["supplement_count"]),
            "snapshots":len(snapshots),"conditional_cases":len(conditional),"unknown_priority_edges":len(priority),
            "shelter_cases":len(shelter),"shelter_choice_changes":len(shelter_changes),
            "decision_stability_strata":len(stability_strata),
            "manifest_hashed_outputs":len(manifest["output_hashes_before_manifest"])}


if __name__=="__main__":
    here=Path(__file__).resolve().parents[3]
    import sys
    out=Path(sys.argv[1]) if len(sys.argv)>1 else here/"data/features/routing/three_state_batch3_v1"
    print(json.dumps(validate_output_dir(out),indent=2))
