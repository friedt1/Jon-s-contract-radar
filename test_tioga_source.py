"""Regression checks for official Tioga procurement coverage and lead honesty."""
import json
import pathlib
import unittest

import scan


class TiogaSourceTests(unittest.TestCase):
    def test_tioga_is_direct_official_source(self):
        sources = json.loads((pathlib.Path(__file__).parent / "sources.json").read_text())
        tioga = next(s for s in sources if s["name"] == "Tioga County NY")
        self.assertEqual(tioga["mode"], "direct_page")
        self.assertEqual(tioga["url"], "https://tiogacountyny.com/departments/public-works/")
        self.assertEqual(len(sources), 102)

    def test_demolition_is_not_mislabeled_tree_service(self):
        notice = ("NOTICE TO BIDDERS Tioga County invites sealed bids for "
                  "67 Central Ave Demolition Project Rebid, Owego, NY. "
                  "Complete demolition and site restoration. "
                  "Bids due November 13, 2026.")
        self.assertIsNone(scan.category(notice))
        self.assertFalse(scan.eligible(notice, "Tioga County NY"))

    def test_tree_bid_remains_relevant_but_not_verified(self):
        notice = "Bid 6565-26 TREE & STUMP REMOVAL AT VARIOUS LOCATIONS"
        self.assertEqual(scan.category(notice), "Tree removal")
        self.assertFalse(scan.eligible(notice, "PennBid platform"))


if __name__ == "__main__":
    unittest.main()
