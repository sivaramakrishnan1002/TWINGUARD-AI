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
manual_steps={
 'M1':'Open docs/trackb/RUNBOOK.md; confirm image tags, pull the four listed images, then start only the trackb profile. Do not delete volumes.',
 'M2':'Install Maven on the development machine; verify with `mvn -version`, then record the version in the setup notes.',
 'M3':'Approve network/package installation for the UI; from frontend run `npm install`, then report permission or dependency failures.',
 'M4':'Create the GitHub repository, confirm its remote and default branch, then push only after reviewing the staged paths.',
 'M5':'Install MLflow in the project environment when approved; record the pinned package in the Lane A requirements file.',
 'M6':'Optional: georeference the 2021/2023 PDFs and December maps in QGIS; preserve originals and document control points/CRS.',
 'M7':'Verify census provenance and dataset licences; record source, terms, date and permitted use in the project catalogue.',
 'M8':'Set mentor review dates and record them in the project schedule.',
 'I14':'Project owner: approve or reject the selector proposal in docs/master/CR-008_B08_ARTIFACT_SELECTORS.md. Lane A selector evidence is recorded in docs/CR008_LANEA_SELECTOR_EVIDENCE.md (commit e3161b5); it does not approve the API change.',
 'I19':'CR-010 was approved and I19 completed the additive C9 raster projection review. See docs/master/CR-010_C9_RASTER_DELIVERY_DECISION.md and I19 evidence.',
 'I04':'Project owner: answer docs/master/I04_RELEASE_BACKUP_DECISION_REQUEST.md with release/tag/ref and publication scope, required reviews, and whether a database dump is required. If yes, identify an isolated test database and owner for a separately authorized preflight. No tag, dump, or publication is authorized yet.'}
for t in manual:
 text.append(f"  - Steps: {manual_steps.get(t['id'],'Review the task prerequisites and record the outcome.')}")
text.append('')
text+=lines('Ready tasks by lane A', [t for t in ready if t['lane']=='A'])
text+=lines('Ready tasks by lane B', [t for t in ready if t['lane']=='B'])
text+=lines('Ready tasks by lane I', [t for t in ready if t['lane']=='I'])
text+=lines('Blocked tasks',blocked)+lines('Running tasks',running)
next_gate=next((g for g in s.get('gates',[]) if g.get('status') not in ('ready','done','done_with_caveats','passed')),None)
if next_gate:
 text += ['## Next gate','', f"{next_gate['id']} is next (`{next_gate.get('status','unknown')}`); review its registered prerequisites and evidence before closure.",'']
else:
 text += ['## Next gate','','All recorded gates are ready or complete.','']
(ROOT/'docs/master/NEXT.md').write_text('\n'.join(text),encoding='utf-8')
plan=ROOT/'docs/master/MASTER_PLAN.md'; body=plan.read_text(encoding='utf-8')
current_start='<!-- CURRENT STATE START -->'; current_end='<!-- CURRENT STATE END -->'
g0=next((g for g in s.get('gates',[]) if g.get('id')=='G0'),{})
contracts=[c for c in s.get('contracts',[]) if c.get('id') in {f'C{i}' for i in range(1,9)}]
active=[t for t in tasks if t.get('status')=='running']
ready_by_lane={lane:[t['id'] for t in ready if t['lane']==lane] for lane in ('A','B','I')}
current=[current_start,'', '## Current coordinated state (generated)', '',
 f"- G0: `{g0.get('status','unknown')}`; C1-C8: {'frozen at v0' if len(contracts)==8 and all(c.get('version')=='v0' and c.get('status')=='frozen' for c in contracts) else 'see STATE.json'}.",
 "- Gate status: "+'; '.join(f"{g['id']} `{g.get('status','unknown')}`"+(f" ([report](GATE_{g['id']}_REPORT.md))" if (ROOT/f"docs/master/GATE_{g['id']}_REPORT.md").is_file() else '') for g in s.get('gates',[]))+'.',
 f"- Running tasks: {', '.join(t['id'] for t in active) if active else 'none'}.",
 f"- Selector-ready tasks: A: {', '.join(ready_by_lane['A']) or 'none'}; B: {', '.join(ready_by_lane['B']) or 'none'}; I: {', '.join(ready_by_lane['I']) or 'none'}.",
 '',current_end]
if current_start in body and current_end in body:
 before=body.split(current_start,1)[0]; after=body.split(current_end,1)[1]
 body=before+'\n'.join(current)+after
else:
 anchor='## Contributions and hypotheses'
 body=body.replace(anchor,'\n'.join(current)+'\n\n'+anchor,1)
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
