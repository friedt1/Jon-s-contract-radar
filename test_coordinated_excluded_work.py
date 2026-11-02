"""Regression cases for coordinated excluded work in public bid notices.

Synthetic text only; no real opportunities are seeded or marked open.
"""
import datetime as dt
import unittest

import scan


class CoordinatedExcludedWorkTests(unittest.TestCase):
    TODAY = dt.date(2026, 11, 2)

    def test_negated_multi_service_work_cannot_become_a_tree_lead(self):
        notices = (
            "Owego demolition RFP: no tree removal or stump grinding required",
            "Owego demolition bid: tree removal and stump grinding by others",
            "Owego demolition bid: tree removal and stump grinding will be performed by owner",
            "Demolition RFP: tree and stump removal shall be handled by the owner",
            "Demolition bid: removal of trees will be completed by another contractor",
            "Owego demolition contract: tree removal is not part of this contract",
            "Demolition RFP: tree trimming is to be performed by others",
            "Owego demolition bid: no tree removal and brush removal",
        )
        for notice in notices:
            with self.subTest(notice=notice):
                self.assertIsNone(scan.category(notice))
                self.assertFalse(scan.eligible(notice, today=self.TODAY))
                found = {}
                scan.add_lead(
                    found, "Synthetic County", notice,
                    "https://example.gov/bids/synthetic-notice",
                )
                self.assertEqual(found, {})

    def test_positive_scope_survives_adjacent_excluded_scope(self):
        cases = (
            ("Brush clearing bid; tree removal and stump grinding by others",
             "Vegetation management"),
            ("Tree removal required; stump grinding will be performed by owner",
             "Tree removal"),
            ("Owego demolition and site grading RFP; tree removal will be "
             "performed by others", "Related site prep"),
            ("Tree removal and stump grinding required by this bid",
             "Tree removal"),
            ("Tree and stump removal bid due November 19, 2026",
             "Tree removal"),
        )
        for notice, expected in cases:
            with self.subTest(notice=notice):
                self.assertEqual(scan.category(notice), expected)

    def test_historical_erie_and_unrelated_owego_stay_excluded(self):
        self.assertFalse(scan.eligible(
            "Erie PA tree and stump removal bid due October 23, 2025",
            today=self.TODAY))
        self.assertFalse(scan.eligible(
            "Owego demolition RFP: tree removal and stump grinding by others; "
            "bids due November 19, 2026", today=self.TODAY))


if __name__ == "__main__":
    unittest.main()
