"""Read-only A21 checks for represented verification outcomes and A09 OD overlap."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"data/features/routing/time_dependent_batch2"
MAIN=ROOT/"data/features/routing/three_state_batch3_v1"
OUT=ROOT/"data/features/routing/three_state_batch3_supplement_v1"


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(4*1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def status_support(arcs: pd.DataFrame, snapshots: pd.DataFrame, priority: pd.DataFrame) -> pd.DataFrame:
    """Count only states present for each prioritized arc in the 900 registered snapshots."""
    selected=arcs.set_index("arc_index",drop=False).loc[priority.arc_index.astype(int).tolist()]
    ids=selected.arc_index.to_numpy(np.int64)
    grid_ids=selected.grid_cell_id.to_numpy(np.int64)
    structures=selected.structure_class.to_numpy()
    assess=selected.assessment_status.to_numpy()
    out=np.zeros((len(selected),3),dtype=np.int32)  # passable, blocked, unknown
    for archive_name,group in snapshots.groupby("archive",sort=True):
        with np.load(BASE/str(archive_name),allow_pickle=False) as z:
            gids=z["grid_cell_ids"].astype(np.int64)
            order=np.argsort(gids,kind="stable")
            sorted_gids=gids[order]
            pos0=np.searchsorted(sorted_gids,grid_ids)
            valid=(grid_ids>=0)&(pos0<len(sorted_gids))
            exact=np.zeros(len(ids),dtype=bool)
            exact[valid]=sorted_gids[pos0[valid]]==grid_ids[valid]
            for snap in group.itertuples(index=False):
                state=np.zeros(len(ids),dtype=np.uint8)
                special=np.isin(structures,["bridge","bridge_and_tunnel","unassessed"])
                state[special]=4
                for mask,key in ((structures=="ordinary","ordinary_state"),
                                 (structures=="tunnel_underpass_proxy","tunnel_state")):
                    use=mask&exact&(assess!="NO_A07_ELIGIBLE_CELL")&(
                        assess!="AMBIGUOUS_OR_UNMATCHED_SEGMENT_KEY")
                    if use.any():
                        state[use]=z[key][int(snap.member_index),int(snap.horizon_index),order[pos0[use]]]
                out[:,0]+=np.isin(state,[1,2])
                out[:,1]+=(state==3)
                out[:,2]+=np.isin(state,[0,4])
    return pd.DataFrame({"rank":priority["rank"].to_numpy(),"arc_index":ids,
        "distinct_conditional_cases":priority["distinct_conditional_cases"].to_numpy(),
        "saved_passable_snapshots":out[:,0],"saved_blocked_snapshots":out[:,1],
        "saved_unknown_snapshots":out[:,2],
        "both_passable_and_blocked_represented":(out[:,0]>0)&(out[:,1]>0)})


def main() -> None:
    if OUT.exists():
        raise RuntimeError(f"REFUSE_EXISTING_SUPPLEMENT_OUTPUT: {OUT}")
    snapshots=pd.read_parquet(BASE/"snapshot_index.parquet")
    snapshots=snapshots[snapshots.horizon_hours.isin([6,24,72])].copy()
    priority=pd.read_parquet(MAIN/"unknown_verification_priority.parquet")
    arcs=pd.read_parquet(BASE/"directed_arcs.parquet")
    result=status_support(arcs,snapshots,priority)
    result.to_csv(OUT.parent/"_temporary_status_support.csv",index=False) if False else None
    a09_path=ROOT/"data/features/routing/results/batch2_v1/revision_3/route_results.jsonl"
    a09=[json.loads(line) for line in a09_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    sampled=pd.read_parquet(MAIN/"sampled_od_pairs.parquet")
    primary=set(zip(sampled.loc[sampled.sampling_class=="PRIMARY","origin_osmid"].astype(int),
                     sampled.loc[sampled.sampling_class=="PRIMARY","destination_osmid"].astype(int)))
    a09_pairs={(int(str(x["origin_id"]).split(":")[-1]),int(str(x["destination_id"]).split(":")[-1])) for x in a09}
    OUT.mkdir(parents=True,exist_ok=False)
    csv_path=OUT/"unknown_edge_saved_status_support.csv"
    result.to_csv(csv_path,index=False)
    both=int(result.both_passable_and_blocked_represented.sum())
    summary={"purpose":"A21 registered conditional check for evidence-supported passable/blocked status scenarios",
        "status":"NO_SUPPORTED_STATUS_SCENARIOS",
        "registered_snapshot_count":int(len(snapshots)),"snapshot_horizons_hours":[6,24,72],
        "prioritized_unknown_arc_count":int(len(result)),
        "arcs_with_both_passable_and_blocked_states":both,
        "arcs_with_any_passable_state":int((result.saved_passable_snapshots>0).sum()),
        "arcs_with_any_blocked_state":int((result.saved_blocked_snapshots>0).sum()),
        "arcs_unknown_in_all_registered_snapshots":int((result.saved_unknown_snapshots==len(snapshots)).sum()),
        "passable_or_blocked_scenarios_run":False,
        "reason":"No prioritized UNKNOWN arc has an A08 saved passable or blocked state; imposing either state would invent support.",
        "a09_direct_overlap":{"saved_route_rows":len(a09),"unique_a09_od_pairs":len(a09_pairs),
            "primary_sampled_od_pairs":len(primary),"exact_od_pair_overlap":len(primary&a09_pairs),
            "comparison_status":"UNAVAILABLE_NO_EXACT_OD_OVERLAP",
            "note":"No mapping is inferred from route IDs, filenames, or timestamps."}}
    json_path=OUT/"supplement.json"
    json_path.write_text(json.dumps(summary,indent=2),encoding="utf-8")
    inputs=[BASE/"snapshot_index.parquet",BASE/"directed_arcs.parquet",
        MAIN/"unknown_verification_priority.parquet",MAIN/"sampled_od_pairs.parquet",a09_path]
    outputs=[csv_path,json_path]
    manifest={"script_sha256":sha256_file(Path(__file__)),
        "input_sha256":{str(p.relative_to(ROOT)).replace("\\","/"):sha256_file(p) for p in inputs},
        "output_sha256":{p.name:sha256_file(p) for p in outputs}}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
