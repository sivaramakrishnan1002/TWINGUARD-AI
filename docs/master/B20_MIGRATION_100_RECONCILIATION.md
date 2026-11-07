# B20 migration-100 checksum reconciliation — 2026-10-28

**Disposition: recoverable checksum-comparison mismatch; B20 may resume against its already authorized isolated target.** This was a read-only investigation. No migration was applied, no fixture was written, no ledger value was edited, and neither Docker nor shared `twinguard` was modified. Migration 101 remains absent/unapplied.

## Exact checksum evidence

- B20's blocked note said the migration-100 ledger checksum differed from the checked-in file, but did not record either hash or the algorithm used.
- `pipelines/stage5/apply_migrations.py` defines the authoritative checksum algorithm: `path.read_text(encoding="utf-8")`, then SHA-256 of that decoded text re-encoded as UTF-8. This normalizes platform newline translation; the comparison below reproduces that exact implementation rather than assuming equivalence from SQL appearance.
- `database/migrations/100_trackb_twin_link.sql`, using the migration runner's exact algorithm: `5caaa99191ecc96cb1e36a923b67151679ea2b226910bb246bf7041f327a48b0`.
- Git history contains one migration-100 commit on `--follow`: `b0d123e` (`Complete Track B streaming metrics and runtime evidence`). SHA-256 of that exact Git blob: `5caaa99191ecc96cb1e36a923b67151679ea2b226910bb246bf7041f327a48b0`. `git status --short -- database/migrations/100_trackb_twin_link.sql` was empty; no unstaged SQL edit exists.
- The isolated database ledger row for `100_trackb_twin_link.sql`: `5caaa99191ecc96cb1e36a923b67151679ea2b226910bb246bf7041f327a48b0`. Thus the ledger identifies the exact SQL blob retained in Git history and matches the runner-computed checksum.
- SHA-256 of raw working-tree bytes was `b35b60bc52604929777c57766d9832758b16f7437bb82693ea3beff6edde63b2`; this is not the migration runner's checksum input. B20's mismatch is explained by comparing a raw-byte hash with a decoded/normalized-text ledger hash. The exact runner computation, Git blob, and ledger match; no migration-content restoration or ledger repair is warranted.

## Read-only isolated database identity and migration state

The inspection connection explicitly selected `twinguard_trackb_test` and set PostgreSQL `default_transaction_read_only=on`. It reported `transaction_read_only=on`, `current_database=twinguard_trackb_test`, `current_user=twinguard_app`, database owner `twinguard_app`, and `datistemplate=false`. No connection values or credentials were printed.

Ledger checksums for 001, 005, and 010 also matched the migration runner's current computations. Migration 101 was not in the ledger. The three migration-100 relations exist: `trackb.alert_events`, `twin.trackb_alert_links`, and `twin.trackb_recompute_markers`.

Read-only catalog metadata matches migration 100's expected object definitions:

- `trackb.alert_events`: `event_id` text primary key; `source` text with replay/live/simulated check; `observed_at` timestamptz NOT NULL; `payload` jsonb NOT NULL; `created_at` timestamptz NOT NULL default now().
- `twin.trackb_alert_links`: `event_key` text primary key; `alert_id` bigint NOT NULL, unique and FK to `twin.alerts(alert_id)` with `ON DELETE CASCADE`; `source` text with replay/live/simulated check; `created_at` timestamptz NOT NULL default now().
- `twin.trackb_recompute_markers`: `marker_key` text primary key; `reservoir_key` FK to `twin.reservoirs`; `valid_at` timestamptz NOT NULL; `source` with replay/live/simulated check; JSONB `payload` default `{}`; `created_at` default now(); nullable `consumed_at`; and `trackb_recompute_pending_idx` on `created_at` where `consumed_at IS NULL`.

These timestamp constraints are expected for migration 100 and explain why date-only observations need migration 101's separate date-keyed relations. They do not establish B20's date-only persistence; that remains untested against PostgreSQL.

## Other provenance sources and precedent

- `git log --all --follow -- database/migrations/100_trackb_twin_link.sql` identifies only the commit above; no alternate migration-100 source copy appears in tracked repository files. Repository searches found no deployment log or checksum manifest with a different applied SQL version. Existing `backups/` files are dated 2026-10-24 and are not identified as the isolated `twinguard_trackb_test` migration-100 deployment artifact; they cannot establish a different applied version.
- `docs/ISSUES.md` documents the earlier 001 checksum repair: restore the already-applied SQL contents and move later additive work into a new migration. That remedy is not applicable here because the applied ledger hash, migration runner hash, and authoritative Git blob all match exactly. Do not edit migration 100 or the ledger.
- Read-only inspection used `psycopg` against the explicit isolated database with `options='-c default_transaction_read_only=on'`; queries read only identity, ledger, catalog columns, constraints, and indexes. No fixture write, migration, transaction commit, Docker operation, or shared-database connection was made for this reconciliation.

## Task disposition and boundary

B20's blocker was an algorithm mismatch in the checksum comparison, not unknown migration provenance. B20 is returned to `ready` with the fixed target `twinguard_trackb_test`; it must repeat identity/owner/isolation and migration-ledger preflight immediately before any write. Its conditional task authorization to apply migration 101 remains limited to that exact test database. If any preflight value differs, stop with no write and request DBA provisioning/reconciliation before changing the task's target or authorization.

B20 must still apply/test migration 101 only after that preflight and prove date-only and genuine timestamped persistence/read-back/idempotency. I11 remains blocked pending B20 completion. Historical measurement-time meaning and timezone remain unknown; C3 remains v0/unfrozen and G0 `not_ready`.

Validation: `git diff --check` on the Integrator records passed; `verify_state.py` and the Integrator selector are recorded after this reconciliation.
