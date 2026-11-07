"""Offline regressions for honest 102-source coverage reporting.

These fixtures never create or publish procurement opportunities.
"""
import unittest

from audit_source_coverage import audit, strict_failures


class CoverageIntegrityRegressionTests(unittest.TestCase):
    def test_duplicate_agency_does_not_satisfy_102_distinct_targets(self):
        sources = [
            {"name": "Agency " + str(i), "mode": "discovery_pending"}
            for i in range(101)
        ]
        sources.append({"name": "  AGENCY   0  ", "mode": "discovery_pending"})
        report = audit(sources)
        self.assertEqual(report["total"], 102)
        self.assertEqual(report["unique_named_targets"], 101)
        self.assertEqual(report["duplicate_source_rows"], 1)
        self.assertFalse(report["inventory_integrity_ok"])
        self.assertTrue(strict_failures(report))

    def test_delegated_supplier_page_is_not_an_individual_notice_feed(self):
        source = {
            "name": "Example County Purchasing",
            "mode": "direct_page",
            "url": "https://example.org/purchasing",
            "verified_url": True,
            "delegated_provider": "BidNet Direct",
        }
        row = audit([source])["sources"][0]
        self.assertTrue(row["provider_access_required"])
        self.assertFalse(row["direct_fetch_target"])
        self.assertIn("not connected", row["status"])

    def test_staged_supplier_gateway_is_not_promoted_to_direct(self):
        source = {
            "name": "Example County",
            "mode": "discovery_pending",
            "url": "",
            "verified_url": False,
            "candidate_official_url": "https://example.org/bids",
            "delegated_provider": "PennBid",
            "provider_access_required": True,
        }
        report = audit([source])
        self.assertEqual(report["direct_configured"], 0)
        self.assertEqual(report["staged_provider_access_required"], 1)
        self.assertFalse(report["sources"][0]["direct_fetch_target"])


if __name__ == "__main__":
    unittest.main()
