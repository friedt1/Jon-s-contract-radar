"""Towanda Borough official announcements: staged only, no invented bids."""
import datetime as dt
import json
from pathlib import Path
import unittest

import audit_source_coverage
import scan
import source_health


ROOT = Path(__file__).resolve().parent
URL = "https://towandaborough.org/public-announcements/"


class TowandaOfficialStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
        cls.source = next(x for x in cls.sources if x["name"] == "Towanda Borough")

    def test_verified_publisher_page_is_staged_not_activated(self):
        self.assertEqual(len(self.sources), 102)
        self.assertEqual(self.source["candidate_official_url"], URL)
        self.assertEqual(self.source["mode"], "discovery_pending")
        self.assertEqual(self.source["url"], "")
        self.assertIs(self.source["verified_url"], False)
        self.assertIn("individual", self.source["activation_gate"])
        self.assertEqual(source_health.classify(self.source, "")["direct_state"],
                         "staged_official_url")
        audit = audit_source_coverage.audit(self.sources)
        row = next(x for x in audit["sources"] if x["source"] == "Towanda Borough")
        self.assertTrue(row["official_url_staged"])
        self.assertFalse(row["direct_configured"])
        self.assertFalse(row["direct_fetch_target"])

    def test_historical_unrelated_waste_bid_is_not_tree_work(self):
        # Synthetic excerpt based on a borough announcement. The actual
        # October 27, 2026 waste collection deadline is already past.
        excerpt = ("Sealed bids for municipal solid waste collection, "
                   "recycling, transportation and disposal services, "
                   "including residential curbside collection and spring cleanup. "
                   "Bids due October 27, 2026.")
        self.assertIsNone(scan.category(excerpt))
        self.assertFalse(scan.eligible(excerpt, "Towanda Borough",
                                       today=dt.date(2026, 10, 31)))
        results = {}
        scan.add_lead(results, "Towanda Borough", "Municipal solid waste collection",
                      URL, excerpt)
        self.assertEqual(results, {})

    def test_published_health_is_staging_metadata_not_new_scan(self):
        feed = json.loads((ROOT / "data/opportunities.json").read_text(encoding="utf-8"))
        row = next(x for x in feed["source_health"]["sources"]
                   if x["name"] == "Towanda Borough")
        self.assertEqual(row["direct_state"], "staged_official_url")
        self.assertEqual(row["staged_official_url"], URL)
        self.assertEqual(row["individual_bid_details_fetched"], 0)
        self.assertEqual(feed["source_health"]["counts"]["staged_official_url"],
                         audit_source_coverage.audit(self.sources)["official_urls_staged"])
        self.assertEqual(feed["opportunities"], [])


if __name__ == "__main__":
    unittest.main()
