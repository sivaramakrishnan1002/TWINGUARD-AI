# A16 — local MLflow setup

Status: completed as a local synthetic smoke check. This is experiment-tracking setup evidence only; it is not a science run.

## Environment and pin

- Environment: project-local `D:\TIWNGUARD\.venv` (Python executable: `.venv\Scripts\python.exe`). No global installation was used.
- Lane A pin: `mlflow==3.17.2`, recorded in `requirements-A.txt`; shared `requirements.txt` was not changed by this task.
- Install or reproduce the pin from the repository root with:

  ```powershell
  .venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements-A.txt
  ```

- MLflow 3.17 requires opting into its local filesystem tracking backend. `run_smoke.py` sets `MLFLOW_ALLOW_FILE_STORE=true` in its own process only. It does not start a tracking server or contact a remote server.
- This install resolved MLflow's `pyarrow<26` requirement by changing the project venv's PyArrow from 26.0.0 to 25.0.1. `certifi` in that venv is 2026.10.23. No shared package pin file other than the A16-only `requirements-A.txt` was edited.

## Local smoke check

Run from `D:\TIWNGUARD`:

```powershell
$env:MLFLOW_DISABLE_AGENT_HINT = '1'
.venv\Scripts\python.exe experiments\mlflow\run_smoke.py
```

The script creates a new, unique directory per run under `experiments/mlflow/` and refuses a path collision. It uses three in-memory synthetic observations, logs three parameters, two synthetic metrics, and `smoke/synthetic_smoke.json`, then reads the run and artifact back using `MlflowClient`. It records a local `file:` tracking URI and does not read project data or credentials.

Successful run evidence:

- Run directory: `experiments/mlflow/smoke_20261028T075935Z_4e744a9f3cd6/`
- Experiment: `TwinGuard_A16_synthetic_smoke_4e744a9f3cd6` (ID `197856590113366366`)
- Run ID: `78c59f9aba5e4039a3c81e560064ea9d`
- Read-back parameters: `method=synthetic_linear_smoke`, `sample_count=3`, `seed=1601`
- Read-back metrics: synthetic MAE `0.1333333333333334`, synthetic RMSE `0.16329931618554525`
- Artifact read-back matched the original JSON; SHA-256 `13a679093d831c3c44c41e40fa5d946458070dae2e07203362323c865c326329`.
- Full machine-readable evidence is in that run directory's `smoke_evidence.json`.
- Three earlier unique smoke directories were retained rather than overwritten or deleted while correcting two harness issues (MLflow's required file-store opt-in, then artifact-list path matching). They are partial diagnostic runs, not the passing evidence; the successful run above is the acceptance result.

Check the installation without starting a server:

```powershell
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -c "from importlib.metadata import version; assert version('mlflow') == '3.17.2'; print(version('mlflow'))"
```

The smoke is deliberately small and synthetic. It verifies local logging and read-back, not tracking-server access, production retention, or reproducibility of project analyses. Preserve run directories; each smoke invocation writes to a fresh path.
