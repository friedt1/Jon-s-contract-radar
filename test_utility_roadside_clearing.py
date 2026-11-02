"""Offline scope regressions for road/utility clearing; no live bids are seeded."""
import datetime as dt
import unittest

import regional_rank
import scan


NOW = dt.datetime(2026, 11, 2, 18, tzinfo=dt.timezone.utc)
TODAY = dt.date(2026, 11, 2)


class UtilityAndRoadsideScopeTests(unittest.TestCase):
    def test_explicit_utility_and_roadside_clearing_is_discoverable(self):
        for phrase in (
            "power line clearing", "powerline clearing",
            "transmission line clearing", "distribution line clearing",
            "utility line clearing", "roadside clearing",
            "roadway vegetation clearing",
        ):
            with self.subTest(phrase=phrase):
                notice = "Invitation to bid for " + phrase + " due November 20, 2026"
                self.assertEqual(scan.category(notice), "Vegetation management")
                self.assertTrue(scan.eligible(notice, today=TODAY, now=NOW))

    def test_unrelated_road_and_utility_work_is_not_admitted(self):
        for phrase in (
            "Bid for utility line painting and markings",
            "Bid for roadside snow plowing",
            "RFP for power line transformer replacement",
            "Bid for roadway resurfacing and asphalt repair",
        ):
            with self.subTest(phrase=phrase):
                self.assertIsNone(scan.category(phrase))
                self.assertFalse(scan.eligible(phrase, today=TODAY, now=NOW))

    def test_clearing_excluded_or_by_others_is_not_work_for_bidder(self):
        for phrase in (
            "Owego demolition bid; power line clearing by others",
            "Owego demolition bid; powerline clearing by owner",
            "Owego demolition bid; transmission line clearing excluded",
            "Owego demolition bid; distribution line clearing by others",
            "Owego demolition bid; utility line clearing by another contractor",
            "Owego demolition bid; roadside clearing by owner",
            "Owego demolition bid; roadway vegetation clearing excluded",
        ):
            with self.subTest(phrase=phrase):
                self.assertIsNone(scan.category(phrase))
                self.assertFalse(scan.eligible(phrase, today=TODAY, now=NOW))

    def test_separate_required_work_survives_an_exclusion(self):
        notice = ("Bid: power line clearing by others. "
                  "Roadside clearing is required of the successful bidder; "
                  "submissions due November 20, 2026")
        self.assertEqual(scan.category(notice), "Vegetation management")
        self.assertTrue(scan.eligible(notice, today=TODAY, now=NOW))

    def test_regional_review_remains_unverified(self):
        notice = {
            "title": "Invitation to bid", "summary": "Utility line clearing",
            "url": "https://county.example/bids/102",
            "deadline": "2026-11-20", "travel_verified": False,
        }
        result = regional_rank.classify(notice, today=TODAY, now=NOW)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "review required")
        self.assertEqual(result["distance_status"], "unverified")
        self.assertFalse(result["travel_verified"])
        notice["summary"] = "Utility line clearing by others; transformer replacement"
        self.assertIsNone(regional_rank.classify(notice, today=TODAY, now=NOW))

    def test_historical_erie_and_unrelated_owego_stay_excluded(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            today=TODAY, now=NOW))
        self.assertFalse(scan.eligible(
            "Owego demolition bid due November 13, 2026; tree removal by others",
            today=TODAY, now=NOW))


if __name__ == "__main__":
    unittest.main()
