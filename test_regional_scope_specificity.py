"""Offline regional relevance regressions; synthetic examples are not live bids."""
import datetime as dt
import unittest

from regional_rank import build, classify


TODAY = dt.date(2026, 11, 2)
URL = "https://county.example/bids?bidID=901"


class RegionalScopeSpecificityTests(unittest.TestCase):
    def test_generic_storm_right_of_way_and_blocked_road_not_tree_work(self):
        # These phrases describe location or disaster context, not the
        # contractor's vegetation-clearing or debris-removal responsibilities.
        unrelated = (
            "Storm restoration RFP for electrical transformer replacement",
            "DOT right-of-way easement appraisal contract",
            "Blocked road bridge deck reconstruction RFP",
            "Utility right-of-way parcel survey and land acquisition",
            "Storm restoration contract for roof and HVAC repairs",
        )
        for title in unrelated:
            with self.subTest(title=title):
                notice = {"title": title, "url": URL, "deadline": "2026-11-20"}
                self.assertIsNone(classify(notice, today=TODAY))
                self.assertEqual(build([notice], today=TODAY)["opportunities"], [])

    def test_explicit_tree_debris_and_right_of_way_clearing_still_reviewable(self):
        relevant = (
            "Storm restoration contract for emergency tree removal",
            "DOT right-of-way clearing and brush removal RFP",
            "Utility right-of-way vegetation management services",
            "Blocked road debris removal following windstorm",
            "Power line clearing bid for distribution corridors",
            "Right of way clearing along county roads",
        )
        for title in relevant:
            with self.subTest(title=title):
                notice = {"title": title, "url": URL, "deadline": "2026-11-20"}
                result = classify(notice, today=TODAY)
                self.assertIsNotNone(result)
                self.assertEqual(result["status"], "review required")
                self.assertEqual(result["deadline_status"], "stated_unverified")
                self.assertFalse(result["travel_verified"])

    def test_excluded_work_and_historical_controls_not_promoted(self):
        notices = [
            {"title": "Right-of-way clearing by others; roadway resurfacing RFP",
             "url": URL, "deadline": "2026-11-20"},
            {"title": "Storm restoration electrical work; tree removal excluded",
             "url": URL + "&bidID=902", "deadline": "2026-11-20"},
            # Historical Erie and Owego examples remain negative controls.
            {"title": "Erie tree and stump removal bid",
             "url": URL + "&bidID=903", "deadline": "2026-10-28"},
            {"title": "Owego building demolition; tree removal by others",
             "url": URL + "&bidID=904", "deadline": "2026-11-13"},
        ]
        self.assertEqual(build(notices, today=TODAY)["opportunities"], [])


if __name__ == "__main__":
    unittest.main()
