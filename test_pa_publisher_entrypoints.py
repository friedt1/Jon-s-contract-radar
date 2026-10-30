"""Official PA county publisher entrypoints are not active bid adapters.

All fixtures are synthetic; this test never fetches live websites or seeds bids.
"""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_source_coverage
import scan
import source_health


class PaPublisherEntrypointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        cls.by_name = {row["name"]: row for row in cls.sources}

    def test_three_pa_publishers_are_staged_not_activated(self):
        expected = {
            "Tioga County PA": "www.tiogacountypa.us",
            "Potter County PA": "www.pottercountypa.gov",
            "Wyoming County PA": "wyomingcountypa.gov",
        }
        self.assertEqual(len(self.sources), 102)
        self.assertEqual(len(self.by_name), 102)
        for name, host in expected.items():
            with self.subTest(name=name):
                source = self.by_name[name]
                self.assertEqual(source["mode"], "discovery_pending")
                self.assertEqual(source["url"], "")
                self.assertFalse(source["verified_url"])
                self.assertIn(host, source["candidate_official_url"])
                self.assertEqual(source["official_page_role"],
                                 "publisher_entrypoint_only")
                self.assertIn("NOT a", source["activation_gate"])
                self.assertEqual(source_health.classify(source, "")["direct_state"],
                                 "staged_official_url")
                with patch.object(scan, "scan_direct", side_effect=AssertionError(
                        "Staged publisher must not be crawled as a direct source"
                )) as direct, patch.object(scan, "scan_news", return_value=[]):
                    _, _, leads = scan.run(source)
                direct.assert_not_called()
                self.assertEqual(leads, [])

    def test_coverage_audit_does_not_count_staged_publishers_as_direct(self):
        audit = audit_source_coverage.audit(self.sources)
        self.assertEqual(audit["total"], 102)
        self.assertEqual(audit["direct_configured"], 18)
        self.assertEqual(audit["not_directly_monitored"], 84)
        self.assertGreaterEqual(audit["official_urls_staged"], 31)
        for name in ("Tioga County PA", "Potter County PA", "Wyoming County PA"):
            row = next(x for x in audit["sources"] if x["source"] == name)
            self.assertFalse(row["direct_configured"])
            self.assertFalse(row["direct_fetch_target"])
            self.assertTrue(row["official_url_staged"])

    def test_provider_gate_survives_missing_or_stale_scan_status(self):
        providers = ("Tompkins County purchasing", "PennBid platform",
                     "BidNet NY platform")
        for name in providers:
            with self.subTest(name=name):
                source = self.by_name[name]
                for status in ("", "direct fetched; 1 listing pages"):
                    row = source_health.classify(source, status)
                    self.assertTrue(row["provider_access_required"])
                    self.assertEqual(row["direct_state"], "access_required")
                # A real robots block must remain visible while the access
                # requirement continues to count in configured coverage.
                blocked = source_health.classify(
                    source, "direct blocked by robots policy: disallowed")
                self.assertEqual(blocked["direct_state"], "robots_blocked")
                self.assertTrue(blocked["provider_access_required"])
        summary = source_health.summarize(
            [self.by_name[name] for name in providers], {})
        self.assertEqual(summary["counts"]["configured_direct"], 3)
        self.assertEqual(summary["counts"]["configured_access_required"], 3)
        self.assertEqual(summary["counts"]["configured_fetch_targets"], 0)

    def test_expired_erie_and_unrelated_owego_are_not_live(self):
        import datetime as dt
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            today=dt.date(2026, 10, 30)))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            today=dt.date(2026, 10, 30)))


if __name__ == "__main__":
    unittest.main()
