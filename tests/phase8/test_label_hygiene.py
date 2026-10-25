from pipelines.stage5.db_common import make_engine
from sqlalchemy import text


def test_stage8_candidates_are_rejected_and_usable_view_is_tier_limited():
    engine = make_engine()
    try:
        with engine.connect() as connection:
            rejected = connection.execute(text("""
                SELECT tier, review_status, count(*)
                FROM labels.derived_flood_polygons
                GROUP BY tier, review_status
            """)).fetchall()
            assert rejected == [('D', 'REJECTED_PENDING_REWORK', 45096)]
            outside_tier = connection.execute(text("""
                SELECT count(*) FROM labels.v_usable_flood_labels
                WHERE tier NOT IN ('A', 'B', 'C') OR NOT is_valid OR NOT in_cma
            """)).scalar_one()
            assert outside_tier == 0
            official = connection.execute(text("""
                SELECT count(*) FROM labels.v_usable_flood_labels WHERE tier = 'A'
            """)).scalar_one()
            assert official > 0
    finally:
        engine.dispose()
