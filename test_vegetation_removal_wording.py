"""Synthetic vegetation-removal scope regressions; no real bids are seeded."""
import datetime as dt
import unittest

import scan


class VegetationRemovalWordingTests(unittest.TestCase):
    TODAY = dt.date(2026, 11, 1)

    def test_positive_vegetation_removal_is_a_separate_service_category(self):
        for wording in (
            "Vegetation Removal",
            "Removal of Vegetation",
            "Vegetation Clearing",
            "Invasive Vegetation Removal",
        ):
            with self.subTest(wording=wording):
                self.assertEqual(scan.category(wording + " RFP"),
                                 "Vegetation management")
                self.assertTrue(scan.eligible(
                    wording + " Bid due November 19, 2026",
                    today=self.TODAY))

    def test_excluded_vegetation_work_cannot_turn_demolition_into_a_lead(self):
        for wording in (
            "Owego demolition RFP; vegetation removal by others",
            "Owego demolition bid: no vegetation removal required",
            "Building demolition contract; removal of vegetation excluded",
            "Road paving RFP without vegetation clearing",
            "Owego demolition RFP; invasive vegetation removal not included",
        ):
            with self.subTest(wording=wording):
                self.assertIsNone(scan.category(wording))
                self.assertFalse(scan.eligible(wording, today=self.TODAY))

    def test_positive_work_survives_separate_excluded_work(self):
        self.assertEqual(
            scan.category("Vegetation clearing RFP; tree removal by others"),
            "Vegetation management")
        self.assertEqual(
            scan.category("Tree and vegetation removal bid"),
            "Tree removal")
        self.assertEqual(
            scan.category("Owego demolition and site grading RFP; "
                          "vegetation removal by others"),
            "Related site prep")

    def test_historical_and_out_of_region_are_not_live_contracts(self):
        self.assertFalse(scan.eligible(
            "Erie PA vegetation removal bid due October 29, 2026",
            today=self.TODAY))
        self.assertFalse(scan.eligible(
            "Erie PA vegetation removal bid due November 19, 2026",
            source="PennBid platform", today=self.TODAY))
        self.assertFalse(scan.eligible(
            "Owego demolition RFP; vegetation removal by others; "
            "bids due November 19, 2026", today=self.TODAY))

    def test_candidate_remains_unverified_not_an_open_contract(self):
        found = {}
        scan.add_lead(
            found, "Synthetic County",
            "Vegetation removal bid",
            "https://county.example/bids/123",
            "Removal of vegetation; deadline not confirmed",
            kind="direct detail candidate",
        )
        self.assertEqual(len(found), 1)
        item = next(iter(found.values()))
        self.assertEqual(item["category"], "Vegetation management")
        self.assertEqual(item["status"], "unverified")
        self.assertNotEqual(item.get("open_status"), "verified_open")


if __name__ == "__main__":
    unittest.main()
