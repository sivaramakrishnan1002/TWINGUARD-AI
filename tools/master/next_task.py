import argparse
from state import read_state
p=argparse.ArgumentParser(); p.add_argument('--lane',choices='ABIM',required=True); a=p.parse_args()
s=read_state(); tasks={t['id']:t for t in s['tasks']}
for t in s['tasks']:
 if t['lane']!=a.lane or t['status'] not in ('ready','not_started'): continue
 reasons=[f"dependency {d} is {tasks[d]['status']}" for d in t['depends_on'] if tasks[d]['status'] not in ('done','done_with_caveats')]
 reasons += [f"prerequisite: {x}" for x in t['prerequisites'] if t['status']!='ready']
 conflicts=[u['id'] for u in s['tasks'] if u['status']=='running' and set(u['outputs']) & set(t['outputs'])]
 if conflicts: reasons.append('output conflict: '+','.join(conflicts))
 if not reasons: print(f"{t['id']}\t{t['title']}")
 elif t['status']=='ready': print(f"{t['id']} blocked: {'; '.join(reasons)}")
