"""Synthetic negative-scope regression cases. No live bids are seeded."""
import datetime as dt
import unittest

import scan


class ExcludedWorkScopeTests(unittest.TestCase):
    TODAY = dt.date(2026, 10, 31)

    def test_negated_tree_work_does_not_create_a_tree_contract(self):
        notices = (
            "Owego building demolition RFP: tree removal by others",
            "Owego demolition bid; no tree removal required",
            "Demolition contract: tree removal is excluded",
            "Building demolition RFP; tree trimming not included",
            "Demolition bid: stump grinding not required",
            "Demolition RFP without brush removal",
            "Owego demolition RFP: tree and vegetation removal by others",
            "Owego demolition bid: no tree & vegetation removal required",
            "Owego demolition RFP: removal of trees and vegetation excluded",
        )
        for notice in notices:
            with self.subTest(notice=notice):
                self.assertIsNone(scan.category(notice))
                self.assertFalse(scan.eligible(notice, today=self.TODAY))

    def test_excluded_storm_line_and_right_of_way_work_is_not_a_lead(self):
        # A demolition/road contract can mention tree-adjacent work solely
        # to exclude it. Such text must not create a tree-service candidate.
        notices = (
            "Owego demolition bid; tree clearing by others",
            "Road paving RFP; right-of-way clearing excluded",
            "Bridge repairs contract; line clearance not included",
            "Building demolition RFP; storm cleanup by others",
            "Paving contract; disaster debris removal not required",
            "Bridge RFP without woody debris removal",
            "Road repair bid; roadside mowing by others",
            "Demolition RFP; forestry mowing excluded",
        )
        for notice in notices:
            with self.subTest(notice=notice):
                self.assertIsNone(scan.category(notice))
                self.assertFalse(scan.eligible(notice, today=self.TODAY))

    def test_positive_tree_work_survives_excluded_storm_work(self):
        notice = ("Tree removal bid on county property; "
                  "storm debris removal by others; bids due November 19, 2026")
        self.assertEqual(scan.category(notice), "Tree removal")
        self.assertTrue(scan.eligible(notice, today=self.TODAY))

    def test_actual_sitework_remains_separately_labeled(self):
        notice = ("Owego demolition and site grading RFP; "
                  "tree removal by others; bids due November 19, 2026")
        self.assertEqual(scan.category(notice), "Related site prep")
        self.assertTrue(scan.eligible(notice, today=self.TODAY))

    def test_other_positive_work_survives_local_exclusion(self):
        self.assertEqual(
            scan.category("Brush clearing bid; tree removal not included"),
            "Vegetation management")
        self.assertEqual(
            scan.category("Tree removal required; tree trimming excluded RFP"),
            "Tree removal")
        self.assertEqual(
            scan.category("Tree removal and stump grinding RFP"),
            "Tree removal")

    def test_historical_erie_and_unrelated_owego_remain_excluded(self):
        self.assertFalse(scan.eligible(
            "Erie PA tree and stump removal bid due October 23, 2025",
            today=self.TODAY))
        self.assertFalse(scan.eligible(
            "Owego demolition RFP: tree removal by others; "
            "bids due November 13, 2026",
            today=self.TODAY))


if __name__ == "__main__":
    unittest.main()
