"""Demolition-only scope must not become a related site-prep tree lead.

Synthetic fixtures only. Historical Erie/Owego are exclusion regressions,
not seeded procurement opportunities or evidence of an open solicitation.
"""
import datetime as dt
import unittest
from unittest.mock import patch

import scan


class DemolitionScopeGateTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(
            scan, "NOW", dt.datetime(2026, 10, 31, 18, tzinfo=dt.timezone.utc)
        )
        clock.start()
        self.addCleanup(clock.stop)

    def test_tree_protection_does_not_turn_demolition_into_site_prep(self):
        for notice in (
            "Owego building demolition and site preparation bid due November 10, 2026; "
            "existing trees must be protected",
            "Demolition and site preparation RFP: preserve vegetation and landscape buffers",
            "Demolition and site preparation bid with tree protection fencing",
            "Razing and site prep contract: existing trees to remain undisturbed",
        ):
            with self.subTest(notice=notice):
                self.assertIsNone(scan.category(notice))
                self.assertFalse(scan.eligible(notice))
                found = {}
                scan.add_lead(found, "Synthetic County", notice,
                              "https://example.gov/bids/notice-1")
                self.assertEqual(found, {})

    def test_substantive_sitework_still_qualifies_as_related_not_tree(self):
        for notice, expected in (
            ("Building demolition and site grading bid due November 10, 2026",
             "Related site prep"),
            ("Demolition and site preparation with excavation and grading RFP",
             "Related site prep"),
            # Explicit clearing takes precedence under the existing core
            # category hierarchy; never mislabel it as adjacent site prep.
            ("Razing and site preparation including clearing and grubbing contract",
             "Land clearing"),
        ):
            with self.subTest(notice=notice):
                self.assertEqual(scan.category(notice), expected)
                self.assertTrue(scan.eligible(notice))
                found = {}
                scan.add_lead(found, "Synthetic County", notice,
                              "https://example.gov/bids/sitework")
                self.assertEqual(len(found), 1)
                lead = next(iter(found.values()))
                self.assertEqual(lead["category"], expected)
                self.assertEqual(lead["status"], "unverified")

    def test_explicit_tree_removal_still_takes_precedence(self):
        self.assertEqual(
            scan.category("Tree removal and building demolition RFP"),
            "Tree removal"
        )

    def test_historical_erie_expired_and_owego_unrelated(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bids due October 23, 2025",
            today=dt.date(2026, 10, 31)))
        self.assertFalse(scan.eligible(
            "Owego building demolition and site preparation bids due November 10, 2026",
            today=dt.date(2026, 10, 31)))


if __name__ == "__main__":
    unittest.main()
