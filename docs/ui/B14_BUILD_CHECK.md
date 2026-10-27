# B14 local build and checks

Date: 2026-10-27

## Frontend production build

- Command: `npm run build` from `frontend/`
- Dependency source: existing local `frontend/node_modules` and lockfile; no package install or network access was used.
- Result: **passed** (`tsc --noEmit` and Vite production build, Vite 6.4.5; 37 modules transformed).
- Existing Vite warning remains: minified application JavaScript chunk is 1,253.63 kB (349.62 kB gzip), above the 500 kB advisory threshold. MapLibre worker is 520.10 kB.
- The three moderate Tailwind 3/PostCSS advisories remain documented. No forced upgrade or Tailwind v4 upgrade was run.

## Other local checks

- `python tools/audit_raw_logs.py`: passed; 157 files / 30,544,672,450 bytes, 157 hash matches, no incomparable hashes, no mismatches.
- `git diff --check`: no whitespace errors reported for tracked changes. The B14 UI sources and evidence files are newly untracked in this checkout, so Git's diff check does not inspect them.
- Lane B pytest checks were attempted with `pytest tests/trackb tests/ai_service` and `python -m pytest tests/trackb tests/ai_service`; both could not run because pytest is not installed in the available Python environment. No dependency installation was attempted.
- `python tools/master/verify_state.py`: state/board consistency checks completed; DB inspection was unavailable because the configured Python environment lacks a required database module. This is recorded as an environment limitation, not a G0 change.
- Manual visual rendering was unavailable because local browser use is disabled in Work settings. No visual-rendering or data-integration result is claimed.
