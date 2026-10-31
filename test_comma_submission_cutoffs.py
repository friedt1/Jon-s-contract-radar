"""Synthetic receipt/deadline punctuation regressions, never live bids."""
import datetime as dt
import unittest

import scan
from submission_deadlines import submission_deadline_details, explicit_closing_passed


class CommaSeparatedSubmissionCutoffTests(unittest.TestCase):
    def test_dotted_receipt_clock_followed_by_comma_and_on(self):
        notice = ("Tree removal sealed bids will be received until "
                  "1:45 P.M., on October 23,2025, where they will be opened at 2 PM.")
        self.assertEqual(submission_deadline_details(notice),
                         ("2025-10-23", "1:45 PM"))

    def test_receipt_clock_comma_without_on(self):
        notice = "Sealed bids will be received until 14:30, November 3, 2026"
        self.assertEqual(submission_deadline_details(notice),
                         ("2026-11-03", "2:30 PM"))

    def test_due_clock_comma_before_date(self):
        notice = "Tree trimming bids due 3:00 PM, November 3, 2026"
        self.assertEqual(submission_deadline_details(notice),
                         ("2026-11-03", "3:00 PM"))

    def test_local_time_before_date(self):
        notice = "Sealed proposals due at 14:30 local time on November 3, 2026"
        self.assertEqual(submission_deadline_details(notice),
                         ("2026-11-03", "2:30 PM"))

    def test_same_day_receipt_cutoff_is_not_kept_live(self):
        notice = "Tree removal bids will be received until 14:30, November 3, 2026"
        self.assertFalse(explicit_closing_passed(
            notice, dt.datetime(2026, 11, 3, 18, tzinfo=dt.timezone.utc)))
        self.assertTrue(explicit_closing_passed(
            notice, dt.datetime(2026, 11, 3, 20, tzinfo=dt.timezone.utc)))

    def test_questions_and_bid_openings_do_not_supply_deadlines(self):
        self.assertEqual(submission_deadline_details(
            "Questions about bids will be received until 14:30, November 3, 2026"),
            ("", ""))
        self.assertEqual(submission_deadline_details(
            "Tree removal bid opening at 14:30, November 3, 2026"),
            ("", ""))

    def test_historical_erie_and_unrelated_owego_remain_excluded(self):
        erie = "Erie PA tree & stump removal bids due 10/29/2026"
        owego = "Owego demolition rebid due 11/13/2026"
        self.assertFalse(scan.eligible(erie, "PennBid platform",
                                       today=dt.date(2026, 10, 31)))
        self.assertIsNone(scan.category(owego))


if __name__ == "__main__":
    unittest.main()
