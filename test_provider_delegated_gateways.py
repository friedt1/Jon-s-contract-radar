"""Regression gates for official provider-delegated purchasing pages.

Synthetic tests only: no contract is seeded or claimed open.
"""
import datetime as dt
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_source_coverage
import scan
import source_health


DELEGATED = {
    "Schuyler County purchasing": "BidNet Direct",
    "Elmira City bids": "BidNet Direct",
    "Lycoming County bids": "PennBid",
}


class DelegatedCountyGatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads(
            (Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
        cls.by_name = {row["name"]: row for row in cls.sources}

    def test_three_official_gateways_do_not_fetch_individual_bids(self):
        self.assertEqual(len(self.sources), 102)
        self.assertEqual(len(self.by_name), 102)
        for name, provider in DELEGATED.items():
            with self.subTest(name=name):
                source = self.by_name[name]
                self.assertEqual(source["delegated_provider"], provider)
                self.assertIs(source["provider_access_required"], True)
                self.assertIn("individual", source["activation_gate"])
                self.assertIn(name, scan.UNCONNECTED_PLATFORMS)
                with patch.object(scan, "scan_direct",
                                  side_effect=AssertionError("gateway crawled")) as direct:
                    with patch.object(scan, "scan_news", return_value=[]):
                        returned_name, status, leads = scan.run(source)
                direct.assert_not_called()
                self.assertEqual(returned_name, name)
                self.assertEqual(leads, [])
                self.assertIn("direct access required:", status)
                self.assertNotIn("direct fetched;", status)
                health = source_health.classify(source, status)
                self.assertEqual(health["direct_state"], "access_required")
                self.assertEqual(health["individual_bid_details_fetched"], 0)
                # Even missing status must not silently activate a gateway.
                self.assertEqual(source_health.classify(source, "")["direct_state"],
                                 "access_required")

    def test_coverage_does_not_count_provider_gateways_as_fetch_targets(self):
        audit = audit_source_coverage.audit(self.sources)
        self.assertEqual(audit["total"], 102)
        self.assertEqual(audit["direct_configured"], 18)
        self.assertEqual(audit["configured_provider_access_required"], 6)
        self.assertEqual(audit["direct_fetch_targets"], 12)
        self.assertEqual(audit["official_urls_staged"], 40)
        self.assertEqual(audit["discovery_required"], 44)
        self.assertEqual(audit["not_directly_monitored"], 84)
        health = source_health.summarize(self.sources, {})
        self.assertEqual(health["counts"]["configured_access_required"], 6)
        self.assertEqual(health["counts"]["configured_fetch_targets"], 12)
        for name in DELEGATED:
            row = next(r for r in audit["sources"] if r["source"] == name)
            self.assertTrue(row["provider_access_required"])
            self.assertFalse(row["direct_fetch_target"])

    def test_existing_chemung_civicplus_remains_independent(self):
        chemung = self.by_name["Chemung County bids"]
        self.assertNotIn(chemung["name"], scan.UNCONNECTED_PLATFORMS)
        self.assertFalse(chemung.get("provider_access_required", False))
        self.assertTrue(audit_source_coverage.audit([chemung])["direct_fetch_targets"])

    def test_historical_erie_and_unrelated_owego_are_not_live_tree_bids(self):
        today = dt.date(2026, 10, 30)
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal sealed bid due October 28, 2026",
            today=today))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            today=today))


if __name__ == "__main__":
    unittest.main()
