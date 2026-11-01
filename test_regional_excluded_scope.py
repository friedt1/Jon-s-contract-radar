"""Synthetic regional scope regressions; never seed or claim live contracts."""
import datetime as dt
import unittest

import scan
from regional_rank import build, classify


TODAY = dt.date(2026, 11, 1)
URL = "https://county.example/bids?bidID=44"


class RegionalExcludedScopeTests(unittest.TestCase):
    def test_negated_tree_work_does_not_create_regional_demolition_lead(self):
        notices = (
            "Owego demolition RFP; tree removal by others",
            "Owego demolition bid; no tree removal required",
            "Owego demolition contract; stump removal excluded",
            "Owego demolition RFP; vegetation management not in scope",
            "Owego demolition bid; land clearing not required",
            "Owego demolition RFP without brush clearing",
        )
        for title in notices:
            with self.subTest(title=title):
                notice = {"title": title, "url": URL,
                          "deadline": "2026-11-19"}
                self.assertIsNone(scan.category(title))
                self.assertIsNone(classify(notice, today=TODAY))
                self.assertEqual(build([notice], today=TODAY)["opportunities"], [])

    def test_excluded_storm_and_line_work_never_enters_regional_feed(self):
        for title in (
            "Owego demolition RFP; tree clearing by others",
            "Paving contract; right-of-way clearing excluded",
            "Bridge rehabilitation RFP; power line clearing by others",
            "Road repair bid; line clearance not included",
            "Building demolition contract; storm cleanup by others",
            "Owego demolition RFP; disaster debris removal not required",
            "Paving bid without woody debris removal",
            "Bridge repairs RFP; roadside mowing by others",
        ):
            with self.subTest(title=title):
                notice = {"title": title, "url": URL,
                          "deadline": "2026-11-19"}
                self.assertIsNone(classify(notice, today=TODAY))
                self.assertEqual(build([notice], today=TODAY)["opportunities"], [])

    def test_positive_tree_or_brush_work_survives_other_exclusions(self):
        for title in (
            "Tree removal bid; vegetation management by others",
            "Brush clearing RFP; tree removal excluded",
            "Disaster debris removal contract; stump grinding not required",
        ):
            with self.subTest(title=title):
                notice = {"title": title, "url": URL,
                          "deadline": "2026-11-19"}
                result = classify(notice, today=TODAY)
                self.assertIsNotNone(result)
                self.assertEqual(result["status"], "review required")
                self.assertEqual(result["deadline_status"], "stated_unverified")

    def test_excluded_scope_duplicate_cannot_invent_deadline_conflict(self):
        positive = {"title": "Brush clearing contract",
                    "url": URL, "deadline": "2026-11-19"}
        excluded = {"title": "Owego demolition; tree removal by others",
                    "url": URL + "&utm_source=county",
                    "deadline": "2026-11-05"}
        for notices in ([positive, excluded], [excluded, positive]):
            with self.subTest(order=notices[0]["title"]):
                items = build(notices, today=TODAY)["opportunities"]
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0]["deadline"], "2026-11-19")
                self.assertNotIn("deadline_conflict", items[0])

    def test_historical_erie_expired_and_owego_unrelated_stay_excluded(self):
        erie = {"title": "Erie tree and stump removal",
                "url": "https://county.example/bids?bidID=45",
                "deadline": "2026-10-28"}
        owego = {"title": "Owego demolition; tree removal by others",
                 "url": URL, "deadline": "2026-11-13"}
        self.assertEqual(build([erie, owego], today=TODAY)["opportunities"], [])


if __name__ == "__main__":
    unittest.main()
