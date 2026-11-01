"""The Ashland target is Chemung County, not the Greene County namesake."""
import json
from pathlib import Path
import unittest

import audit_source_coverage
import scan
import source_health


ROOT = Path(__file__).resolve().parent
OFFICIAL = "https://ashlandnychemung.gov/"
WRONG_COUNTY = "ashlandny.com"


class AshlandChemungStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
        cls.source = next(x for x in cls.sources if x["name"] == "Town of Ashland NY")

    def test_correct_county_publisher_staged_without_direct_monitoring(self):
        self.assertEqual(len(self.sources), 102)
        self.assertEqual(self.source["candidate_official_url"], OFFICIAL)
        self.assertEqual(self.source["official_page_role"], "publisher_entrypoint_only")
        self.assertNotIn(WRONG_COUNTY, self.source["candidate_official_url"])
        self.assertIn("Greene County", self.source["activation_gate"])
        self.assertEqual(self.source["mode"], "discovery_pending")
        self.assertEqual(self.source["url"], "")
        self.assertIs(self.source["verified_url"], False)
        self.assertEqual(source_health.classify(self.source, "")["direct_state"],
                         "staged_official_url")
        row = next(x for x in audit_source_coverage.audit(self.sources)["sources"]
                   if x["source"] == "Town of Ashland NY")
        self.assertTrue(row["official_url_staged"])
        self.assertFalse(row["direct_fetch_target"])

    def test_homepage_does_not_imply_an_open_tree_bid(self):
        sample = ("Town of Ashland New York, Town Hall, "
                  "3663 Sixth Street, Wellsburg NY 14894. "
                  "Events, Board, Clerk, Court, Minutes.")
        self.assertIsNone(scan.category(sample))
        self.assertFalse(scan.eligible(sample, "Town of Ashland NY"))
        leads = {}
        scan.add_lead(leads, "Town of Ashland NY", "Town Hall", OFFICIAL, sample)
        self.assertEqual(leads, {})

    def test_staging_count_reconciles_with_feed_without_fresh_scan(self):
        feed = json.loads((ROOT / "data/opportunities.json").read_text(encoding="utf-8"))
        row = next(x for x in feed["source_health"]["sources"]
                   if x["name"] == "Town of Ashland NY")
        self.assertEqual(row["direct_state"], "staged_official_url")
        self.assertEqual(row["staged_official_url"], OFFICIAL)
        self.assertEqual(row["individual_bid_details_fetched"], 0)
        # The published feed is a historical snapshot, not a new scan.
        self.assertLessEqual(feed["source_health"]["counts"]["staged_official_url"],
                             audit_source_coverage.audit(self.sources)["official_urls_staged"])
        self.assertEqual(feed["opportunities"], [])


if __name__ == "__main__":
    unittest.main()
