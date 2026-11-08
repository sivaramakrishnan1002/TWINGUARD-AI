# A27 — Per-frame flow velocity and water-surface export

**Engine:** `twinguard-flood-engine/2.1.0`. Runs from 2.1.0 onwards write `flow.npz` next to `frames.npz`. Runs from 2.0.0 are unchanged and stay readable; the flow readers raise `products.FlowUnavailable` for them, which Lane B serves as 503.

## What is saved

`flow.npz` covers every saved frame of the central member:

| Array | Shape / type | Meaning |
|---|---|---|
| `u` | [frames, rows, cols] int16 | Eastward (+x) depth-averaged velocity, 0.01 m/s units |
| `v` | [frames, rows, cols] int16 | Northward (+y) depth-averaged velocity, 0.01 m/s units |
| `wse` | [frames, rows, cols] int16 | Water-surface elevation relative to `wse_offset_cm`, 0.01 m units |
| `wse_offset_cm` | [rows, cols] int16 | Per-cell bed offset (cm). Decode `wse_m = (wse + wse_offset_cm) × 0.01` |
| `scale`, `nodata`, `wet_threshold_m` | scalars | 0.01, −32768, 0.01 m |

- **Grid and CRS:** the run's C4 v3 GridSpec (EPSG:32644, row 0 north). Values are cell-centred: the mean of the two face discharges per width divided by the cell depth. The solver's row-direction flux points south, so `v = −q_row / h`.
- **Vertical datum:** EGM2008, inherited from the Copernicus GLO-30 heights of the engine DEM.
- **NoData:** outside the computed domain (including sea and nested-boundary cells), u, v and wse are null. Dry cells (depth < 0.01 m) have u = v = 0 and wse null. Frame 0 is still water (u = v = 0).
- **Unchanged outputs:** depth frames, peaks and peak speed are bit-identical with and without flow recording (tested). `hires.run(..., record_flow=False)` skips the sidecar.

## Readers (`services/flood_engine/products.py`)

- `flow_frame(runs_root, run_id, frame_index, stride=1)` returns the C4 v3 FlowFrame for the proposed `GET /v3/simulations/{run_id}/flow`.
- `velocity_frame(...)` returns u and v only; `wse_frame(...)` returns wse only.
- **Stride** (1–8) takes every n-th row and column starting at (0, 0). The returned `grid` describes the subsampled lattice: `cell_size_m × stride`, with the origin shifted so each subsampled cell is centred on the original sampled cell centre.
- **Errors:** `ValueError` for a bad frame or stride (422); `NotFound` for an unknown run (404); `FlowUnavailable` for a missing or unreadable sidecar (503).

## Size and speed

Measured on the Dec 2015 event, 48 h, 97 frames at 30 min:

| Run | frames.npz | flow.npz | Ratio | `flow_frame` stride 1 | stride 4 |
|---|---:|---:|---:|---|---|
| Citywide 120 m (440 × 343), `evt-20261108T092709Z-ba7ef063` | 3.97 MB | 9.00 MB | 2.27× | ~30 ms after first load, 2.7 MB JSON | ~30 ms, 0.17 MB |
| Focus 30 m VELACHERY (200 × 200), `evt-20261108T093021Z-a4857cea` | 1.67 MB | 3.23 MB | 1.93× | 0.7 MB JSON | 0.04 MB |

- **First read:** the first read of a run decompresses its sidecar once, taking about 0.5–0.8 s citywide. It is cached for the 2 most recent runs, keyed by file modification time.
- **Simulation cost:** unchanged. The 48 h citywide run took 191 s and the nested 30 m focus run 482 s.
- **Unchanged outputs on real data:** both reruns have depth frames and every peak layer identical to the pre-A27 runs `evt-20261107T120140Z-b0df587c` and `evt-20261107T172655Z-b8175ee2`.
- **Peak speeds:** at frame 60 the maximum speed is 0.49 m/s citywide and 3.4 m/s in Velachery, where flow is concentrated in channels.

## Tests

`tests/flood_engine/test_a27_flow.py` covers:
- bit-identical existing outputs;
- east and north sign conventions on tilted planes;
- wse = bed + depth, both in the solver and through the offset encoding;
- speed consistent with discharge/depth;
- dry and NoData cells;
- stride lattice and origin;
- a pre-A27 run without the sidecar;
- invalid frame and stride.
