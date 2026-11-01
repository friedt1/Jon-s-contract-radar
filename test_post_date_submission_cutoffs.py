"""Offline deadline regression cases; synthetic notices are never published."""
import datetime as dt
import unittest

import scan
from submission_deadlines import (
    submission_deadline_details, explicit_closing_passed,
)


class PostDateCutoffTests(unittest.TestCase):
    def test_by_after_dotted_month_date_is_an_explicit_clock(self):
        notice = "Sealed tree-trimming bids due Nov. 2, 2026 by 2:30 P.M."
        self.assertEqual(
            submission_deadline_details(notice), ("2026-11-02", "2:30 PM"))
        self.assertTrue(explicit_closing_passed(
            notice, dt.datetime(2026, 11, 2, 19, 31,
                                tzinfo=dt.timezone.utc)))

    def test_no_later_than_with_24_hour_clock(self):
        notice = "Tree removal proposals due 11/02/2026 no later than 14:00"
        self.assertEqual(
            submission_deadline_details(notice), ("2026-11-02", "2:00 PM"))
        self.assertFalse(explicit_closing_passed(
            notice, dt.datetime(2026, 11, 2, 18, 59,
                                tzinfo=dt.timezone.utc)))

    def test_until_after_date_is_submission_cutoff(self):
        self.assertEqual(
            submission_deadline_details(
                "Vegetation management bids due 11-02-2026 until 1:15 PM"),
            ("2026-11-02", "1:15 PM"))

    def test_earlier_revised_by_cutoff_supersedes_original(self):
        notice = (
            "Tree removal bids due 11/19/2026 at 4:00 PM. "
            "Amendment 3: bids due 11/02/2026 by 1:00 PM.")
        self.assertEqual(
            submission_deadline_details(notice), ("2026-11-02", "1:00 PM"))

    def test_questions_and_meetings_do_not_supply_bid_clock(self):
        notice = (
            "Tree removal bids due 11/02/2026; "
            "questions due 11/18/2026 by 5:00 PM; "
            "pre-bid meeting at 2:00 PM on 11/01/2026")
        self.assertEqual(
            submission_deadline_details(notice), ("2026-11-02", ""))

    def test_unrelated_clock_is_not_inferred(self):
        notice = "Tree removal bids due 11/02/2026. Bid opening at 4:00 PM."
        self.assertEqual(
            submission_deadline_details(notice), ("2026-11-02", ""))

    def test_historical_erie_and_unrelated_owego_are_not_live(self):
        erie = "Erie PA tree and stump removal bids due 10/29/2026 by 2 PM"
        owego = "Owego NY demolition rebid due 11/13/2026 by 2 PM"
        self.assertFalse(scan.eligible(
            erie, today=dt.date(2026, 11, 1)))
        self.assertIsNone(scan.category(owego))


if __name__ == "__main__":
    unittest.main()
