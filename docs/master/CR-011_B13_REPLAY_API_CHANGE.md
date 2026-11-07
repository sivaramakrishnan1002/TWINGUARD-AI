# CR-011 — B13 historical replay lookup and packaged UI

**Status: project-owner approved, conditional on a uniquely verified source-backed fixture.** Approval authorizes only the read-only, test-scoped routes and narrow backend CORS described here. It does not verify a fixture, publish active projections, mount routes, change G0, or alter frozen C4 v0/C4 v1 or C1–C8. C9 remains separate, proposed, and unfrozen.

## Why change control is needed

B13 requires a source-labelled historical `REPLAY` result to pass through a mounted backend route and appear in the packaged UI. Existing B08 operations do not provide that result: `/impact` returns an A07 result with `source_mode=SIMULATED`, and `/route-results/{result_id}` returns an A09 revision-3 result with `source_mode=SIMULATED` and `run_id=null`. Relabeling either as `REPLAY` would be false.

The existing `docs/trackb/replay_2015_alerts.jsonl` is a historical replay artifact, but it predates B19's approved C3 date-only representation. Its POONDI 2015-12-01 row (line 37) contains a synthetic `observed_at`/valid interval and `date_timezone=Asia/Kolkata` with timezone status `DEFAULT, to confirm`. It cannot be served as-is. Current B19 producer/replay semantics instead use `source_date`, null `observed_at`, unknown timezone, a separate `received_at`, and null alert validity bounds for date-only sources. A Lane B owner must produce and verify a dedicated normalized fixture before runtime work.

## Proposed bounded flow

Subject to source-owner verification and project-owner approval, add an additive C4 v2 request/operation delta, leaving C4 v0 and v1 documents unchanged:

1. AI service exact read-only lookup: `GET /replay-alerts/{event_id}`.
2. Spring backend exact read-only route: `GET /replay-alerts/{event_id}`, which calls only the AI lookup over the local B11 service network and returns its validated response unchanged.
3. Static packaged UI selection/display for exactly one test-scoped replay result through the backend route. No proxy or runtime status API is added.

Candidate fixture identity, to be verified by Lane B before enabling the operations:

- Source record: POONDI, calendar date `2015-12-01`, from the recorded B9 replay candidate / source-derived replay path.
- Exact date-precision event key under the current B19 replay identity rule: `replay:POONDI:date:2015-12-01`.
- This key is a candidate, not a claim that the normalized fixture currently exists. The owner must demonstrate exactly one matching result produced under current B19 semantics and record its fixture hash. If it is absent or ambiguous, stop and select no substitute without owner evidence.

## Proposed response mapping

Return the validated `trackb.alert.v1` date-only representation already specified in `docs/trackb/MESSAGES.md`:

- `schema=trackb.alert.v1`, exact `event_id`, `source=replay`, `time_precision=date`, and exact `source_date=2015-12-01`.
- `observed_at=null`, `observation_timezone=unknown`, and `valid_from=null`, `valid_to=null`. The UI must not synthesize midnight, an offset, a validity interval, or sub-day ordering.
- Preserve `received_at` as the separate ingestion/replay processing timestamp; preserve `reservoir_key`, rule version, target assumptions, trigger-input nulls, provenance/source-file/hash, and the source's unknown-time limitation.
- Preserve field meanings and units: storage/capacity `mcft`, release `cusecs` or null, rain `mm`, storage/rise percentages as documented, and confidence as rule-decision confidence rather than release probability. Null remains null; unknown is not zero.
- Display explicit historical REPLAY and research-only labels. Do not present the alert as live, current, operational, a warning, safe guidance, or validated flood science.

Proposed error behavior: 400 invalid selector/input; 404 no exact result; 409 duplicate/ambiguous identity; 503 missing, unreadable, or hash-invalid fixture with no partial result. The backend preserves the AI status/body mapping. The lookup is bounded to one allowlisted fixture and GET-only.

Because the static browser at `http://127.0.0.1:8081` must call the backend directly, this proposal also requests a narrow backend CORS policy: that exact origin, GET, and `Accept` only; credentials disabled. It does not request broader B24 AI CORS, a proxy, or public binding. The B11 backend remains loopback-bound.

## Project-owner decision recorded — 2026-10-31

The project owner approved the following bounded change, subject to the constraints listed below:

1. Add the separately versioned C4 v2 AI and Spring backend exact replay lookup operations described above; frozen C4 v0/v1 and C7/C8 response schemas stay unchanged.
2. Permit the date-only `trackb.alert.v1` response mapping above, conditional on Lane B proving the exact source-date fixture and hash; historical measurement time/timezone remain unknown.
3. Permit backend CORS only for `http://127.0.0.1:8081`, GET, `Accept`, with credentials disabled, for the static packaged UI to call the backend directly.
4. Permit enabling the route only in the local B11 test-scoped package, default-disabled elsewhere; no shared database, database migration, Docker volume, live feed, or operational service behavior.

Approval does not close G5. Do not publish active OpenAPI projections, mount routes, or start B27 until Lane B has verified the exact source-backed fixture and I22 has completed the projection review. No live feed, operational behavior, database write, migration, shared data access, or service exposure is authorized.

Approval constraints recorded from the owner:

- Keep C3 date-only semantics: preserve the calendar source date; observation time and timezone remain unknown; ingestion time is separate.
- Never synthesize midnight or validity intervals, and never relabel `SIMULATED` results as historical `REPLAY`.
- Select only a uniquely evidenced source-backed fixture with recorded provenance and hash.
- Keep routes read-only and test-scoped; do not enable live feeds or operational behavior.
- G5 remains open until the verified fixture flows through the mounted backend route into the packaged UI and all B13 acceptance checks pass.

### G5 scope recommendation pending fixture evidence

Keep the registered G5/B13 scope unchanged: a source-labelled historical Track B `REPLAY` result must traverse the approved AI lookup, mounted backend route, and packaged UI. This is distinct from B9's pipeline replay and B18/I08's A20 visualization. The evidence-supported next step is for Lane B to attempt the exact current candidate using the existing source-backed replay path and B19 semantics. If that path produces exactly one qualifying alert, preserve it as an immutable fixture and record source/fixture hashes. If the candidate is absent, ambiguous, or violates the date-only contract, stop and return the observed result to the project owner for a scope decision. Do not substitute a synthetic row, a different date, a `SIMULATED` A07/A09 output, or a C9 visualization. This recommendation does not change G5 acceptance or claim readiness.

## Owner sequence

- **Lane B B28:** produce or reject the candidate fixture using source-backed replay inputs only; record exact identity, raw-source and fixture hashes, uniqueness, date-only fields, tests, and limitations. If no fixture qualifies, stop and request the scope decision described above.
- **Integrator I22:** after B28 evidence, publish the approved additive C4 v2 AI/backend projection and conformance tests. Preserve C4 v0/v1 and C7/C8.
- **Lane B B27:** after B28 and I22, implement the test-scoped AI lookup, backend route/CORS, and packaged UI. Keep B13 blocked until B27 completes with runtime evidence.
- **Lane B B13:** perform the separately registered full-stack replay acceptance using the approved route and package. B9 pipeline replay and B18/I08 saved A20 visualization do not substitute.

## I21 review conclusion — 2026-10-31

**Disposition: CR-011 route/CORS scope is approved conditionally; B27 and B13 remain blocked.** The approval is recorded above. It does not override C3 or establish that an eligible fixture exists.

### Fixture compatibility finding

- The legacy `docs/trackb/replay_2015_alerts.jsonl` POONDI row for `2015-12-01` is not compatible. It contains `observed_at="2015-12-01T00:00:00+05:30"`, the same synthetic `valid_from`, a next-day `valid_to`, and provenance `date_timezone="Asia/Kolkata"` / `timezone_status="DEFAULT, to confirm"`. Serving it would contradict C3's approved date-only policy. It remains untouched.
- `pipelines/trackb/replay.py` implements a date identity of `replay:{RESERVOIR}:date:{source_date}` and emits null observation/validity instants for date precision, with `received_at` separate. `tests/trackb/test_date_only_timestamps.py::test_replay_alerts_keep_date_only_and_supplied_timestamp_offset` verifies those rules on an in-memory test row. It does not prove that an immutable, source-backed POONDI alert was actually produced, uniquely selected, or saved with a stable fixture hash.
- B19's date-only producer/consumer tests and B20's isolated persistence evidence establish representation and persistence behavior within their recorded scopes. They do not identify a saved B13 fixture. B9's historical REPLAY is separate pipeline evidence; its recorded output predates B19 normalization. No database was accessed for this review.
- B08's exact A07 `POST /impact` and A09 `GET /route-results/{result_id}` selectors return `source_mode=SIMULATED`; neither can satisfy a historical `REPLAY` selector without mislabeling. A20/C9 assets are separate saved research visualization outputs.

Therefore the candidate selector `replay:POONDI:date:2015-12-01` is implementation-derived but not yet an evidenced existing fixture. No alternate date, result, or identity is selected by inference. There is not currently a specific verified fixture that can be projected for G5 without risking a C3 contradiction.

### Remaining fixture evidence needed

The route/CORS decision is now approved conditionally. CR-009/CR-010 and the earlier date-only policy are not used as substitute approval; the explicit CR-011 approval is recorded in this document.

Lane B must provide owner evidence before I22/B27 can proceed: a normalized alert fixture from the source-backed replay path; exact event ID and source-date-to-source-row mapping; raw source/archive and fixture SHA-256; evidence of exactly one selector match; preserved `source=REPLAY`, `source_date`, null `observed_at`/`valid_from`/`valid_to`, unknown timezone, separate `received_at`, provenance and null inputs; plus focused tests or a report showing these facts. If the POONDI candidate is absent or ambiguous, Lane B must stop and present observed evidence for a project-owner G5 scope decision rather than silently substituting another record.

Until the Lane B fixture evidence exists and I22 completes the approved projection review, do not edit the active AI/backend OpenAPI projections, mount routes, or start B27. I21 is complete with caveats; C1-C8 remain frozen at v0, C3 historical measurement-time meaning/timezone remain unknown, C9 remains proposed/unfrozen, G0 remains unchanged, and G5 remains not ready pending B13.

### I21 validation record

- `python tools/validate_api_contracts.py` — PASS; AI OpenAPI 3.1.0 (11 paths, 11 operations), backend OpenAPI 3.1.0 (10 paths, 11 operations). These existing projections were validated as found; no CR-011 operation was added.
- `.venv\Scripts\python.exe -m pytest -q --import-mode=importlib tests\master\test_api_contract_projection.py tests\ai_service\test_api.py tests\trackb\test_date_only_timestamps.py` — **38 passed**, one existing Starlette/httpx deprecation warning.
- `git diff --check -- docs/master/CR-011_B13_REPLAY_API_CHANGE.md` — PASS.
- `python tools/master/verify_state.py` — PASS (exit 0; its read-only DB check reported `ModuleNotFoundError`, so that optional database probe was unavailable; no database was accessed).
- `python tools/master/gate_check.py G0` — `G0 READY: all C1-C8 checklist criteria and evidence paths pass` (existing recorded G0 result, unchanged).
- `python tools/master/gate_check.py G5` — `G5 CLOSED: tasks incomplete: B13`.
- `python tools/master/gate_check.py G6` — `G6 CLOSED: tasks incomplete: I04`.
- A, B, and I selectors exited successfully with no ready task printed after I21 finished; no task was claimed or started in another lane.

## Follow-up after conditional approval — 2026-10-31

The project-owner approval in this record resolves the route/CORS decision, subject to fixture qualification. A second repository search found no normalized immutable date-only alert fixture: the only matching POONDI 2015-12-01 record is still the incompatible legacy JSONL row; B19's test row is in-memory test input, not saved source-backed output. No data was generated during this Integrator review.

The recommended G5 scope decision is to retain B13's registered source-backed historical REPLAY vertical slice unchanged while Lane B verifies whether the existing candidate actually produces one qualifying date-only alert under the current replay code. B28 now owns that fixture evidence check. If it proves a unique result, I22 can publish the approved additive C4 v2 projection, then B27 may implement the test-scoped route/UI flow. If it proves no qualifying result, B28 must stop without a substitute and return the source/result evidence for an explicit project-owner G5 scope decision. This preserves the current gate meaning and avoids inventing an alert or broadening acceptance by inference.

Master state records B28 as ready, I22 as blocked on B28, and B27/B13 as blocked on the ordered evidence and implementation. G0, C1-C8, C3 semantics, C9, and G5 status are unchanged. No OpenAPI projection or Lane B implementation path was edited.

## Superseded B13 scope note — CR-012

The project owner later approved CR-012, replacing B13's requirement for an existing saved historical alert outcome with a replay of one source-backed date-only reservoir observation and explicit separation of source input from any derived system output. The CR-011 alert-lookup proposal is therefore not the B13 implementation contract. Its C3 safeguards and narrow read-only boundary remain applicable; its alert response shape must not be reused to imply the observation itself was a historical alert. See `docs/master/CR-012_G5_DATE_ONLY_OBSERVATION_REPLAY.md` for the approved scope and updated task sequence.
