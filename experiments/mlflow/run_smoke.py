"""One-shot local-only A16 MLflow smoke run with synthetic values only.

Run from the repository root:
  .venv\\Scripts\\python.exe experiments\\mlflow\\run_smoke.py

Each invocation creates a fresh UUID-named directory and refuses collisions.
No project data, environment variables, credentials, or remote tracking server
are used.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

# MLflow 3.17 requires an explicit opt-in for its local filesystem backend.
# Scope it to this process; it does not enable remote tracking or persist a
# machine-wide environment change.
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"

import mlflow
from mlflow.tracking import MlflowClient


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "experiments" / "mlflow"
PIN = "3.17.2"
SEED = 1601


def main() -> None:
    if mlflow.__version__ != PIN:
        raise RuntimeError(f"Expected pinned MLflow {PIN}; found {mlflow.__version__}")
    token = uuid.uuid4().hex[:12]
    run_root = BASE / f"smoke_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{token}"
    if run_root.exists():
        raise FileExistsError(f"Refusing to overwrite existing A16 smoke output: {run_root}")
    tracking_dir = run_root / "tracking_store"
    staging_dir = run_root / "staging"
    readback_dir = run_root / "readback"
    tracking_dir.mkdir(parents=True, exist_ok=False)
    staging_dir.mkdir(parents=True, exist_ok=False)
    readback_dir.mkdir(parents=True, exist_ok=False)

    tracking_uri = tracking_dir.resolve().as_uri()
    mlflow.set_tracking_uri(tracking_uri)
    if mlflow.get_tracking_uri() != tracking_uri or not mlflow.get_tracking_uri().startswith("file:"):
        raise RuntimeError("MLflow did not resolve to the expected local file URI")

    # Small deterministic values generated in memory; no project or raw data.
    x = [0.0, 1.0, 2.0]
    observed = [0.0, 2.0, 4.0]
    predicted = [0.0, 1.8, 4.2]
    errors = [a - b for a, b in zip(predicted, observed)]
    mae = sum(abs(v) for v in errors) / len(errors)
    rmse = (sum(v * v for v in errors) / len(errors)) ** 0.5
    artifact_payload = {
        "kind": "synthetic_smoke_only",
        "seed": SEED,
        "x": x,
        "observed_synthetic": observed,
        "predicted_synthetic": predicted,
    }
    staging_artifact = staging_dir / "synthetic_smoke.json"
    staging_artifact.write_text(json.dumps(artifact_payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    artifact_sha = hashlib.sha256(staging_artifact.read_bytes()).hexdigest()

    experiment_name = f"TwinGuard_A16_synthetic_smoke_{token}"
    experiment = mlflow.set_experiment(experiment_name)
    client = MlflowClient(tracking_uri=tracking_uri)
    with mlflow.start_run(experiment_id=experiment.experiment_id, run_name=f"synthetic-smoke-{token}") as active:
        run_id = active.info.run_id
        mlflow.log_params({"seed": SEED, "sample_count": len(x), "method": "synthetic_linear_smoke"})
        mlflow.log_metrics({"mae_synthetic": mae, "rmse_synthetic": rmse})
        mlflow.log_artifact(str(staging_artifact), artifact_path="smoke")

    stored = client.get_run(run_id)
    expected_artifact_rel = "smoke/synthetic_smoke.json"
    artifact_paths = {entry.path for entry in client.list_artifacts(run_id, "smoke")}
    if not any(Path(path).name == "synthetic_smoke.json" for path in artifact_paths):
        raise RuntimeError("Logged synthetic artifact is missing from the local MLflow store")
    downloaded = Path(client.download_artifacts(run_id, expected_artifact_rel, dst_path=str(readback_dir)))
    readback_payload = json.loads(downloaded.read_text(encoding="utf-8"))
    if readback_payload != artifact_payload:
        raise RuntimeError("Artifact readback content does not match the synthetic artifact")
    if stored.data.params.get("seed") != str(SEED) or not math_close(stored.data.metrics.get("mae_synthetic"), mae):
        raise RuntimeError("Run parameter/metric readback validation failed")

    summary = {
        "task": "A16",
        "status": "SMOKE_PASSED_LOCAL_FILE_TRACKING",
        "mlflow_version": mlflow.__version__,
        "experiment_name": experiment_name,
        "experiment_id": experiment.experiment_id,
        "run_id": run_id,
        "tracking_uri": tracking_uri,
        "tracking_uri_scheme": "file",
        "parameters_read_back": dict(stored.data.params),
        "metrics_read_back": dict(stored.data.metrics),
        "artifact_path": expected_artifact_rel,
        "artifact_sha256": artifact_sha,
        "artifact_readback_matches": True,
        "synthetic_only": True,
    }
    (run_root / "smoke_evidence.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("status", "mlflow_version", "experiment_name", "experiment_id", "run_id", "tracking_uri_scheme", "artifact_path", "artifact_sha256", "artifact_readback_matches")}))


def math_close(actual: float | None, expected: float, tolerance: float = 1e-12) -> bool:
    return actual is not None and abs(float(actual) - expected) <= tolerance


if __name__ == "__main__":
    main()
