# I13 — Root and Lane A dependency reconciliation

**Disposition:** `done_with_caveats`. The combined root + Lane A manifests now resolve in an offline pip dry-run using the one project-owner-authorized certifi wheel. The root PyArrow and certifi pins are compatible with MLflow's resolved dependencies; no package was installed. I13 completion alone did not close G0. The later final G0 reassessment is recorded in `docs/master/GATE_G0_REPORT.md`; it resolved the stale checklist blocker, completed the gate protocol, and froze C1-C8 at v0.

## Decision and scope

- Lane A keeps `mlflow==3.17.2` in `requirements-A.txt`. Its package metadata requires `pyarrow>=4.0.0,<26`. The Integrator root pin is `pyarrow==25.0.1`, which satisfies this constraint and the project's Parquet use.
- The first approved retry retrieved `certifi==2026.7.22`, but the combined resolver exposed that `databricks-sdk==0.157.0` (in the MLflow dependency tree) requires `certifi>=2026.10.19`. No extra pin or package was changed/retrieved during that attempt.
- The project owner then approved changing the root certifi pin and retrieving the compatible wheel. The root pin is now `certifi==2026.10.23`, satisfying the reported lower bound and matching the already installed `.venv` version. Only root `pyarrow` and `certifi` pins changed; the four pre-existing root additions and every other pin remain unchanged. `requirements-A.txt` and all A16 tracking outputs were not modified.

## Authorized wheel and resolver

Retrieved only `certifi-2026.10.23-py3-none-any.whl` into an OS temporary wheelhouse: 135,082 bytes, SHA-256 `e9b54de76e530bb6cf0ccd036787103acb58fd42ba930ea8bf948ddbaa2f61d1`. No package was installed into any environment. No additional package network retrieval occurred.

Exact combined resolver invocation (wheelhouse path redacted as a temporary local path):

```powershell
.venv\Scripts\python.exe -m pip install --dry-run --disable-pip-version-check --no-index --find-links <temporary-wheelhouse> --only-binary=:all: -r requirements.txt -r requirements-A.txt
```

Result: **exit 0; resolver PASS**. This is a dry run only and did not install or update packages.

## Validation

- Parsed `requirements.txt`, `requirements-A.txt`, and `requirements-trackb.txt` as PEP 508 requirements; normalized direct package names were unique across the three manifests. All direct pins matched installed package metadata after the two justified pin updates.
- `.venv` package versions: `mlflow==3.17.2`, `pyarrow==25.0.1`, `certifi==2026.10.23`. MLflow metadata: `pyarrow>=4.0.0,<26`; the root exact pin satisfies it. `databricks-sdk==0.157.0`'s `certifi>=2026.10.19` bound is satisfied by the root pin.
- `.venv\Scripts\python.exe -m pip check` — PASS, no broken installed requirements.
- Focused command `.venv\Scripts\python.exe -m pytest -q tests/master/test_master.py tests/decision_lab/test_phase22_decision_lab.py tests/phase11 tests/phase12 tests/phase13 --import-mode=importlib` — **25 passed**.
- Full command `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib` — **211 passed, 1 skipped**, one existing Starlette/httpx deprecation warning.
- In-memory PyArrow 25.0.1 Parquet write/read equality check — PASS. `git diff --check` on I13 outputs — PASS.
- Raw audit `tools/audit_raw_logs.py` — **157 files, 30,544,672,450 bytes, 157 hash matches, 0 incomparable hashes, 0 mismatches**.
- `verify_state.py` — PASS, exit 0; read-only summary reported 14 shared-schema migrations and 1,319,380 grid cells. No database write. At I13 task closeout, `gate_check.py G0` was still NOT READY because the final G0 reassessment had not yet run. The later result is recorded in `docs/master/GATE_G0_REPORT.md`.

## Boundary

No packages were installed, no Lane A/B files or A16 artifacts were changed, and no G0/contract status was changed. I13 itself did not freeze contracts or change G0. The subsequent G0 closeout is recorded in `docs/master/GATE_G0_REPORT.md`.
