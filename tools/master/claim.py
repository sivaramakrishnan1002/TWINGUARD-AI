import argparse, json, time
from state import read_state, write_state, append_log, output_conflicts, ROOT
p=argparse.ArgumentParser(); p.add_argument('task'); p.add_argument('--session',required=True); a=p.parse_args()
s=read_state(); t=next((x for x in s['tasks'] if x['id']==a.task),None)
if not t: raise SystemExit('unknown task')
byid={x['id']:x for x in s['tasks']}
if t['status'] not in ('ready','not_started'): raise SystemExit(f"not claimable: {t['status']}")
if any(byid[d]['status'] not in ('done','done_with_caveats') for d in t['depends_on']): raise SystemExit('dependencies are not complete')
heavy_file=ROOT/'docs/master/locks/HEAVY.lock'
if t['heavy'] and heavy_file.exists():
 try: held=json.loads(heavy_file.read_text(encoding='utf-8'))
 except Exception: raise SystemExit('heavy lock exists but is unreadable; inspect manually')
 age=time.time()-heavy_file.stat().st_mtime
 if age>6*3600: append_log(f"Stale heavy lock (>6h) found for {held.get('task')}; manual verification required")
 raise SystemExit(f"heavy lock held by {held.get('lane')} {held.get('task')}; age_seconds={int(age)}")
if output_conflicts(s,t): raise SystemExit('output path conflict')
t.update(status='running',session=a.session,claimed_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
if t['heavy']:
 lock={'task':t['id'],'lane':t['lane'],'start_time':t['claimed_at'],'expected_duration':'set by claimant'}
 try:
  with heavy_file.open('x',encoding='utf-8') as f: json.dump(lock,f,indent=2); f.write('\n')
 except FileExistsError: raise SystemExit('heavy lock was acquired concurrently; claim cancelled')
 s['locks'].append(lock)
write_state(s); append_log(f"Claimed {t['id']} by {a.session}")
