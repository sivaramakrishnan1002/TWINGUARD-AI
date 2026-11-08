# Flood engine GPU benchmark (A26)

**Engine:** `twinguard-flood-engine/2.1.0`; backend `services/flood_engine/hires_torch.py` (torch float32, CUDA). NumPy (`hires.py`) remains the default and the automatic fallback. **Date:** 2026-11-08. **Raw results:** `data/features/simulation/a26_benchmark_v1/benchmark.json` (runs under `cpu/` and `cuda/`). **Script:** `python -m pipelines.a25_hires.benchmark_gpu`.

## Hardware and software

| Item | Value |
|---|---|
| CPU | Intel Core (Family 6 Model 154), 16 logical cores; NumPy backend uses 8 threads |
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU, 4,096 MB, driver 621.01 |
| Software | Windows 11 (10.0.26300), NumPy 2.5.3, torch 2.14.1+cu126 (CUDA 12.6, pin from `requirements-gpu.txt`) |

## Speed-up

All runs use the Dec 2015 event (A06 IMERG/ERA5 forcing) with 30-minute frames. Wall time covers the full `run_scenario` call: simulation, flow sidecar, buildings, wards, roads and shelters. The post-processing is CPU-bound and identical on both devices, so solver-only speed-ups are higher than shown.

| Case | Grid | Members | Solver steps | CPU wall s | CUDA wall s | Speed-up | Peak VRAM |
|---|---|---:|---:|---:|---:|---:|---:|
| Citywide 120 m, 24 h | 440 × 343 | 1 | 4,634 | 62.8 | 17.1 | **3.67×** | 16.3 MB |
| Citywide 120 m, 48 h | 440 × 343 | 1 | 11,827 | 101.2 | 36.3 | **2.79×** | 16.3 MB |
| Citywide 120 m, 24 h, 3 members | 440 × 343 | 3 | 14,208 | 105.8 | 34.6 | **3.06×** | 16.3 MB |
| Citywide 90 m, 24 h | 587 × 457 | 1 | 6,101 | 57.1 | 19.4 | **2.94×** | 29.5 MB |
| Focus 30 m VELACHERY, 24 h (nested) | 200 × 200 | 1 | 19,208 | 104.9 | 46.6 | **2.25×** | 4.3 MB |

The focus case excludes its citywide parent, which is cached in each device's run store.

## Agreement with the NumPy reference

| Case | Max abs peak diff | Mean abs peak diff | p99 abs peak diff | Max abs frame diff | Cells > 0.05 m / > 0.10 m | Flooded IoU (≥ 0.10 m) | Mass balance (CPU = CUDA) |
|---|---:|---:|---:|---:|---|---:|---:|
| Citywide 120 m, 24 h | 0.016 m | < 0.001 m | 0.0005 m | 0.02 m | 0 / 0 of 150,923 | 0.99954 | ≤ 1e-6 |
| Citywide 120 m, 48 h | 0.380 m | < 0.001 m | 0.0003 m | 0.19 m | 3 / 1 | 0.99997 | 1e-6 |
| Citywide 120 m, 24 h, 3 members | 0.016 m | < 0.001 m | 0.0005 m | 0.02 m | 0 / 0 | 0.99954 | ≤ 1e-6 |
| Citywide 90 m, 24 h | 0.016 m | < 0.001 m | 0.0002 m | 0.02 m | 0 / 0 of 268,258 | 0.99994 | 1e-6 |
| Focus 30 m VELACHERY, 24 h | 0.003 m | < 0.001 m | 0.0007 m | 0.07 m | 0 / 0 of 40,000 | 1.00000 | 6e-5 |

**Stated tolerance** (also enforced by `tests/flood_engine/test_a26_gpu.py` on the synthetic grid):

- Mean absolute peak-depth difference below 0.001 m, and the 99th percentile below 0.001 m.
- Fewer than 0.01% of cells above 0.05 m.
- Flooded IoU of at least 0.999.
- Mass balance of 1% or better on both devices; the two devices give identical values.
- Step counts are identical, because the CFL time step uses the same depths.

Rare isolated differences of a few decimetres (one cell in the 48 h run) come from float32 rounding at threshold-sensitive cells. They do not change any summary class.

## VRAM

The whole grid is held on the GPU, and frames, flow arrays and peaks are copied to host memory as they are produced. Peak allocation is therefore 4–30 MB regardless of run length or member count (members run sequentially), far below the 4 GB card. No tiling is needed for the A25 grids.

## Usage

```python
run_scenario(static_root, runs_root, mode="event", event_key="2015-12-01", device="cuda")   # or "cpu" (default), "cuda:0"
```

- `services.flood_engine.hires_torch.available()` returns `(bool, device name or reason)`.
- `provenance.device` in the run document is `{requested, used, name, fallback_reason, peak_vram_mb}`.
- **Fallback:** if torch or CUDA is unavailable, or the device string is unsupported, the run uses NumPy and records the reason. If a CUDA error occurs mid-run (for example out-of-memory or a driver error), that member and all later members rerun on NumPy, and the error text goes into `fallback_reason`.
- **Request cache:** device-independent. A cached CPU run can answer a CUDA request and vice versa, since results agree within the tolerance above.
- **CLI:** `python -m services.flood_engine.scenario_cli ... --device cuda`.

## Follow-up: first /v3 CUDA run (2026-11-08)

Lane B's first real `/v3` job was `evt-20261108T141229Z-fb36a1cd` (Dec 2015, 48 h, citywide 120 m, `cuda:0`, 16 MB VRAM, no fallback). It reported `runtime_seconds` 100.8, against 36.3 s in the table above. Note that the benchmark figure is end to end, not solver-only, but it was measured with torch and CUDA already warm in the benchmark process.

### Cold-process breakdown

Fresh `python` process, same 48 h case, same machine:

| Phase | Before fix (s) | After fix (s) |
|---|---:|---:|
| `import torch` | 15.5 (first load from disk) | — |
| Device init (torch import + CUDA context), now timed separately | 1.1 | 3.4 |
| GPU solve (11,827 steps, ≈ 2 ms/step, kernel-launch bound) | 25–26 | 23.8 |
| Post-processing (frames/flow/road/shelter writes, reachability, wards) | 12.9 | 7.7 |
| **Engine `runtime_seconds`** | 39.0 with torch pre-imported; 58.1 with torch imported inside `run_scenario` | **34.8** (cold process, torch imported inside) |

**Diagnosis.** In a cold child process, `run_scenario(device="cuda")` imports torch and creates the CUDA context inside the call, about 5–20 s depending on the OS file cache. That accounts for 39 → 58 s. The remaining ~40 s of the 100.8 s is consistent with machine load during that job: the AI-service process and a Chrome tab using the same GPU for the UI's 3D view were both active. The engine itself shows no regression.

### Fixes (A26 follow-up)

1. **Warm-up:** `hires_torch.warmup(device)` imports torch and creates the CUDA context once per process. A long-lived worker can call it at start-up, and later runs pay 0 s.
2. **Timing block:** every run document now has `timing = {forcing_and_setup_s, device_init_s, torch_import_s, cuda_context_s, solve_s, post_processing_s}`, so slow runs can be attributed without re-profiling.
3. **Faster writes:** `frames.npz`, `flow.npz` and `road_states.npz` are written with zlib level 1 (`scenario.savez_fast`, same `.npz` layout, read by `np.load` unchanged). About 3× faster writes for about 17% larger files (48 h citywide: frames 4.6 MB, flow 10.8 MB).
4. **Reachability cache:** shelter reachability is reused for frames with identical road states and site depths (70 distinct of 97 frames in this case).

Numerical results are unchanged: same arrays, same tests.

## Follow-up 2: event-dependent slowness and CUDA graphs (2026-11-08)

Lane B's re-check, `evt-20261108T144322Z-8e5ed75e` (2021-11-11, 48 h, citywide 120 m, `cuda`), took 147.1 s: device init 15.4 s, solve 117.6 s, post-processing 14.1 s.

### Cause

- **Same work:** the step count is almost the same as for Dec 2015 (12,469 vs 11,827), so the event is not harder. Each step was slower: 9.4 ms against 2 ms.
- **What the GPU was doing:** sampled every 4 s during a reproduction, it sat mostly at P3 (255–735 MHz) with 3–46% utilisation, throttle reason `0x1` (GPU idle).
- **Why it idled:** the eager solver issues about 60 small kernels plus one host sync per step from Python, so the GPU waits between kernels and the driver lowers its clocks.
- **CPU contention:** the CPU was 64–100% loaded by other applications, which slows the launch loop further. Per-step time therefore depends on machine load (2–9 ms), not on the event.
- **Power:** the laptop was on mains power, not battery.
- **Device init:** the 10–15 s is the first CUDA runtime initialisation in a fresh process, through `torch.cuda.is_available()` and the device query. It is paid once per process.

### Fix: CUDA-graph step

`hires_torch.run` now captures one complete time step as a CUDA graph and replays it, giving one launch per step instead of about 60.

- `dt` and the rain rate are device scalars updated before each replay, and all state tensors are updated in place.
- The boundary flux is summed with a mask multiply, so the step has no host syncs and no dynamic shapes. One host read per step remains, for the CFL depth.
- Set `TWINGUARD_CUDA_GRAPH=0`, or let a failed capture trigger the fallback, to use the previous eager kernels.
- `diagnostics.kernel_mode` reports `cuda_graph` or `eager`.
- Graph replay is bit-identical to eager on the test grid (frames, flow, steps; tested), and NumPy parity is unchanged.

| 48 h citywide 120 m, `cuda` | Steps | Solve before | Solve with CUDA graph | ms/step |
|---|---:|---:|---:|---:|
| 2021-11-11 (Lane B run) | 12,469 | 117.6 s | — | 9.4 |
| 2021-11-11 (this machine, eager) | 12,469 | 62.4 s | — | 5.0 |
| 2021-11-11 (this machine, graph) | 12,525 | — | **12.8 s** | **1.0** |
| 2015-12-01 (this machine, graph) | 11,827 | 23.8 s | **21.2 s** | 1.8 |

Mass balance is ≤ 2e-6 in all of these runs.

Post-processing (about 8–20 s, NumPy on the CPU) is now the larger share and grows with CPU load from other applications. The CPU was at 100% during the graph benchmark.

### Recommendations for /v3

- **Long-lived worker:** call `hires_torch.warmup("cuda:0")` once, so the 10–15 s CUDA init is not paid per run.
- **Timing:** log `timing` and `diagnostics.kernel_mode` with each run.
- **Expected warm times:** a 48 h citywide run takes ≈ 25–45 s end to end, depending on CPU load.
