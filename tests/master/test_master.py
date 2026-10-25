"""Lightweight control-tool checks, including a simulated competing claim."""
import json, pathlib, subprocess, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'tools' / 'master'))
from state import ROOT, output_conflicts

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
