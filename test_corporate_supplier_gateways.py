"""Official corporate supplier contact routes must never be counted as bid feeds.

Fixtures are offline and synthetic. No contract is created or published.
"""
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
    "UPMC Williamsport":
        "https://www.upmc.com/about/supply-chain/inquiries/registration-non-mwdbe",
    "Corning Incorporated":
        "https://www.corning.com/worldwide/en/sustainability/processes/supply-chain-social-responsibility/supplier-responsibility.html",
    "Kimco Realty": "https://www.kimcorealty.com/vendor-opportunities",
    "Wegmans regional properties": "https://www.wegmans.com/service/for-our-suppliers",
}


class CorporateSupplierGatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        cls.by_name = {source["name"]: source for source in cls.sources}

    def test_official_vendor_pages_are_staged_access_required_not_active(self):
        self.assertEqual(len(self.sources), 102)
        self.assertEqual(len(self.by_name), 102)
        for name, url in OFFICIAL.items():
            with self.subTest(name=name):
                source = self.by_name[name]
                self.assertEqual(source["candidate_official_url"], url)
                self.assertEqual(source["mode"], "discovery_pending")
                self.assertEqual(source["url"], "")
                self.assertIs(source["verified_url"], False)
                self.assertIs(source["provider_access_required"], True)
                self.assertIs(source["require_local_evidence"], True)
                self.assertFalse(direct_fetch_target(source))
                self.assertTrue(source["activation_gate"])
                self.assertIn("NOT", source["official_page_role"])

    def test_supplier_gateways_never_trigger_direct_fetch(self):
        for name in OFFICIAL:
            with self.subTest(name=name):
                source = self.by_name[name]
                with patch.object(scan, "scan_direct", side_effect=AssertionError(
                    "Supplier gateway must not be fetched as a public bid feed"
                )) as direct, patch.object(scan, "scan_news", return_value=[]):
                    _, _, opportunities = scan.run(source)
                direct.assert_not_called()
                self.assertEqual(opportunities, [])

    def test_audit_and_source_health_distinguish_supplier_access(self):
        subset = [self.by_name[name] for name in OFFICIAL]
        summary = summarize(subset, {})
        self.assertEqual(summary["counts"]["configured_direct"], 0)
        self.assertEqual(summary["counts"]["configured_fetch_targets"], 0)
        self.assertEqual(summary["counts"]["staged_official_url"], 4)
        self.assertEqual(summary["counts"]["staged_provider_access_required"], 4)
        self.assertEqual(summary["counts"]["individual_bid_details_fetched"], 0)
        coverage = audit(self.sources)
        self.assertEqual(coverage["total"], 102)
        self.assertEqual(coverage["direct_configured"], 18)
        self.assertEqual(coverage["not_directly_monitored"], 84)
        self.assertEqual(coverage["official_urls_staged"], 84)
        self.assertEqual(coverage["discovery_required"], 0)
        by_name = {row["source"]: row for row in coverage["sources"]}
        for name in OFFICIAL:
            self.assertTrue(by_name[name]["official_url_staged"])
            self.assertTrue(by_name[name]["staged_provider_access_required"])
            self.assertFalse(by_name[name]["direct_fetch_target"])

    def test_historical_examples_remain_non_live(self):
        today = dt.date(2026, 11, 1)
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            "PennBid platform", today=today))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            "Tioga County NY", today=today))


if __name__ == "__main__":
    unittest.main()
