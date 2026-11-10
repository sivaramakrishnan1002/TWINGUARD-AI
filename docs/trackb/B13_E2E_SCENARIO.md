# B13 — G5 product-pipeline replay (CR-020)

**Lane B report, 2026-11-08** (written 2026-11-10). This report covers event 2015-12-01 → `/v3` → outputs, run through the packaged B11 stack. The full machine-readable evidence is in [`B13_PRODUCT_REPLAY_EVIDENCE.json`](B13_PRODUCT_REPLAY_EVIDENCE.json), which records every call with its status, timing, byte count, SHA-256 and schema-check result. The script that produced it is [`tests/e2e/b13_product_replay.py`](../../tests/e2e/b13_product_replay.py).

**Result: acceptance items 1–3 and 5–7 pass.** Item 4 is supplied by B48 (see below). Item 8 belongs to the Integrator at closeout.

## Stack and commands

| | |
|---|---|
| Stack | `docker compose -p twinguard-b11 -f docker-compose.b11.yml up --build -d --wait` |
| Docker | Docker Desktop 29.8.2 |
| Image | CPU image `local/twinguard-b11-ai:0.1.0` (no GPU image) |
| Health | All three services healthy after 135 s |
| Base URL | nginx `http://127.0.0.1:8081/api/ai` |
| Evidence run | `.venv\Scripts\python.exe tests\e2e\b13_product_replay.py --base http://127.0.0.1:8081/api/ai` (exit 0, 198 s) |
| Raw audit | `.venv\Scripts\python.exe tools\audit_raw_logs.py` |
| Engine | A25 on the 120 m citywide grid, `twinguard-flood-engine/2.1.0` behind `twinguard-v3-engine/1.1.0`. In the container `GET /v3/status` reports `device {requested auto, resolved cpu, cuda_available false}` and `worker.mode per_run`. |
| Proxy | `/api/ai/v3/` allows GET, POST and PUT. A `DELETE` through nginx returned 403. |

The first `up --build` failed in the AI image's `pip install`: pip reported `pydantic-core==2.50.1` with "versions: none". The index lists that version, and a retry built cleanly in 63 s, so this was a transient network problem inside the build.

## 1 Input (REPLAY)

| Item | Value |
|---|---|
| A25 event catalogue `data/features/live/a25_static_v1/shared/events.json` | SHA-256 `e402c3f5f5940104551ca76fbf620af30eae2822a23d5247468718a0bdf37d61` |
| A25 bundle `manifest.json` (`a25_static_v1`) | SHA-256 `a4bced11e8a6f77b31ff80274d257c81bb51f66acf6371edcde311fddd9bf48a` |
| Selected record | `2015-12-01`, "Chennai floods, Dec 2015", 2015-11-30T00:00Z → 2015-12-03T00:00Z, 72 × 60 min, 351.54 mm. Source: GPM IMERG daily CMA mean with ERA5 hourly shape. `source_mode` REPLAY. `values_mm` SHA-256 `bd8494b3…09d63c`. |
| A06 fallback catalogue (not used) | `services/ai-service/app/v3/events.json`, SHA-256 `9d2e922e…6a3001` |

No Open-Meteo snapshot was used.

## 2 Engine runs (packaged)

All three runs completed and passed schema validation. All three have `forcing_sha256` = `181f4c39ab47f0da4e72e3d5f67f020811de966ab367eb58151a6a0e20783cd7`, because A25 hashes the whole 72 h event series regardless of duration.

| Run | Request | run_id | Wall | Engine output | `provenance.device` |
|---|---|---|---|---|---|
| Acceptance body | `{"mode":"event","event_key":"2015-12-01"}` (24 h) | `evt-20261108T152124Z-415999af` | 4.1 s | Reused engine run `evt-20261108T094352Z-b6540ac7` (35.8 s when computed) | cuda (how the reused result was computed) |
| Primary, paired with the UI | `{"mode":"event","event_key":"2015-12-01","duration_hours":48}` | `evt-20261108T152128Z-59eba744` | 4.1 s | Reused engine run `evt-20261108T141235Z-ba7ef063` (100.8 s when computed), the same engine output as the B48 run `evt-20261108T141229Z-fb36a1cd` | cuda (as above) |
| Fresh compute | as above, `duration_hours` 36 | `evt-20261108T152132Z-49db828b` | **161.2 s** | Computed in the container: engine run `evt-20261108T152134Z-c1ad6db9`, 155.4 s | **cpu** |

- **Frames:** 49, 97 and 73 respectively, all on the 120 m grid.
- **Limitations:** every run's notes now read "A25 local-inertial model on a 120 m citywide grid …". This is the B13 finding fix in commit `8686f12`.
- **Primary summary:** max depth 7.85 m, 368.54 km² flooded, 81,935 buildings, 197 wards.

## 3 Outputs for the primary run (frame 48)

Every output was validated against C4 v3 with no schema errors. The SHA-256 is over the response body after gzip decoding.

| Output | Status | Bytes | SHA-256 |
|---|---|---|---|
| `/depth` | 200 | 717,093 | `c4dc137ff391cf47…` |
| `/flow` | 200 | 2,167,453 | `a9c15ebb8d4423c3…` |
| `/wards` | 200 | 55,828 | `b15e9e249dfad447…` |
| `/roads` (bbox Velachery–Adyar) | 200 | 3,065,825 | `903bd9f2a7440d95…` |
| `POST /v3/routes` | 200 | 12,445 | `0bbc54109ca47883…` |
| `/shelters` | 200 | 224,798 | `fcf5500b5bb94b0b…` |
| `/incidents` | 200 | 2,779,425 | `4788554dfe48d235…` |

Full hashes are in the evidence JSON. All seven outputs were also fetched for the acceptance-body run and for the B48 run `fb36a1cd`.

**Pairing with the UI run.** I normalised `run_id` and compared each output body against the same body for `fb36a1cd`. All seven are content-identical.

## 4 Packaged UI (B48)

The UI evidence is B48's screenshots of run `evt-20261108T141229Z-fb36a1cd` (`docs/ui/screenshots/16_g5_flood_simulation.webp` and `16_g5_digital_twin.webp`, commit 25d8cc1). Mapping: packaged primary run `evt-20261108T152128Z-59eba744` = `fb36a1cd` (same engine output, identical bodies per §3).

- **How they were captured:** against the live `/api/ai/v3`, but through the Vite dev server, not the packaged nginx stack.
- **Packaged UI build:** `http://127.0.0.1:8081/` returned 200. Its main bundle contains `/api/ai/v3` and the "DEMO / SIMULATION" badge, and contains no `AIza` key.
- **Not done:** I did not take new screenshots of the packaged UI.

## 5 Determinism

Repeating the primary request returned `state: cached` with the same `run_id`. All seven output hashes were byte-identical on refetch.

## 6 Fail-closed

Every error body was a C4 v3 `ApiError` that passed schema validation, with no partial bodies.

| Check | Expected | Got |
|---|---|---|
| Unknown run `evt-20200101T000000Z-deadbeef` | 404 | 404 |
| `/flow` on the pre-2.1.0 run `evt-20261108T090744Z-b0d2d2bc` | 503 | 503 |
| `/depth?frame_index=9999` | 422 | 422 |
| `/flow?frame_index=9999` | 422 | 422 |
| Queue over limit: six distinct 6 h custom runs, 2.2 s apart | 409 on the sixth | 202 ×5, then 409 |

The five accepted queue-test runs were genuine CPU computes. Three completed. The last two were still running or queued when the stack stopped; on the next service start the run store marks them failed ("interrupted by a service restart").

## 7 Boundaries

- **Raw audit:** `DATA_FILES=157; HASH_MATCH=157; MISMATCH=0`.
- **Database:** the B11 stack has no database service and made no shared-database writes. The other compose project's `tiwnguard-db-1` was left untouched.
- **Docker volumes:** none deleted. B11 uses bind mounts only, with one writable run store at `data/features/v3/runs`.
- **Google key:** 47 calls scanned (request and response bodies), with no `AIza`, `VITE_GOOGLE` or `GOOGLE_MAPS` markers.

## Optional: CR-012 replay route

`GET /api/ai/replay-alerts/replay:POONDI:date:2015-12-01` returned 200 (3,847 B, SHA-256 `06721441…71539`). The body is C4-v2 with `source_observation.event_id` = `replay:POONDI:date:2015-12-01` and `source_mode` REPLAY.

## Limitations

- **Reused engine output.** The acceptance-body and primary runs took 4.1 s because they reused engine output; the 36 h run shows the real CPU compute time in the container.
- **Device field on reused runs.** On runs that reuse engine output, `provenance.device` describes how that output was computed (the RTX 3050), not the CPU container that served it.
- **GPU image.** The GPU image (`docker-compose.gpu.yml`) was not built.
- **UI screenshots.** They come from B48 on the dev server; the packaged UI was checked through its build output only.
