# Session protocol

At session start run `python tools/master/verify_state.py`, then `python tools/master/next_task.py --lane A|B|I`. Read the lane's batch spec and progress board; reconcile board claims with files, database and git before trusting status.

Claim only a ready task with completed dependencies and no output conflict: `python tools/master/claim.py TASK --session "session label"`. Heavy tasks need `docs/master/locks/HEAVY.lock`; claim/finish maintain STATE locks. A lock older than six hours is stale: verify the process is gone, record the stale lock in CHANGELOG.md, then clear it.

During work, save a task spec, record non-blocking decisions and defaults, fix script bugs, run task checks, lane tests and the raw audit. Keep data/raw read-only and credentials private. Finish with `python tools/master/finish.py TASK --status done|done_with_caveats --evidence path --commit HASH`, append notes, record commit, regenerate NEXT.md and commit only owned paths. Never commit lane paths from the other session.

Stop for raw hash mismatch, credential exposure risk, a result beyond known tolerance, three completed tasks, context handoff, no ready task, or a ready gate. At a gate both lanes stop; integrator runs gate_check, merges requirements, checks migration numbers, full tests, raw audit and end-to-end tests, writes the gate report, and handles backups only under GATES.md. Never delete Docker volumes. Modelling checks require fair baselines, spatial blocking/no leakage, true test prevalence, PR-AUC/ROC-AUC/F1/IoU/Brier/calibration, uncertainty coverage, physical sanity, fixed seeds, registry entry and limits.

