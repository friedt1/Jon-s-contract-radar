"""Offline September-abbreviation deadline tests; no live bids are created."""
import datetime as dt
import unittest

from submission_deadlines import (
    explicit_closing_passed,
    submission_deadline,
    submission_deadline_details,
)
from scan import eligible


class SeptemberBidDeadlineTests(unittest.TestCase):
    def test_september_abbreviations_are_submission_dates(self):
        for month in ("Sep", "Sep.", "Sept", "Sept.", "September"):
            with self.subTest(month=month):
                self.assertEqual(
                    submission_deadline_details(
                        f"Tree removal bids due {month} 10, 2026 at 1:45 PM"
                    ),
                    ("2026-09-10", "1:45 PM"),
                )

    def test_abbreviation_with_ordinal_and_receipt_before_date(self):
        self.assertEqual(
            submission_deadline_details(
                "Sealed bids will be received until 9:30 A.M. on Sept. 3rd, 2026"
            ),
            ("2026-09-03", "9:30 AM"),
        )

    def test_revised_earlier_september_deadline_supersedes_original(self):
        notice = (
            "Original bids due October 5, 2026 at 4:00 PM. "
            "Addendum No. 2: bids due Sept. 29, 2026 at 1:00 PM."
        )
        self.assertEqual(submission_deadline(notice), "2026-09-29")
        self.assertEqual(submission_deadline_details(notice),
                         ("2026-09-29", "1:00 PM"))

    def test_september_question_deadline_is_not_bid_deadline(self):
        notice = (
            "Questions due Sept. 1, 2026 at 2:00 PM. "
            "Bids due Sept. 10, 2026 at 11:00 AM."
        )
        self.assertEqual(submission_deadline_details(notice),
                         ("2026-09-10", "11:00 AM"))

    def test_expired_same_day_abbreviated_deadline(self):
        notice = "Bids due Sept. 10, 2026 at 9:00 AM"
        before = dt.datetime(2026, 9, 10, 12, tzinfo=dt.timezone.utc)
        after = dt.datetime(2026, 9, 10, 14, tzinfo=dt.timezone.utc)
        self.assertFalse(explicit_closing_passed(notice, before))
        self.assertTrue(explicit_closing_passed(notice, after))

    def test_erie_expired_and_owego_unrelated_still_excluded(self):
        today = dt.date(2026, 11, 1)
        self.assertFalse(eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            "PennBid platform", today=today))
        self.assertFalse(eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            "Tioga County NY", today=today))


if __name__ == "__main__":
    unittest.main()
