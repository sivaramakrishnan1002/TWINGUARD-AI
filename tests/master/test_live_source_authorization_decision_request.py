from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "docs/trackb/live_source_readiness_inventory.json"
PACKAGE = ROOT / "docs/master/live_source_authorization_decision_request.json"
REQUEST = ROOT / "docs/master/LIVE_SOURCE_AUTHORIZATION_DECISION_REQUEST.md"
REQUIRED = {
    "source_id", "category", "candidate_name", "product_or_version", "inventory_status",
    "source_evidence_status", "live_access_verified", "authorized_for_live",
    "owner_and_custodian", "documented_local_access", "authorized_access_path",
    "permission_and_terms", "written_permission_status", "retention_rights",
    "redistribution_rights", "authentication_method", "credential_custodian",
    "credentials_recorded", "update_frequency", "publication_latency",
    "revision_backfill_behavior", "units", "field_meanings", "timestamp_semantics_timezone",
    "coverage_resolution", "provenance_and_existing_hash_evidence", "evidence_paths",
    "known_sample_or_schema_reference", "known_sample_sha256", "missing_and_nodata_behavior",
    "freshness_expectations", "retry_duplicate_and_idempotency_expectations",
    "decision", "required_before_implementation",
}


class LiveSourceAuthorizationRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        cls.package = json.loads(PACKAGE.read_text(encoding="utf-8"))
        cls.request_text = REQUEST.read_text(encoding="utf-8")

    def test_all_rainfall_and_reservoir_candidates_are_carried_forward(self):
        expected = {
            row["id"]: (row["category"], row.get("availability_class", "UNKNOWN"), row.get("live_access_verified", False))
            for row in self.inventory["sources"]
            if row.get("category") in {"rainfall", "reservoir"}
        }
        actual = {row["source_id"]: row for row in self.package["sources"]}
        self.assertEqual(set(actual), set(expected))
        self.assertEqual(self.package["candidate_count"], len(expected))
        for source_id, (category, inventory_status, live_verified) in expected.items():
            row = actual[source_id]
            self.assertEqual(row["category"], category)
            self.assertEqual(row["inventory_status"], inventory_status)
            self.assertEqual(row["live_access_verified"], bool(live_verified))

    def test_each_candidate_has_decision_and_evidence_fields(self):
        for row in self.package["sources"]:
            self.assertTrue(REQUIRED.issubset(row), f"missing fields for {row.get('source_id')}")
            for field in REQUIRED - {"evidence_paths", "known_sample_sha256", "required_before_implementation"}:
                self.assertNotIn(row[field], (None, ""), f"empty {field} for {row['source_id']}")
            self.assertEqual(row["decision"]["status"], "PENDING")
            self.assertFalse(row["authorized_for_live"])
            self.assertFalse(row["credentials_recorded"])
            self.assertEqual(row["freshness_expectations"]["current_threshold"].split(" — ")[0], "PENDING")
            self.assertEqual(row["freshness_expectations"]["stale_threshold"].split(" — ")[0], "PENDING")

    def test_d2_d3_and_d8_are_separate_and_unapproved(self):
        decisions = self.package["decisions"]
        self.assertEqual(set(decisions), {
            "D2_rainfall_source_and_access", "D3_reservoir_source_and_access", "D8_prototype_source_mode"
        })
        self.assertTrue(all(item["status"] == "PENDING" for item in decisions.values()))
        self.assertIn("fixture/replay demonstration only", decisions["D8_prototype_source_mode"]["options"])
        self.assertIn("bounded live prototype using specifically authorized source(s)", decisions["D8_prototype_source_mode"]["options"])

    def test_c3_date_only_policy_and_limits_are_explicit(self):
        c3 = self.package["c3_policy"]
        self.assertIn("date-only", c3["historical_reservoir_source_date"])
        self.assertIn("unknown/null", c3["observation_time_and_timezone"].lower())
        self.assertIn("separate", c3["received_at"].lower())
        self.assertIn("offset", c3["timestamped_sources"])
        for phrase in ("source_date", "received_at", "do not synthesize midnight", "d8", "pending"):
            self.assertIn(phrase, self.request_text.lower())
        self.assertIn("NO_CANDIDATE_VERIFIED_LIVE", self.package["inventory_live_source_readiness"])

    def test_unknown_or_pending_is_preserved_without_live_authorization(self):
        self.assertEqual(self.package["status"], "DECISION_REQUEST_ONLY")
        self.assertTrue(any("Silence" in rule and "authorize" in rule for rule in self.package["no_approval_inference"]))
        self.assertTrue(all(not row["authorized_for_live"] and not row["live_access_verified"] for row in self.package["sources"]))
        self.assertIn("PENDING owner decision", self.request_text)


if __name__ == "__main__":
    unittest.main()
