import argparse
from state import read_state
p=argparse.ArgumentParser(); p.add_argument('gate'); a=p.parse_args(); s=read_state(); g=next(x for x in s['gates'] if x['id']==a.gate); tasks={t['id']:t for t in s['tasks']}
missing=[r for r in g['requires'] if r in tasks and tasks[r]['status'] not in ('done','done_with_caveats')]
if missing: print(f"{a.gate} CLOSED: tasks incomplete: {', '.join(missing)}")
elif any(r not in tasks for r in g['requires']): print(f"{a.gate} NOT READY: criterion evidence needs explicit gate checklist review")
else: print(f"{a.gate} READY for integrator gate checklist; all listed task prerequisites are complete")
