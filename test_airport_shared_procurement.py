"""Official shared county-airport procurement gateway is NOT a second live feed.

No production bids or fabricated opportunities are introduced by these tests.
"""
import datetime as dt
import json
from pathlib import Path
import unittest

from audit_source_coverage import audit
from notice_identity import canonical_url
from source_health import summarize
import scan


class AirportSharedProcurementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        cls.by_name = {source["name"]: source for source in cls.sources}

    def test_airport_official_gateway_is_staged_and_shared_not_active(self):
        county = self.by_name["Chemung County bids"]
        airport = self.by_name["Elmira-Corning Regional Airport"]
        self.assertEqual(airport["mode"], "discovery_pending")
        self.assertFalse(airport["verified_url"])
        self.assertEqual(airport["url"], "")
        self.assertEqual(canonical_url(airport["candidate_official_url"]),
                         canonical_url(county["url"]))
        coverage = audit(self.sources)
        rows = {row["source"]: row for row in coverage["sources"]}
        self.assertEqual(coverage["total"], 102)
        self.assertEqual(coverage["direct_configured"], 18)
        self.assertEqual(coverage["official_urls_staged"], 70)
        self.assertEqual(coverage["not_directly_monitored"], 84)
        self.assertTrue(rows[airport["name"]]["shared_official_entrypoint"])
        self.assertTrue(rows[county["name"]]["shared_official_entrypoint"])
        self.assertFalse(rows[airport["name"]]["direct_fetch_target"])
        self.assertIn("individual-notice", rows[airport["name"]]["status"])
        self.assertIn(airport["name"],
                      coverage["shared_official_entrypoint_groups"][county["url"]])

    def test_empty_status_does_not_claim_airport_extraction(self):
        health = summarize([self.by_name["Elmira-Corning Regional Airport"]], {})
        self.assertEqual(health["counts"]["staged_official_url"], 1)
        self.assertEqual(health["counts"]["configured_direct"], 0)
        self.assertEqual(health["counts"]["individual_bid_details_fetched"], 0)
        self.assertEqual(health["counts"]["configured_fetch_targets"], 0)

    def test_erie_and_owego_regressions_remain_non_live(self):
        today = dt.date(2026, 11, 1)
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            "PennBid platform", today=today))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            "Tioga County NY", today=today))


if __name__ == "__main__":
    unittest.main()
