import argparse, time
from state import read_state, write_state, append_log, output_conflicts
p=argparse.ArgumentParser(); p.add_argument('task'); p.add_argument('--session',required=True); a=p.parse_args()
s=read_state(); t=next((x for x in s['tasks'] if x['id']==a.task),None)
if not t: raise SystemExit('unknown task')
byid={x['id']:x for x in s['tasks']}
if t['status'] not in ('ready','not_started'): raise SystemExit(f"not claimable: {t['status']}")
if any(byid[d]['status'] not in ('done','done_with_caveats') for d in t['depends_on']): raise SystemExit('dependencies are not complete')
if t['heavy'] and any(x.get('task') and x.get('task')!=a.task for x in s['locks']): raise SystemExit('heavy lock held')
if output_conflicts(s,t): raise SystemExit('output path conflict')
t.update(status='running',session=a.session,claimed_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
if t['heavy']: s['locks'].append({'task':t['id'],'lane':t['lane'],'start_time':t['claimed_at'],'expected_duration':'set by claimant'})
write_state(s); append_log(f"Claimed {t['id']} by {a.session}")
