"""Official local supplier gateways are not active bid feeds (offline fixtures only)."""
import datetime as dt
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from audit_source_coverage import audit
from source_config import direct_fetch_target
from source_health import summarize
import scan


GATEWAYS = {
    "Norfolk Southern": "https://www.norfolksouthern.com/en/suppliers",
    "Guthrie Healthcare": "https://www.guthrie.org/vendor-information",
    "Arnot Health": "https://www.arnothealth.org/arnot-ogden-medical-center/directory",
}


class LocalSupplierGatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        cls.by_name = {s["name"]: s for s in cls.sources}

    def test_official_entrypoints_remain_staged_not_bid_feeds(self):
        self.assertEqual(len(self.sources), 102)
        self.assertEqual(len(self.by_name), 102)
        for name, url in GATEWAYS.items():
            with self.subTest(source=name):
                s = self.by_name[name]
                self.assertEqual(s["candidate_official_url"], url)
                self.assertEqual(s["mode"], "discovery_pending")
                self.assertEqual(s["url"], "")
                self.assertIs(s["verified_url"], False)
                self.assertIs(s["provider_access_required"], True)
                self.assertIs(s["require_local_evidence"], True)
                self.assertFalse(direct_fetch_target(s))
                self.assertIn("NOT", s["official_page_role"])
                self.assertIn("before activation", s["activation_gate"])

    def test_scanner_never_fetches_staged_vendor_gateways_directly(self):
        for name in GATEWAYS:
            with self.subTest(source=name):
                s = self.by_name[name]
                with patch.object(scan, "scan_direct",
                                  side_effect=AssertionError("not an active bid feed")) as direct:
                    with patch.object(scan, "scan_news", return_value=[]):
                        _, _, leads = scan.run(s)
                direct.assert_not_called()
                self.assertEqual(leads, [])

    def test_audit_preserves_role_and_access_blockers(self):
        result = audit(self.sources)
        self.assertEqual(result["total"], 102)
        self.assertEqual(result["direct_configured"], 18)
        self.assertEqual(result["not_directly_monitored"], 84)
        self.assertEqual(result["official_urls_staged"], 76)
        self.assertEqual(result["discovery_required"], 8)
        by_name = {row["source"]: row for row in result["sources"]}
        for name in GATEWAYS:
            with self.subTest(source=name):
                row = by_name[name]
                self.assertTrue(row["official_url_staged"])
                self.assertTrue(row["staged_provider_access_required"])
                self.assertFalse(row["direct_fetch_target"])
                self.assertIn("NOT", row["official_page_role"])
                self.assertTrue(row["activation_gate"])
        health = summarize([self.by_name[name] for name in GATEWAYS], {})
        self.assertEqual(health["counts"]["configured_direct"], 0)
        self.assertEqual(health["counts"]["staged_provider_access_required"], 3)
        self.assertEqual(health["counts"]["individual_bid_details_fetched"], 0)

    def test_historical_erie_and_unrelated_owego_remain_excluded(self):
        today = dt.date(2026, 11, 1)
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            "PennBid platform", today=today))
        self.assertIsNone(scan.category(
            "Owego NY demolition and site restoration rebid due Nov 13 2026"))


if __name__ == "__main__":
    unittest.main()
