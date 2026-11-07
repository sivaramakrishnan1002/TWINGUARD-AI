# C6 twin schema v0

The base `twin` schema is created by migration 010. Track B migration 100 links replay/message alerts and reservoir state to twin records. Serialization is relational PostgreSQL scalar columns for unit-bearing state, `jsonb` for nested payload/provenance/manifest structures, and external artifacts identified by media type/path/hash. Offset-bearing JSON timestamps map to `timestamptz`; nullable measurements remain NULL (unavailable), not zero. Run/event/version/source and artifact hashes provide provenance; idempotency keys/unique markers prevent duplicate replay writes.

Evidence: migrations 010/100, `pipelines/trackb/persistence.py`, `docs/trackb/G0_REPAIR_EVIDENCE.md`, and isolated database/run evidence in `docs/trackb/RUNBOOK.md`. Migration 100 and B9 persistence/replay were applied only to `twinguard_trackb_test`; shared `twinguard` remains without migration 100. B9 is REPLAY evidence and proves isolated serialization/persistence/idempotency and recorded Kafka/Redis/Prometheus replay behavior, not live feed or production operation. Do not claim shared DB integration or operational twin state.

The serialization mapping and isolated replay are evidence-backed. Shared integration/runtime compatibility is not asserted. C6 is frozen at v0 for G0. Shared integration/runtime compatibility is not asserted.
