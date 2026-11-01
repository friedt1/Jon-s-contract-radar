"""Offline inventory regressions for the final two verified official entrypoints.

Official agency/supplier pages are NOT evidence of an accessible individual
solicitation feed. These tests never create or publish contract records.
"""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import scan
from audit_source_coverage import audit
from source_config import direct_fetch_target
from source_health import summarize


OFFICIAL = {
    "SUNY Corning Community College": "https://www.corning-cc.edu/rbot/index.php",
    "Wegmans regional properties": "https://www.wegmans.com/service/for-our-suppliers",
}


class FinalOfficialEntrypointsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        cls.by_name = {row["name"]: row for row in cls.sources}

    def test_official_pages_remain_staged_not_individual_bid_feeds(self):
        self.assertEqual(len(self.sources), 102)
        for name, url in OFFICIAL.items():
            with self.subTest(name=name):
                row = self.by_name[name]
                self.assertEqual(row["candidate_official_url"], url)
                self.assertEqual(row["mode"], "discovery_pending")
                self.assertEqual(row["url"], "")
                self.assertIs(row["verified_url"], False)
                self.assertIn("NOT", row["official_page_role"])
                self.assertTrue(row["activation_gate"])
                self.assertFalse(direct_fetch_target(row))
        self.assertIs(self.by_name["Wegmans regional properties"]["provider_access_required"], True)

    def test_no_official_entrypoint_is_silently_activated(self):
        for name in OFFICIAL:
            with self.subTest(name=name):
                source = self.by_name[name]
                with patch.object(scan, "scan_direct", side_effect=AssertionError(
                        "Staged entrypoint must not be crawled as a direct bid feed")) as direct, \
                     patch.object(scan, "scan_news", return_value=[]):
                    _, status, leads = scan.run(source)
                direct.assert_not_called()
                self.assertNotIn("direct fetched", status)
                self.assertEqual(leads, [])

    def test_coverage_reports_84_staged_and_no_unknown_official_urls(self):
        result = audit(self.sources)
        self.assertEqual(result["total"], 102)
        self.assertEqual(result["direct_configured"], 18)
        self.assertEqual(result["not_directly_monitored"], 84)
        self.assertEqual(result["official_urls_staged"], 84)
        self.assertEqual(result["discovery_required"], 0)
        subset = [self.by_name[name] for name in OFFICIAL]
        counts = summarize(subset, {})["counts"]
        self.assertEqual(counts["configured_direct"], 0)
        self.assertEqual(counts["staged_official_url"], 2)
        self.assertEqual(counts["staged_provider_access_required"], 1)
        self.assertEqual(counts["individual_bid_details_fetched"], 0)


if __name__ == "__main__":
    unittest.main()
