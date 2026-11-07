# Decisions pending

Consolidated from `docs/DECISIONS_PENDING.md` and `docs/trackb/DECISIONS_PENDING.md`; check those lane-owned files for full source context. C9 activation is resolved by owner decision CR-009; see `docs/master/CR-009_C9_ROUTE_ACTIVATION.md`.

| Decision | Current default/status | Owner/action |
|---|---|---|
| Older vs expanded CMA boundary | Provisional older CMA; handbook/project status says about 1,187 km². | User/manual confirmation before final evaluation. |
| T3 flood-rule constants | Candidate outputs exist; T4 preregistration/evaluation not completed. | Lane A; no acceptance inferred. |
| Track B alert target N/fraction | Board says N=7 and 0.80, DEFAULT to confirm. | Lane B/user. |
| Track B image tags and packages | Tags to confirm; streaming B7–B9 blocked. | M1 then Lane B. |
| Georeferencing, census/licences, mentor dates | Manual items; see `docs/MANUAL_TODO.md`. | User. |


| Phase 9C/10 interpretation | Use only as a single-event radar-visible susceptibility pilot; physical complement is a separate non-probability score. | No model acceptance decision implied; collect/digitise independent event labels before claiming generalisation. |

| Batch 2 simulation resolution | Select 30 m only if runtime and stability are acceptable; otherwise test and justify a coarser grid without overwriting prior outputs. | Lane A during A06. |
| Batch 2 building representation | Default to land-cover porosity; do not treat GLO-30 as a building DSM. | Lane A during A06. |
| Batch 2 roughness/loss parameters | Use documented land-cover Manning and drainage/infiltration assumptions; run sensitivity rather than claim observed values. | Lane A during A06. |
| Flood depth road threshold | 0.30 m default, sensitivity 0.15–0.50 m; remains an assumption until literature check. | Lane A during A07/A08. |
| Candidate shelter capacities | Explicit assumptions for schools/colleges and missing OSM capacity; test sensitivity. | Lane A during A10. |
| SAR map-label acceptance | Held-out IoU >=0.25 permits Tier C candidate only; UNOSAT scene dependence prevents independent accuracy claim. | Lane A during A04d; no automatic acceptance. |

| C3 historical date-only contract | Project owner approved the six bounded unknown-time semantics on 2026-10-28; record: `docs/master/C3_DATE_ONLY_DECISION.json`. Historical source meaning/timezone remain unknown; migration 101 remains unapplied. | Integrator: reflect the approved representation policy in C3 draft/checklist and validate it without claiming source-time truth or G0 readiness. |
