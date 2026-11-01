"""School publisher entrypoints are staged only; synthetic regressions, no live bids."""
import datetime as dt
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_source_coverage
import scan
import source_config
import source_health


OFFICIAL = {
    "Horseheads Central School District": "https://www.horseheadsdistrict.com/",
    "Binghamton City School District": "https://www.binghamtonschools.org/",
    "Watkins Glen Central School District": "https://www.wgcsd.org/page/business-office",
    "Bath Central School District": "https://www.bathcsd.org/page/business-office",
}


class AdditionalSchoolGatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads(
            (Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
        cls.by_name = {source["name"]: source for source in cls.sources}

    def test_gateway_urls_are_official_staging_not_activated_adapters(self):
        for name, url in OFFICIAL.items():
            with self.subTest(source=name):
                source = self.by_name[name]
                self.assertEqual(source["mode"], "discovery_pending")
                self.assertEqual(source["url"], "")
                self.assertIs(source["verified_url"], False)
                self.assertEqual(source["candidate_official_url"], url)
                self.assertTrue(source_config.valid_public_https_url(url))
                self.assertIn("NOT", source["official_page_role"])
                for requirement in ("robots/terms", "scope", "deadline", "open status"):
                    self.assertIn(requirement, source["activation_gate"])
                self.assertFalse(source_config.direct_configured(source))
                self.assertFalse(source_config.direct_fetch_target(source))
                health = source_health.classify(source, "")
                self.assertEqual(health["direct_state"], "staged_official_url")
                self.assertEqual(health["direct_url"], "")

    def test_no_direct_request_or_fabricated_bid_from_gateway(self):
        for name in OFFICIAL:
            with self.subTest(source=name):
                with (patch.object(scan, "scan_direct",
                                   side_effect=AssertionError("unapproved direct fetch")),
                      patch.object(scan, "scan_news", return_value=[])):
                    _, status, leads = scan.run(self.by_name[name])
                self.assertEqual(leads, [])
                self.assertNotIn("direct fetched", status)

    def test_inventory_and_activation_gaps_are_reported(self):
        coverage = audit_source_coverage.audit(self.sources)
        self.assertEqual(coverage["total"], 102)
        self.assertEqual(coverage["direct_configured"], 18)
        self.assertEqual(coverage["not_directly_monitored"], 84)
        self.assertEqual(coverage["official_urls_staged"], 62)
        self.assertEqual(coverage["discovery_required"], 22)
        for name in OFFICIAL:
            row = next(row for row in coverage["sources"] if row["source"] == name)
            self.assertTrue(row["official_url_staged"])
            self.assertFalse(row["direct_fetch_target"])

    def test_expired_erie_and_unrelated_owego_remain_excluded(self):
        today = dt.date(2026, 10, 31)
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            "PennBid platform", today=today))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            "Tioga County NY", today=today))


if __name__ == "__main__":
    unittest.main()
