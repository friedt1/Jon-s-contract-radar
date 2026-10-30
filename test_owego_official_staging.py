"""Offline Village of Owego staging and expired/unrelated notice regressions."""
import datetime as dt
import json
from pathlib import Path
import unittest

import probe_staged_sources as staged
import scan

NOW = dt.datetime(2026, 10, 30, 14, 0, tzinfo=dt.timezone.utc)


class OwegoOfficialSourceTests(unittest.TestCase):
    def test_official_news_index_is_staged_not_direct(self):
        sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        self.assertEqual(len(sources), 102)
        source = next(row for row in sources if row["name"] == "Village of Owego")
        self.assertEqual(source["mode"], "discovery_pending")
        self.assertEqual(source["url"], "")
        self.assertFalse(source["verified_url"])
        self.assertEqual(source["candidate_official_url"],
                         "https://villageofowegony.gov/newslist.php")
        self.assertIn("individual-notice", source["activation_gate"])

    def test_empty_official_news_index_cannot_imply_no_open_bids(self):
        source = {
            "name": "Village of Owego", "mode": "discovery_pending",
            "candidate_official_url": "https://villageofowegony.gov/newslist.php",
            "activation_gate": "Terms and individual extraction required",
        }
        html = "<html><h1>Newslist</h1><p>Village of Owego</p></html>"
        result = staged.probe(
            source, fetch=lambda url: (html, "text/html", url), now=NOW)
        self.assertEqual(result["state"],
                         "official_page_reachable_no_procurement_evidence")
        self.assertTrue(result["listing_retrieved"])
        self.assertFalse(result["individual_notice_retrieved"])
        self.assertFalse(result["direct_monitoring_activated"])
        self.assertNotIn("opportunities", result)

    def test_expired_tree_bid_and_unrelated_demolition_never_become_live(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due April 17, 2026",
            today=dt.date(2026, 10, 30)))
        self.assertIsNone(scan.category(
            "67 Central Avenue Owego demolition rebid and site restoration"))
        self.assertFalse(scan.eligible(
            "67 Central Avenue Owego demolition rebid due November 13, 2026",
            today=dt.date(2026, 10, 30)))


if __name__ == "__main__":
    unittest.main()
