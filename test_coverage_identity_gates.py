"""Offline regression checks: coverage counts must not overstate agency monitoring."""
import unittest

from audit_source_coverage import audit


class SourceIdentityGateTests(unittest.TestCase):
    def test_duplicate_name_cannot_count_as_two_fetch_targets(self):
        sources = [
            {"name": "Tioga County NY", "mode": "direct_page",
             "url": "https://tiogacountyny.com/departments/public-works/",
             "verified_url": True},
            {"name": "  TIOGA   COUNTY NY ", "mode": "direct_page",
             "url": "https://tiogacountyny.com/departments/public-works/",
             "verified_url": True},
        ]
        result = audit(sources)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["unique_named_targets"], 1)
        self.assertEqual(result["duplicate_source_rows"], 1)
        self.assertEqual(result["direct_fetch_targets"], 0)
        self.assertFalse(result["inventory_integrity_ok"])
        for row in result["sources"]:
            self.assertIn("duplicate_source_name", row["activation_blockers"])

    def test_shared_gateway_not_independent_verified_ingestion(self):
        gateway = "https://example.gov/purchasing"
        sources = [
            {"name": "County Purchasing", "mode": "discovery_pending",
             "candidate_official_url": gateway, "verified_url": False,
             "official_page_role": "publisher_entrypoint_only"},
            {"name": "City Purchasing", "mode": "discovery_pending",
             "candidate_official_url": gateway, "verified_url": False,
             "official_page_role": "publisher_entrypoint_only"},
        ]
        result = audit(sources)
        self.assertEqual(result["direct_fetch_targets"], 0)
        self.assertEqual(result["official_urls_staged"], 2)
        self.assertEqual(result["distinct_official_entrypoints"], 1)
        self.assertEqual(result["shared_official_entrypoint_targets"], 2)
        for row in result["sources"]:
            self.assertTrue(row["shared_official_entrypoint"])
            self.assertIn("procurement_index_not_identified", row["activation_blockers"])

    def test_provider_access_gate_never_counts_as_fetchable(self):
        source = {"name": "County Purchasing", "mode": "direct_page",
                  "url": "https://example.gov/purchasing",
                  "verified_url": True, "delegated_provider": "BidNet Direct",
                  "provider_access_required": True}
        result = audit([source])
        self.assertEqual(result["direct_fetch_targets"], 0)
        self.assertIn("provider_authorization_required",
                      result["sources"][0]["activation_blockers"])


if __name__ == "__main__":
    unittest.main()
