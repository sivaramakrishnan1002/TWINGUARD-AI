import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipelines/routing/three_state_batch3"))
import analyze
import validate_outputs
import cluster_bootstrap


def arcs(rows):
    return pd.DataFrame(rows, columns=["arc_index", "from_node", "to_node", "length_m", "base_speed_kmh",
                                      "structure_class", "assessment_status", "grid_cell_id", "source_osmid"])


def test_unknown_and_structure_reasons_are_not_passable_or_dry():
    a = arcs([
        (0, 1, 2, 10., 30., "ordinary", "A07_CELL_ASSESSED_IF_DEPTH_VALID", 10, 100),
        (1, 2, 3, 10., 30., "ordinary", "A07_CELL_ASSESSED_IF_DEPTH_VALID", 11, 101),
        (2, 1, 3, 10., 30., "bridge", "A07_CELL_ASSESSED_IF_DEPTH_VALID", 12, 102),
        (3, 3, 4, 10., 30., "ordinary", "NO_A07_ELIGIBLE_CELL", -1, 103),
        (4, 4, 5, 10., 30., "ordinary", "AMBIGUOUS_OR_UNMATCHED_SEGMENT_KEY", -1, 104),
    ])
    z = {"ordinary_state": np.array([[[1, 0, 3]]], dtype=np.uint8),
         "ordinary_speed_multiplier": np.ones((1, 1, 3), dtype=np.float32),
         "tunnel_state": np.ones((1, 1, 3), dtype=np.uint8),
         "tunnel_speed_multiplier": np.ones((1, 1, 3), dtype=np.float32)}
    state, reason, _ = analyze.edge_states(z, 0, 0, a, np.array([0, 1, 2, -1, -1]), np.arange(3))
    assert state.tolist() == [1, 0, 4, 0, 0]
    assert reason.tolist() == ["ASSESSED", "UNKNOWN_NODATA", "UNASSESSED_STRUCTURE",
                               "NO_A07_ELIGIBLE_CELL", "AMBIGUOUS_OR_UNMATCHED_SEGMENT_KEY"]


def test_fail_closed_excludes_blocked_and_unknown_edges():
    a = arcs([
        (0, 0, 1, 10., 30., "ordinary", "A07_CELL_ASSESSED_IF_DEPTH_VALID", 0, 1),
        (1, 1, 2, 10., 30., "ordinary", "A07_CELL_ASSESSED_IF_DEPTH_VALID", 1, 2),
        (2, 0, 2, 30., 30., "ordinary", "NO_A07_ELIGIBLE_CELL", -1, 3),
    ])
    state = np.array([1, 3, 0], dtype=np.uint8); mult = np.ones(3)
    g, _, _, _ = analyze.state_route_graph(3, a, np.array([0,1,0]), np.array([1,2,2]), state, mult)
    d = dijkstra(g, directed=True, indices=0)
    assert np.isinf(d[2])
    assert np.isfinite(d[1])


def test_conditional_route_uses_unknown_only_after_passable_path_fails():
    a = arcs([
        (0, 0, 1, 10., 30., "ordinary", "A07_CELL_ASSESSED_IF_DEPTH_VALID", 0, 1),
        (1, 1, 2, 10., 30., "ordinary", "A07_CELL_ASSESSED_IF_DEPTH_VALID", 1, 2),
        (2, 0, 2, 40., 30., "ordinary", "NO_A07_ELIGIBLE_CELL", -1, 3),
    ])
    st = np.array([1, 3, 0], dtype=np.uint8); mult = np.ones(3)
    paths = analyze.conditional_paths_for_source(3, a, np.array([0,1,0]), np.array([1,2,2]), st, mult, 0, [2])
    assert paths[2] == [2]
    detail = analyze.route_details(paths[2], st, np.array(["A","B","NO_A07_ELIGIBLE_CELL"], dtype=object),
                                   a.length_m.to_numpy(), a.base_speed_kmh.to_numpy(), mult)
    assert detail["status"] == "CONDITIONAL_NEEDS_VERIFICATION"
    assert detail["unknown_distance_m"] == 40.
    assert detail["assessed_edge_fraction"] == 0.


def test_conditional_lexicographic_objective_minimizes_unknown_distance_first():
    # A longer unknown arc plus fast assessed arcs must lose to the shorter unknown path.
    a = arcs([
        (0, 0, 1, 5., 20., "ordinary", "NO_A07_ELIGIBLE_CELL", -1, 1),
        (1, 1, 3, 5., 20., "ordinary", "NO_A07_ELIGIBLE_CELL", -1, 2),
        (2, 0, 2, 7., 20., "ordinary", "NO_A07_ELIGIBLE_CELL", -1, 3),
        (3, 2, 3, 20., 120., "ordinary", "A07_CELL_ASSESSED_IF_DEPTH_VALID", 0, 4),
    ])
    st = np.array([0,0,0,1], dtype=np.uint8); mult=np.ones(4)
    paths=analyze.conditional_paths_for_source(4,a,np.array([0,1,0,2]),np.array([1,3,2,3]),st,mult,0,[3])
    assert paths[3] == [2,3]


def test_arc_index_sequence_breaks_equal_cost_path_ties_deterministically():
    a=arcs([
        (8,0,1,10.,36.,"ordinary","A07_CELL_ASSESSED_IF_DEPTH_VALID",0,1),
        (3,1,3,10.,36.,"ordinary","A07_CELL_ASSESSED_IF_DEPTH_VALID",1,2),
        (2,0,2,10.,36.,"ordinary","A07_CELL_ASSESSED_IF_DEPTH_VALID",2,3),
        (9,2,3,10.,36.,"ordinary","A07_CELL_ASSESSED_IF_DEPTH_VALID",3,4),
    ])
    # Analyze assumes arc_index is the row index (as it is in the authoritative graph), so remap fixture IDs.
    a["arc_index"]=[0,1,2,3]
    st=np.ones(4,dtype=np.uint8); mult=np.ones(4)
    g,_,_,out=analyze.state_route_graph(4,a,np.array([0,1,0,2]),np.array([1,3,2,3]),st,mult)
    rev=dijkstra(g.transpose().tocsr(),directed=True,indices=np.array([3]))
    # Equal total cost: [0,1] precedes [2,3] lexicographically.
    path=analyze._recover_lex(0,3,2.0,rev,0,*out)
    assert path == [0,1]
    assert analyze._recover_lex(0,3,2.0,rev,0,*out) == path


def test_preordered_collapse_matches_reference_sort_for_parallel_arcs():
    r=np.array([0,0,0,1,1,2]); c=np.array([1,1,2,2,2,0]); a=np.arange(len(r),dtype=np.int64)
    w=np.array([4.,2.,1.,3.,3.,5.]); active=np.array([True,True,False,True,True,True])
    order=np.lexsort((a,c,r))
    starts=np.r_[0,np.flatnonzero((r[order][1:]!=r[order][:-1])|(c[order][1:]!=c[order][:-1]))+1]
    g0,r0,c0,a0=analyze._collapse(3,r[active],c[active],w[active],a[active])
    g1,r1,c1,a1=analyze._collapse_preordered(3,r,c,w,active,a,order,starts)
    assert (r0.tolist(),c0.tolist(),a0.tolist())==(r1.tolist(),c1.tolist(),a1.tolist())
    assert np.array_equal(g0.toarray(),g1.toarray())


def test_no_path_is_none_and_zero_length_route_is_distinct_from_no_path():
    assert analyze._recover(0, 1, 0, np.array([[-9999, -9999]]), np.array([],dtype=np.int64),
                            np.array([],dtype=np.int64), 2) is None
    detail=analyze.route_details([],np.array([],dtype=np.uint8),np.array([],dtype=object),
                                 np.array([],dtype=float),np.array([],dtype=float),np.array([],dtype=float))
    assert detail["status"] == "ASSESSED_PASSABLE_UNDER_A08_ASSUMPTIONS"
    assert detail["path_length_m"] == 0.
    no_route=analyze.route_details(None,np.array([],dtype=np.uint8),np.array([],dtype=object),
                                   np.array([],dtype=float),np.array([],dtype=float),np.array([],dtype=float))
    assert no_route["status"] == "NO_PATH"
    assert no_route["path_length_m"] is None
    assert no_route["unknown_reasons"] == {}
    assert isinstance(detail["unknown_reasons"], dict)
    legacy_rows=[{"unknown_reasons":[],"unknown_arc_indices":None,"proposed_arc_indices":[5,6],
        "proposed_edge_states":["ASSESSED_PASSABLE","UNKNOWN"],"unknown_edge_count":1},
        {"unknown_reasons":{"bridge_unassessed":2},"unknown_arc_indices":[8],
        "proposed_arc_indices":[8],"proposed_edge_states":["UNKNOWN"],"unknown_edge_count":1}]
    analyze.normalize_route_reason_counts(legacy_rows)
    assert legacy_rows[0]["unknown_reasons"]=={} and legacy_rows[0]["unknown_arc_indices"]==[6]
    assert legacy_rows[1]["unknown_reasons"]=={"bridge_unassessed":2} and legacy_rows[1]["unknown_arc_indices"]==[8]


def test_generated_outputs_obey_registered_schema_and_denominators():
    out=ROOT/"data/features/routing/three_state_batch3_v1"
    if not (out/"run_summary.json").exists():
        pytest.skip("A21 comparative outputs are generated after the preregistration commit")
    result=validate_outputs.validate_output_dir(out)
    assert result["primary_pairs"]==120
    assert result["snapshots"]==900


def test_route_edge_evidence_is_three_state_and_blocked_never_selected():
    a=arcs([
        (0,0,1,10.,30.,"ordinary","A07_CELL_ASSESSED_IF_DEPTH_VALID",0,1),
        (1,1,2,10.,30.,"ordinary","A07_CELL_ASSESSED_IF_DEPTH_VALID",1,2),
    ])
    state=np.array([1,0],dtype=np.uint8); mult=np.ones(2)
    path=analyze.conditional_paths_for_source(3,a,np.array([0,1]),np.array([1,2]),state,mult,0,[2])[2]
    detail=analyze.route_details(path,state,np.array(["ASSESSED","UNKNOWN_NODATA"],dtype=object),
        a.length_m.to_numpy(),a.base_speed_kmh.to_numpy(),mult)
    assert path==[0,1]
    assert detail["status"]=="CONDITIONAL_NEEDS_VERIFICATION"
    assert detail["unknown_edge_count"]==1
    blocked=np.array([1,3],dtype=np.uint8)
    g,_,_,_=analyze.state_route_graph(3,a,np.array([0,1]),np.array([1,2]),blocked,mult)
    assert np.isinf(dijkstra(g,directed=True,indices=0)[2])


def test_crossed_bootstrap_resamples_registered_event_and_od_clusters():
    pair_rows=[]; route_rows=[]; truth_rows=[]
    sectors=["NW","NE","SW","SE"]; bands=["short","medium","long"]
    od=0
    for sector in sectors:
        for band in bands:
            for _ in range(10):
                pair_rows.append({"od_id":od,"sector":sector,"distance_band":band,"sampling_class":"PRIMARY"})
                for event in ("e1","e2","e3"):
                    route_rows.append({"od_id":od,"event_key":event,"baseline_arc_indices":[],
                        "proposed_arc_indices":[4],"proposed_status":"CONDITIONAL_NEEDS_VERIFICATION",
                        "sector":sector,"distance_band":band})
                    for method in ("fail_closed","three_state"):
                        truth_rows.append({"od_id":od,"event_key":event,"method":method,
                            "outcome":"SIMULATED_PASSABLE_UNDER_A08_RULE"})
                od+=1
    result=cluster_bootstrap.bootstrap_intervals(pd.DataFrame(route_rows),pd.DataFrame(truth_rows),
        pd.DataFrame(pair_rows),replicates=20,seed=21031)
    assert result["event_cluster_count"]==3
    assert result["primary_OD_cluster_count"]==120
    assert result["metrics"]["availability_gain"]["percentile_2_5"]==1.0
    assert result["metrics"]["three_state_osse_failure_rate"]["percentile_97_5"]==0.0


def test_lazy_verification_priority_matches_registered_reference_greedy():
    exposure={0:{("a",1),("b",2),("c",3)},1:{("a",1),("b",2)},
        2:{("b",2),("c",3)},3:{("c",3)},4:{("d",4)}}
    lengths={0:10.,1:20.,2:20.,3:30.,4:1.}
    remaining=set().union(*exposure.values()); candidates=set(exposure); expected=[]
    while candidates:
        best=min(candidates,key=lambda ai:(-len(exposure[ai]&remaining),-lengths[ai],ai))
        expected.append(best); remaining-=exposure[best]; candidates.remove(best)
    assert analyze.greedy_unknown_edge_priority(exposure,lengths)==expected
