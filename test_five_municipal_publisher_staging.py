"""Publisher URL staging only: no direct bid activation or fabricated opportunities.

All test fixtures are synthetic or historical; source review date 2026-10-30.
"""
import datetime as dt
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_source_coverage
import scan
import source_config
import source_health


EXPECTED = {
    "Village of Bath": (
        "https://villageofbathny.gov/", "publisher_entrypoint_only"),
    "Village of Penn Yan": (
        "https://www.villageofpennyan.gov/meetings.html",
        "mixed_public_notices_not_bid_feed"),
    "Town of Erwin": (
        "https://www.erwinny.gov/", "publisher_entrypoint_only"),
    "Town of Lansing": (
        "https://www.lansingtownny.gov/rfps", "bid_index_no_current_records"),
    "Town of Dryden": (
        "https://www.dryden.ny.us/", "publisher_entrypoint_only"),
}


class FiveMunicipalPublisherStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads(
            (Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
        cls.by_name = {row["name"]: row for row in cls.sources}

    def test_official_urls_staged_but_no_new_direct_ingestion(self):
        self.assertEqual(len(self.sources), 102)
        self.assertEqual(len(self.by_name), 102)
        for name, (url, role) in EXPECTED.items():
            with self.subTest(source=name):
                row = self.by_name[name]
                self.assertEqual(row["mode"], "discovery_pending")
                self.assertEqual(row["url"], "")
                self.assertIs(row["verified_url"], False)
                self.assertEqual(row["candidate_official_url"], url)
                self.assertEqual(row["official_page_role"], role)
                self.assertTrue(source_config.valid_public_https_url(url))
                self.assertFalse(source_config.direct_configured(row))
                self.assertFalse(source_config.direct_fetch_target(row))
                self.assertIn("before activation", row["activation_gate"])
                self.assertIn("robots", row["activation_gate"])
                self.assertEqual(source_health.classify(row, "")["direct_state"],
                                 "staged_official_url")
                with patch.object(scan, "scan_direct",
                                  side_effect=AssertionError("staged URL fetched")) as direct, \
                     patch.object(scan, "scan_news", return_value=[]):
                    _, status, leads = scan.run(row)
                direct.assert_not_called()
                self.assertEqual(leads, [])
                self.assertNotIn("direct fetched", status)

    def test_strict_audit_keeps_staged_sources_out_of_live_coverage(self):
        result = audit_source_coverage.audit(self.sources)
        self.assertEqual(result["total"], 102)
        self.assertEqual(result["direct_configured"], 18)
        self.assertEqual(result["not_directly_monitored"], 84)
        self.assertEqual(result["official_urls_staged"], 40)
        self.assertEqual(result["discovery_required"], 44)
        for name in EXPECTED:
            row = next(x for x in result["sources"] if x["source"] == name)
            self.assertTrue(row["official_url_staged"])
            self.assertFalse(row["direct_fetch_target"])
            self.assertFalse(row["direct_configured"])

    def test_historical_tree_work_and_unrelated_demolition_not_live(self):
        today = dt.date(2026, 10, 30)
        self.assertFalse(scan.eligible(
            "Penn Yan NY tree maintenance and power line clearing bid "
            "due April 3, 2026", "Village of Penn Yan", today=today))
        self.assertFalse(scan.eligible(
            "Erie PA tree and stump removal bid due October 29, 2026",
            "PennBid platform", today=today))
        self.assertFalse(scan.eligible(
            "Owego NY demolition and site restoration bid due November 13, 2026",
            "Tioga County NY", today=today))

    def test_empty_lansing_index_not_proof_of_full_coverage(self):
        row = self.by_name["Town of Lansing"]
        self.assertIn("no bids", row["activation_gate"])
        self.assertIn("not prove", row["activation_gate"])
        self.assertFalse(source_config.direct_fetch_target(row))

    def test_dryden_access_error_documented_not_active(self):
        row = self.by_name["Town of Dryden"]
        self.assertIn("HTTP 403", row["activation_gate"])
        self.assertFalse(source_config.direct_fetch_target(row))


if __name__ == "__main__":
    unittest.main()
