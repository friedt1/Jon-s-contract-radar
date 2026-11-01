"""Synthetic excluded generic service scope; never create live bid records."""
import datetime as dt
import unittest

import scan


class GenericServiceExclusionTests(unittest.TestCase):
    TODAY = dt.date(2026, 10, 31)

    def test_generic_tree_work_exclusions_do_not_create_demolition_leads(self):
        for notice in (
            "Owego demolition RFP; tree work by others",
            "Owego building demolition bid; no tree work required",
            "Demolition contract; tree services excluded",
            "Demolition RFP; tree service not in scope",
            "Demolition bid; vegetation management by others",
            "Demolition RFP; land clearing excluded",
            "Demolition RFP; forestry mulching not required",
        ):
            with self.subTest(notice=notice):
                self.assertIsNone(scan.category(notice))
                self.assertFalse(scan.eligible(notice, today=self.TODAY))
                found = {}
                scan.add_lead(found, "Synthetic County", notice,
                              "https://example.org/bids/not-real")
                self.assertEqual(found, {})

    def test_other_explicit_positive_work_remains_visible(self):
        self.assertEqual(scan.category(
            "Brush clearing RFP; tree work by others"), "Vegetation management")
        self.assertEqual(scan.category(
            "Tree removal RFP; vegetation management by others"), "Tree removal")
        self.assertEqual(scan.category(
            "Demolition and site grading bid; tree work by others"), "Related site prep")
        self.assertEqual(scan.category(
            "Tree services RFP: remove hazardous trees"), "Tree removal")

    def test_historical_erie_and_owego_stay_excluded(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            today=self.TODAY))
        self.assertFalse(scan.eligible(
            "Owego demolition RFP; tree work by others; bids due November 13, 2026",
            today=self.TODAY))


if __name__ == "__main__":
    unittest.main()
