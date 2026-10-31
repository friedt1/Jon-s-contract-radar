"""Five northern PA borough publisher entrypoints; staging is not monitoring."""
import datetime as dt
import json
from pathlib import Path
import unittest

import audit_source_coverage
import scan
import source_health


ROOT = Path(__file__).resolve().parent
PUBLISHERS = {
    "Sayre Borough": "https://sayreborough.org/",
    "Athens Borough": "https://athensboroughpa.org/",
    "Mansfield Borough": "https://mansfieldborough.org/",
    "Troy Borough": "https://troyborough.com/officials.php",
    "Montrose Borough": "https://www.montroseborough.com/",
}


class PABoroughPublisherStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
        cls.feed = json.loads((ROOT / "data/opportunities.json").read_text(encoding="utf-8"))

    def test_all_five_official_entrypoints_are_staged_not_activated(self):
        self.assertEqual(len(self.sources), 102)
        audit = audit_source_coverage.audit(self.sources)
        self.assertEqual(audit["official_urls_staged"], 52)
        self.assertEqual(audit["not_directly_monitored"], 84)
        self.assertEqual(audit["discovery_required"], 32)
        for name, url in PUBLISHERS.items():
            with self.subTest(source=name):
                source = next(s for s in self.sources if s["name"] == name)
                self.assertEqual(source["candidate_official_url"], url)
                self.assertEqual(source["mode"], "discovery_pending")
                self.assertEqual(source["url"], "")
                self.assertIs(source["verified_url"], False)
                self.assertIn("individual", source["activation_gate"])
                self.assertEqual(source_health.classify(source, "")["direct_state"],
                                 "staged_official_url")
                row = next(r for r in audit["sources"] if r["source"] == name)
                self.assertTrue(row["official_url_staged"])
                self.assertFalse(row["direct_configured"])
                self.assertFalse(row["direct_fetch_target"])

    def test_published_health_is_metadata_not_a_new_contract_scan(self):
        counts = self.feed["source_health"]["counts"]
        self.assertEqual(counts["staged_official_url"], 52)
        self.assertEqual(counts["not_configured"], 32)
        self.assertEqual(self.feed["source_coverage"]["pending_direct"], 84)
        self.assertEqual(self.feed["source_coverage"]["verified_open_contracts"], 0)
        self.assertEqual(self.feed["opportunities"], [])
        for name, url in PUBLISHERS.items():
            row = next(r for r in self.feed["source_health"]["sources"]
                       if r["name"] == name)
            self.assertEqual(row["direct_state"], "staged_official_url")
            self.assertEqual(row["staged_official_url"], url)
            self.assertEqual(row["individual_bid_details_fetched"], 0)

    def test_meeting_cleanup_and_expired_paving_are_not_tree_bids(self):
        # Synthetic excerpts derived from official-page headings, not live bids.
        for text in (
            "Athens Borough Shade Tree Meeting October 21, 2026",
            "Sayre Borough Zone #1 Clean-Up community calendar event",
            "Troy Borough Paving Bid Results: Roadway Paving Contract bids "
            "due June 25, 2026",
        ):
            with self.subTest(text=text):
                self.assertIsNone(scan.category(text))
                self.assertFalse(scan.eligible(text, today=dt.date(2026, 10, 31)))

    def test_existing_erie_owego_exclusions_remain(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bids due October 23, 2025",
            today=dt.date(2026, 10, 31)))
        self.assertFalse(scan.eligible(
            "Owego building demolition and site preparation bids due November 5, 2026",
            today=dt.date(2026, 10, 31)))


if __name__ == "__main__":
    unittest.main()
