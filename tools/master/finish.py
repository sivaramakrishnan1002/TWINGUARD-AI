import argparse, time
from state import read_state, write_state, append_log, ROOT
p=argparse.ArgumentParser(); p.add_argument('task'); p.add_argument('--status',choices=['done','done_with_caveats','blocked_prerequisite','blocked_manual'],required=True); p.add_argument('--evidence',action='append',default=[]); p.add_argument('--commit'); p.add_argument('--note',action='append',default=[]); a=p.parse_args()
s=read_state(); t=next(x for x in s['tasks'] if x['id']==a.task)
t['status']=a.status; t['finished_at']=time.strftime('%Y-%m-%dT%H:%M:%S%z') if a.status.startswith('done') else None
t['evidence']+=a.evidence; t['notes']+=a.note; t['commit']=a.commit
s['locks']=[x for x in s['locks'] if x.get('task')!=a.task]
heavy_file=ROOT/'docs/master/locks/HEAVY.lock'
if heavy_file.exists():
 try:
  import json
  if json.loads(heavy_file.read_text(encoding='utf-8')).get('task')==a.task: heavy_file.unlink()
 except Exception: raise SystemExit('could not safely release heavy lock; inspect it manually')
write_state(s); append_log(f"Finished {a.task}: {a.status}")
