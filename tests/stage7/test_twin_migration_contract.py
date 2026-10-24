from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "database/migrations/010_create_twin_schema.sql"


def test_twin_migration_models_required_entities_and_provenance():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    for fragment in (
        "create schema if not exists twin",
        "twin.event_replays",
        "twin.grid_zones",
        "twin.grid_state_artifacts",
        "twin.road_edge_state",
        "twin.facility_state",
        "twin.reservoir_state",
        "twin.model_versions",
        "twin.state_runs",
        "twin.scenarios",
        "twin.alerts",
        "source_sha256",
        "2021-11-01",
        "2023-11-25",
    ):
        assert fragment in sql


def test_grid_state_is_referenced_as_artifacts_not_cell_rows():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "create or replace view twin.grid_zones" in sql
    assert "create table if not exists twin.grid_zone_state" not in sql
    assert "relative_path text not null" in sql
    assert "sha256 text not null" in sql
