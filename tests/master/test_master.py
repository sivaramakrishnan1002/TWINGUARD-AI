"""Lightweight control-tool checks, including a simulated competing claim."""
import json, pathlib, subprocess, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'tools' / 'master'))
from state import ROOT, output_conflicts
from gate_check import (
    COMMON_CRITERIA, SPECIAL_CRITERIA, C3_APPROVED_SEMANTICS,
    C3_DATE_ONLY_DECISION, C3_DATE_ONLY_TESTS, c3_approved_date_only_blockers,
    g0_checklist_blockers,
)

def test_state_and_catalogue():
 s=json.loads((ROOT/'docs/master/STATE.json').read_text())
 assert len({t['id'] for t in s['tasks']})==len(s['tasks'])
 assert all(t['status'] in {'done','done_with_caveats','running','ready','blocked_prerequisite','blocked_manual','not_started','parked'} for t in s['tasks'])

def test_claim_collision_is_rejected():
 # Isolated copy of state module CLI behavior via temporary state file.
 source=(ROOT/'docs/master/STATE.json').read_text(); d=json.loads(source)
 d['tasks']=[{'id':'X1','lane':'I','title':'one','phase':'test','status':'ready','depends_on':[],'prerequisites':[],'inputs':[],'outputs':['shared'],'acceptance':[],'evidence':[],'session':None,'claimed_at':None,'finished_at':None,'commit':None,'heavy':False,'manual':False,'estimate_days':None,'target_day':None,'notes':[]},{'id':'X2','lane':'I','title':'two','phase':'test','status':'ready','depends_on':[],'prerequisites':[],'inputs':[],'outputs':['shared'],'acceptance':[],'evidence':[],'session':None,'claimed_at':None,'finished_at':None,'commit':None,'heavy':False,'manual':False,'estimate_days':None,'target_day':None,'notes':[]}]
 # Exercise the exact predicate used by claim.py with two competing tasks.
 d['tasks'][0]['status']='running'
 assert output_conflicts(d,d['tasks'][1])==['X1']

def test_g0_checklist_requires_all_contract_criteria_and_evidence(tmp_path):
 ids = sorted(SPECIAL_CRITERIA)
 contracts = []
 registry = []
 for cid in ids:
  draft = f'docs/master/contracts/{cid.lower()}_v0.md'
  (tmp_path / draft).parent.mkdir(parents=True, exist_ok=True)
  (tmp_path / draft).write_text('draft', encoding='utf-8')
  reg = {'id': cid, 'version': 'v0', 'path': draft, 'owner': 'I', 'consumers': ['test']}
  registry.append(reg)
  criteria = {}
  for name in (*COMMON_CRITERIA, *SPECIAL_CRITERIA[cid]):
   evidence = f'evidence/{cid}-{name}.txt'
   (tmp_path / evidence).parent.mkdir(parents=True, exist_ok=True)
   (tmp_path / evidence).write_text('evidence', encoding='utf-8')
   criteria[name] = {'status': 'PASS', 'evidence': [evidence]}
  contracts.append({**reg, 'criteria': criteria})
 for path in C3_DATE_ONLY_TESTS:
  (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
  (tmp_path / path).write_text('# date-only regression evidence', encoding='utf-8')
 (tmp_path / C3_DATE_ONLY_DECISION).parent.mkdir(parents=True, exist_ok=True)
 (tmp_path / C3_DATE_ONLY_DECISION).write_text(json.dumps({
  'decision_status': 'approved', 'semantics': list(C3_APPROVED_SEMANTICS),
  'historical_measurement_time_meaning': 'unknown', 'historical_timezone': 'unknown',
  'migration_101_authorized': False, 'shared_database_write_authorized': False,
  'live_operation_claim_authorized': False,
 }), encoding='utf-8')
 c3 = next(item for item in contracts if item['id'] == 'C3')
 c3['criteria']['timezone_status']['evidence'] = [C3_DATE_ONLY_DECISION, *C3_DATE_ONLY_TESTS]
 (tmp_path / 'docs/master/GATE_G0_REPORT.md').write_text('**Current gate decision: PASS**', encoding='utf-8')
 checklist = {'gate': 'G0', 'decision': 'PASS', 'report_path': 'docs/master/GATE_G0_REPORT.md', 'contracts': contracts}
 state = {'contracts': registry}
 assert g0_checklist_blockers(state, checklist, tmp_path) == []

 checklist['contracts'][0]['criteria']['version']['status'] = 'FAIL'
 checklist['contracts'][1]['criteria']['null_nodata']['evidence'] = ['missing.txt']
 blockers = g0_checklist_blockers(state, checklist, tmp_path)
 assert any('version=FAIL' in item for item in blockers)
 assert any('evidence missing: missing.txt' in item for item in blockers)

def test_c3_date_only_policy_rejects_missing_or_unapproved_decision(tmp_path):
 c3 = {'criteria': {'timezone_status': {
  'status': 'PASS', 'evidence': [C3_DATE_ONLY_DECISION, *C3_DATE_ONLY_TESTS]
 }}}
 for path in C3_DATE_ONLY_TESTS:
  (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
  (tmp_path / path).write_text('# regression test', encoding='utf-8')
 assert any('decision record is missing' in item for item in c3_approved_date_only_blockers(c3, tmp_path))

 (tmp_path / C3_DATE_ONLY_DECISION).parent.mkdir(parents=True, exist_ok=True)
 (tmp_path / C3_DATE_ONLY_DECISION).write_text(json.dumps({
  'decision_status': 'rejected', 'semantics': list(C3_APPROVED_SEMANTICS),
  'historical_measurement_time_meaning': 'unknown', 'historical_timezone': 'unknown',
  'migration_101_authorized': False, 'shared_database_write_authorized': False,
  'live_operation_claim_authorized': False,
 }), encoding='utf-8')
 assert any('decision is not approved' in item for item in c3_approved_date_only_blockers(c3, tmp_path))
