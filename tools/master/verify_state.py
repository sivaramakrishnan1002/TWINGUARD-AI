"""Read-only reconciliation of control state against repository evidence."""
import json, pathlib, subprocess
from state import read_state, ROOT
s=read_state(); errors=[]
for t in s['tasks']:
 for e in t['evidence']:
  if not (ROOT/e).exists(): errors.append(f"{t['id']}: missing evidence {e}")
status=subprocess.run(['git','status','--short'],cwd=ROOT,text=True,capture_output=True).stdout
print('Git status entries:',len(status.splitlines()))
print('Lane boards:')
for p in ['docs/PROGRESS_BOARD.md','docs/trackb/PROGRESS_BOARD.md']:
 print(f'  {p}: '+('present' if (ROOT/p).exists() else 'MISSING'))
print('Migrations on disk:',len(list((ROOT/'database/migrations').glob('*.sql'))))
try:
 import psycopg
 lines=(ROOT/'.env').read_text(encoding='utf-8').splitlines(); env={}
 for line in lines:
  if '=' in line and not line.lstrip().startswith('#'):
   k,v=line.split('=',1); env[k.strip()]=v.strip().strip('"\'')
 with psycopg.connect(host=env.get('POSTGRES_HOST','localhost'),port=env.get('POSTGRES_PORT',5432),dbname=env.get('POSTGRES_DB'),user=env.get('POSTGRES_USER'),password=env.get('POSTGRES_PASSWORD'),connect_timeout=3,options='-c default_transaction_read_only=on') as c:
  with c.cursor() as q:
   q.execute('select count(*) from twinguard.schema_migrations'); print('DB applied migrations:',q.fetchone()[0])
   q.execute('select count(*) from twinguard.grid_cells'); print('DB grid_cells:',q.fetchone()[0])
except Exception as exc: print('DB read unavailable:',type(exc).__name__)
for issue in errors: print('DRIFT:',issue)
print('Claimed task state is not a replacement for lane-board evidence; inspect docs/master/RECONCILIATION.md.')
raise SystemExit(bool(errors))
