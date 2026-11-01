"""Official school business-office entrypoints are NOT individual bid feeds.

No opportunities are inserted; Erie and Owego are regression-only examples.
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


GATEWAYS = {
    "Elmira City School District":
        "https://www.elmiracityschools.com/page/business-office",
    "Ithaca City School District":
        "https://www.ithacacityschools.org/page/business-services",
}


class SchoolBusinessGatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads(
            (Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
        cls.by_name = {row["name"]: row for row in cls.sources}

    def test_official_business_offices_remain_staged_only(self):
        for name, url in GATEWAYS.items():
            with self.subTest(name=name):
                row = self.by_name[name]
                self.assertEqual(row["mode"], "discovery_pending")
                self.assertEqual(row["url"], "")
                self.assertIs(row["verified_url"], False)
                self.assertEqual(row["candidate_official_url"], url)
                self.assertTrue(source_config.valid_public_https_url(url))
                self.assertIn("NOT", row["official_page_role"])
                for word in ("robots/terms", "scope", "deadline", "open status"):
                    self.assertIn(word, row["activation_gate"])
                self.assertFalse(source_config.direct_configured(row))
                self.assertFalse(source_config.direct_fetch_target(row))
                health = source_health.classify(row, "")
                self.assertEqual(health["direct_state"], "staged_official_url")
                self.assertEqual(health["direct_url"], "")

    def test_no_direct_network_calls_or_fabricated_opportunities(self):
        for name in GATEWAYS:
            with self.subTest(name=name):
                with (patch.object(scan, "scan_direct",
                                   side_effect=AssertionError("staged direct fetch")),
                      patch.object(scan, "scan_news", return_value=[])):
                    _, status, leads = scan.run(self.by_name[name])
                self.assertEqual(leads, [])
                self.assertNotIn("direct fetched", status)

    def test_102_source_coverage_and_remaining_discovery_are_honest(self):
        coverage = audit_source_coverage.audit(self.sources)
        self.assertEqual(coverage["total"], 102)
        self.assertEqual(coverage["direct_configured"], 18)
        self.assertEqual(coverage["not_directly_monitored"], 84)
        self.assertEqual(coverage["official_urls_staged"], 70)
        self.assertEqual(coverage["discovery_required"], 14)
        for name in GATEWAYS:
            row = next(x for x in coverage["sources"] if x["source"] == name)
            self.assertTrue(row["official_url_staged"])
            self.assertFalse(row["direct_fetch_target"])

    def test_historical_erie_and_unrelated_owego_still_excluded(self):
        today = dt.date(2026, 10, 31)
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            "PennBid platform", today=today))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            "Tioga County NY", today=today))


if __name__ == "__main__":
    unittest.main()
