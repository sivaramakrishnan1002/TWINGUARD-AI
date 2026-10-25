import argparse, subprocess
from state import read_state, ROOT
p=argparse.ArgumentParser(); p.add_argument('--lane',choices=['A','B','I']); a=p.parse_args(); s=read_state(); bad=False
running=[t for t in s['tasks'] if t['status']=='running']
for i,x in enumerate(running):
 for y in running[i+1:]:
  both=set(x['outputs']) & set(y['outputs'])
  if both: bad=True; print(f"OVERLAP {x['id']} {y['id']}: {sorted(both)}")
if a.lane:
 owned={'A':['pipelines/','data/features/','data/processed/','tests/science/','database/migrations/2'], 'B':['pipelines/trackb/','services/trackb/','services/ai-service/','services/backend/','frontend/','infra/','database/migrations/1','database/migrations/3'], 'I':['docs/master/','tools/master/','tests/master/']}[a.lane]
 raw=subprocess.run(['git','status','--short'],cwd=ROOT,text=True,capture_output=True).stdout.splitlines()
 for line in raw:
  path=line[3:].replace('\\','/')
  if not any(path.startswith(x) for x in owned) and not (a.lane=='I' and path=='README.md'): print(f"OUTSIDE {a.lane}: {path}")
files=list((ROOT/'database/migrations').glob('*.sql')); nums={}
for f in files:
 try:n=int(f.name.split('_',1)[0])
 except ValueError:continue
 if n in nums: bad=True; print(f"DUPLICATE MIGRATION {n}: {nums[n].name}, {f.name}")
 nums[n]=f
raise SystemExit(1 if bad else 0)
