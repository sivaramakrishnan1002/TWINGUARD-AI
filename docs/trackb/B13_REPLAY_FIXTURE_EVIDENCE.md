# B28 — Source-backed date-only replay fixture evidence

**Disposition: no qualifying fixture exists in the registered immutable outputs.** B28 therefore finishes with caveats and requests an explicit project-owner G5 scope decision. No fixture, replay output, database write, service, or container was created or modified.

## Candidate source record

The read-only source archive is `data/raw/reservoirs/kaggle_chennai_water_management/archive.zip` (SHA-256 `7645febde7ccc21871200487139d1c8a84ea90a6dd2eccc93b7d1f06faf69197`). Its `chennai_reservoir_levels.csv` member has SHA-256 `3b4b6f2f53b5db20513d2829c2dba265c5738a55bf0c8eade51e0e2d5cfeaef7`. The CSV has one matching source row: physical CSV line 4354, `Date='01-12-2015'`, `POONDI='2745.00'`. The source field is a calendar-date string; it contains no observation time or timezone. This establishes a source observation, not a persisted replay alert.

## Exact alert selector and saved-output search

The approved selector is `replay:POONDI:date:2015-12-01`. Under B19, the date key is `replay:{reservoir}:date:{source_date}`. The existing saved alert file `docs/trackb/replay_2015_alerts.jsonl` (SHA-256 `6b5a02e393935ceabf581eaa34ff43585b6d4999d880428b02b22550988b6e54`, 50 lines) contains **zero** records with that exact event ID. It contains one POONDI record whose observed timestamp begins on the candidate calendar date, but that record has the different ID `replay:POONDI:2015-12-01T00:00:00+05:30`, `observed_at` and `valid_from` set to `2015-12-01T00:00:00+05:30`, `valid_to` set to `2015-12-02T00:00:00+05:30`, and provenance `date_timezone=Asia/Kolkata`, `timezone_status=DEFAULT, to confirm`. It is incompatible with C3's date-only semantics and was not changed or served as a substitute.

B19's current producer/replay code represents date precision with `source_date`, `time_precision=date`, `observed_at=null`, `observation_timezone=unknown`, null `valid_from`/`valid_to`, and separate `received_at`. Its existing focused tests use in-memory source rows; they do not establish a saved, uniquely selected POONDI alert or immutable fixture hash. B08 A07/A09 outputs are `SIMULATED` and cannot be relabeled as historical `REPLAY`.

## B28 conclusion and boundary

The archive row is source-backed but is not itself the required replay-alert fixture. No qualifying immutable alert output exists in the registered candidate outputs, and the legacy alert fails the time-semantics checks. The B28 instructions prohibit creating or modifying a fixture; accordingly the replay path was not executed to generate a replacement. The required `docs/trackb/fixtures/b13/poondi_2015-12-01.json` and `tests/trackb/test_b13_replay_fixture.py` were not created. No database was accessed and no services or containers were started.

B27 and B13 must remain blocked. I22 must not publish a fixture-bound projection. The project owner must decide whether to revise G5/B13 scope or separately authorize a source-backed replay production task; do not select another date/result or weaken the existing criteria by inference. G5 remains not ready. C3's historical observation-time/timezone meaning remains unknown.

## Checks

- Read-only archive/CSV inspection: one candidate source row, as identified above; archive and member hashes recorded.
- Read-only saved-alert scan: 50 rows; exact approved selector matches 0; legacy POONDI/date match 1 and is incompatible as detailed above.
- B19 date-semantics focused tests and raw audit results are recorded in the B28 completion notes in the master task history; no new test fixture was available for B28-specific identity/hash tests.
- `.venv\Scripts\python.exe -m pytest tests\trackb\test_date_only_timestamps.py -q --import-mode=importlib` — **5 passed** (existing B19 date-only behavior; no B28 fixture test was possible without a qualifying fixture).
- `.venv\Scripts\python.exe -m py_compile pipelines\trackb\replay.py` — compile check; see B28 completion evidence.
- `.venv\Scripts\python.exe tools\audit_raw_logs.py` — **157 files, 30,544,672,450 bytes; 157 hash matches; 0 without comparable hashes; 0 mismatches**.
- `git diff --check -- docs/trackb/B13_REPLAY_FIXTURE_EVIDENCE.md` — whitespace check.
