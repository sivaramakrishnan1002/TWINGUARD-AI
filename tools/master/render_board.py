from state import read_state, ROOT
s=read_state(); tasks=s['tasks']; manual=[t for t in tasks if t['manual'] and t['status'] not in ('done','done_with_caveats')]
ready=[]; blocked=[]; running=[]
for t in tasks:
 if t['status']=='running': running.append(t)
 elif t['status'] in ('blocked_manual','blocked_prerequisite'): blocked.append(t)
 elif t['status'] in ('ready','not_started') and all(next(x for x in tasks if x['id']==d)['status'] in ('done','done_with_caveats') for d in t['depends_on']): ready.append(t)
def lines(title,rows):
 out=[f'## {title}','']
 out += [f"- **{t['id']} — {t['title']}** ({t['status']})" for t in rows] or ['- None.']
 return out+['']
text=['# Next actions','']
text+=lines('YOU DO THIS (manual tasks in order)',manual)
text+=lines('Ready tasks by lane A', [t for t in ready if t['lane']=='A'])
text+=lines('Ready tasks by lane B', [t for t in ready if t['lane']=='B'])
text+=lines('Ready tasks by lane I', [t for t in ready if t['lane']=='I'])
text+=lines('Blocked tasks',blocked)+lines('Running tasks',running)
text+=['## Next gate','', 'G0 contracts freeze is the next gate; review contract drafts and explicitly record freeze evidence.','']
(ROOT/'docs/master/NEXT.md').write_text('\n'.join(text),encoding='utf-8')
plan=ROOT/'docs/master/MASTER_PLAN.md'; body=plan.read_text(encoding='utf-8')
start='<!-- TASK TABLE START -->'; end='<!-- TASK TABLE END -->'
table=[start,'','| ID | Task | Lane | Depends on | Status |','|---|---|---|---|---|']
table += [f"| {t['id']} | {t['title']} | {t['lane']} | {', '.join(t['depends_on']) or '—'} | {t['status']} |" for t in tasks]
table += ['',end]
if start in body and end in body:
 before=body.split(start,1)[0]; after=body.split(end,1)[1]
 body=before+'\n'.join(table)+after
else:
 body += '\n## Current task catalogue\n\n'+'\n'.join(table)+'\n'
plan.write_text(body,encoding='utf-8')
