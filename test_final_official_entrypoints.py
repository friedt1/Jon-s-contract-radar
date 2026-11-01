"""The final two official entrypoints are staged evidence, never live bid feeds."""
import datetime as dt
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from audit_source_coverage import audit
from source_config import direct_fetch_target
from source_health import summarize
import scan


OFFICIAL = {
    "SUNY Corning Community College":
        "https://www.corning-cc.edu/about/regional-board-of-trustees/ccc_policy_manual-2023.pdf",
    "Wegmans regional properties":
        "https://www.wegmans.com/service/for-our-suppliers",
}


class FinalOfficialEntryPointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        cls.by_name = {s["name"]: s for s in cls.sources}

    def test_102_targets_have_entrypoints_but_only_18_direct_configurations(self):
        coverage = audit(self.sources)
        self.assertEqual(coverage["total"], 102)
        self.assertEqual(coverage["unique_named_targets"], 102)
        self.assertEqual(coverage["direct_configured"], 18)
        self.assertEqual(coverage["official_urls_staged"], 84)
        self.assertEqual(coverage["discovery_required"], 0)
        self.assertEqual(coverage["not_directly_monitored"], 84)

    def test_policy_and_supplier_pages_are_not_active_bid_sources(self):
        for name, url in OFFICIAL.items():
            with self.subTest(name=name):
                source = self.by_name[name]
                self.assertEqual(source["candidate_official_url"], url)
                self.assertEqual(source["mode"], "discovery_pending")
                self.assertEqual(source["url"], "")
                self.assertIs(source["verified_url"], False)
                self.assertIs(source["provider_access_required"], True)
                self.assertIn("NOT", source["official_page_role"])
                self.assertTrue(source["activation_gate"])
                self.assertFalse(direct_fetch_target(source))
                with patch.object(scan, "scan_direct", side_effect=AssertionError(
                        "Staged policy or supplier page cannot be crawled as bid feed")) as direct, \\
                     patch.object(scan, "scan_news", return_value=[]):
                    _, _, leads = scan.run(source)
                direct.assert_not_called()
                self.assertEqual(leads, [])

    def test_access_and_retrieval_are_reported_separately(self):
        rows = [self.by_name[name] for name in OFFICIAL]
        health = summarize(rows, {})
        self.assertEqual(health["counts"]["configured_direct"], 0)
        self.assertEqual(health["counts"]["staged_official_url"], 2)
        self.assertEqual(health["counts"]["staged_provider_access_required"], 2)
        self.assertEqual(health["counts"]["individual_bid_details_fetched"], 0)

    def test_regression_examples_never_become_live(self):
        today = dt.date(2026, 11, 1)
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            "PennBid platform", today=today))
        self.assertIsNone(scan.category(
            "Owego NY demolition and site restoration rebid due Nov 13 2026"))


if __name__ == "__main__":
    unittest.main()
