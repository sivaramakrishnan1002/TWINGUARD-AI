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
