"""Offline audit regression: inventory rows are not independent verified feeds."""
import unittest

from audit_source_coverage import audit, strict_failures


class InventoryIntegrityTests(unittest.TestCase):
    def test_duplicate_agency_rows_do_not_inflate_unique_target_count(self):
        rows = [
            {"name": "Tioga County", "mode": "discovery_pending",
             "candidate_official_url": "https://tioga.example/Bids.aspx"},
            {"name": "  TIOGA   COUNTY  ", "mode": "discovery_pending",
             "candidate_official_url": "https://tioga.example/Bids.aspx?utm_source=alert"},
        ]
        report = audit(rows)
        self.assertEqual(report["total"], 2)
        self.assertEqual(report["unique_named_targets"], 1)
        self.assertEqual(report["duplicate_source_rows"], 1)
        self.assertEqual(report["distinct_official_entrypoints"], 1)
        self.assertEqual(report["shared_official_entrypoint_targets"], 0)
        self.assertFalse(report["inventory_integrity_ok"])
        self.assertTrue(all(row["duplicate_source_name"] for row in report["sources"]))
        self.assertTrue(any("unique named targets: 1" in message
                            for message in strict_failures(report, expected_targets=2)))

    def test_publisher_homepage_does_not_count_as_bid_index(self):
        report = audit([{
            "name": "Agency A", "mode": "discovery_pending",
            "candidate_official_url": "https://agency.example/procurement",
            "official_page_role": "publisher_entrypoint_only",
        }])
        self.assertEqual(report["direct_configured"], 0)
        self.assertEqual(report["direct_fetch_targets"], 0)
        self.assertEqual(report["staged_publisher_entrypoints_only"], 1)
        self.assertTrue(report["sources"][0]["staged_publisher_entrypoint_only"])
        self.assertIn("current bid index not identified", report["sources"][0]["status"])

    def test_unverified_direct_url_is_not_active_monitoring(self):
        report = audit([{
            "name": "Agency A", "mode": "direct_page",
            "url": "https://agency.example/bids",
            "verified_url": False,
        }])
        self.assertEqual(report["direct_configured"], 0)
        self.assertEqual(report["direct_fetch_targets"], 0)
        self.assertEqual(report["invalid_direct_configurations"], 1)
        self.assertTrue(any("invalid direct configurations: 1" in message
                            for message in strict_failures(report, expected_targets=1)))


if __name__ == "__main__":
    unittest.main()
