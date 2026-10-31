"""Offline regression tests for explicit 24-hour bid submission times.

All examples are synthetic; none represents a live procurement notice.
"""
import datetime as dt
import unittest

from submission_deadlines import (
    submission_deadline,
    submission_deadline_details,
    explicit_closing_passed,
)


class TwentyFourHourDeadlineTests(unittest.TestCase):
    def test_after_date_24_hour_clock(self):
        self.assertEqual(
            submission_deadline_details("Tree removal bids due November 3, 2026 at 14:30"),
            ("2026-11-03", "2:30 PM"),
        )
        self.assertEqual(
            submission_deadline_details("Tree removal bids due 2026-11-03, at 09:05 hours"),
            ("2026-11-03", "9:05 AM"),
        )

    def test_before_date_24_hour_clock(self):
        self.assertEqual(
            submission_deadline_details("Sealed bids will be received until 15:45 on November 3, 2026"),
            ("2026-11-03", "3:45 PM"),
        )
        self.assertEqual(
            submission_deadline_details("Bids due 16:00 on November 3, 2026"),
            ("2026-11-03", "4:00 PM"),
        )

    def test_same_day_expiration_respects_24_hour_time(self):
        after = dt.datetime(2026, 11, 3, 20, 0, tzinfo=dt.timezone.utc)
        before = dt.datetime(2026, 11, 3, 18, 0, tzinfo=dt.timezone.utc)
        notice = "Tree removal bids due November 3, 2026 at 14:30"
        self.assertTrue(explicit_closing_passed(notice, after))
        self.assertFalse(explicit_closing_passed(notice, before))

    def test_preserve_am_pm_and_no_unlabeled_clock_guess(self):
        self.assertEqual(
            submission_deadline_details("Bids due November 3, 2026 at 2:00 P.M."),
            ("2026-11-03", "2:00 PM"),
        )
        self.assertEqual(
            submission_deadline_details("Bids due November 3, 2026 at 2:00 AM"),
            ("2026-11-03", "2:00 AM"),
        )
        self.assertEqual(
            submission_deadline_details("Bids due November 3, 2026. Bid opening at 14:30."),
            ("2026-11-03", ""),
        )

    def test_questions_are_not_submission_deadlines(self):
        notice = ("Questions due November 2, 2026 at 13:00. "
                  "Bids due November 3, 2026 at 16:00.")
        self.assertEqual(submission_deadline_details(notice),
                         ("2026-11-03", "4:00 PM"))

    def test_numbered_amendment_earlier_cutoff(self):
        notice = ("Original bids due November 10, 2026 at 16:00. "
                  "Addendum No. 2: bids due November 3, 2026 at 13:00.")
        self.assertEqual(submission_deadline(notice), "2026-11-03")
        self.assertEqual(submission_deadline_details(notice),
                         ("2026-11-03", "1:00 PM"))


if __name__ == "__main__":
    unittest.main()
