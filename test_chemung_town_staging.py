"""Official Chemung town entrypoints are staged, never active bid adapters.

No network calls, fabricated solicitations, or manually seeded live leads.
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
    "Town of Big Flats": (
        "https://www.bigflatsny.gov/", "publisher_entrypoint_only"),
    "Town of Elmira": (
        "https://townofelmira.gov/", "publisher_entrypoint_only"),
    "Town of Southport": (
        "https://townofsouthportny.gov/post.php?pid=44",
        "mixed_legal_notices_not_bid_feed"),
}


class ChemungTownStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads(
            (Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
        cls.by_name = {row["name"]: row for row in cls.sources}

    def test_verified_publisher_entrypoints_not_live_feeds(self):
        self.assertEqual(len(self.sources), 102)
        self.assertEqual(len(self.by_name), 102)
        for name, (url, role) in EXPECTED.items():
            with self.subTest(name=name):
                row = self.by_name[name]
                self.assertEqual(row["mode"], "discovery_pending")
                self.assertEqual(row["url"], "")
                self.assertIs(row["verified_url"], False)
                self.assertEqual(row["candidate_official_url"], url)
                self.assertEqual(row["official_page_role"], role)
                self.assertTrue(source_config.valid_public_https_url(url))
                self.assertFalse(source_config.direct_configured(row))
                self.assertIn("robots", row["activation_gate"])
                self.assertIn("before activation", row["activation_gate"])
                self.assertEqual(source_health.classify(row, "")["direct_state"],
                                 "staged_official_url")
                with patch.object(scan, "scan_direct",
                                  side_effect=AssertionError("staged page fetched")) as direct, \
                     patch.object(scan, "scan_news", return_value=[]):
                    _, status, leads = scan.run(row)
                direct.assert_not_called()
                self.assertEqual(leads, [])
                self.assertIn("direct not configured", status)

    def test_audit_keeps_102_sources_and_no_new_direct_integrations(self):
        audit = audit_source_coverage.audit(self.sources)
        self.assertEqual(audit["total"], 102)
        self.assertEqual(audit["direct_configured"], 18)
        self.assertEqual(audit["not_directly_monitored"], 84)
        self.assertGreaterEqual(audit["official_urls_staged"], 34)
        for name in EXPECTED:
            row = next(x for x in audit["sources"] if x["source"] == name)
            self.assertTrue(row["official_url_staged"])
            self.assertFalse(row["direct_configured"])
            self.assertFalse(row["direct_fetch_target"])

    def test_expired_erie_and_unrelated_owego_remain_excluded(self):
        today = dt.date(2026, 10, 30)
        self.assertFalse(scan.eligible(
            "Erie PA tree and stump removal bid due October 29, 2026",
            "PennBid platform", today=today))
        self.assertFalse(scan.eligible(
            "Owego NY demolition and site restoration bid due November 13, 2026",
            "Tioga County NY", today=today))


if __name__ == "__main__":
    unittest.main()
