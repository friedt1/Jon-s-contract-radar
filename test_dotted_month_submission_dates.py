"""Offline dotted-month submission deadline regressions; no live bids."""
import datetime as dt
import unittest

from submission_deadlines import (
    explicit_closing_passed,
    submission_deadline,
    submission_deadline_details,
)
from scan import eligible


class DottedMonthSubmissionTests(unittest.TestCase):
    def test_every_dotted_month_abbreviation_with_explicit_clock(self):
        months = (
            ("Jan.", "01"), ("Feb.", "02"), ("Mar.", "03"),
            ("Apr.", "04"), ("Jun.", "06"), ("Jul.", "07"),
            ("Aug.", "08"), ("Sep.", "09"), ("Sept.", "09"),
            ("Oct.", "10"), ("Nov.", "11"), ("Dec.", "12"),
        )
        for month, number in months:
            with self.subTest(month=month):
                self.assertEqual(
                    submission_deadline_details(
                        f"Tree removal bids due {month} 10, 2026 at 1:45 PM"
                    ),
                    (f"2026-{number}-10", "1:45 PM"),
                )

    def test_dotted_month_before_date_clock_in_receipt_notice(self):
        self.assertEqual(
            submission_deadline_details(
                "Sealed bids will be received until 9:30 A.M. on Oct. 3rd, 2026"
            ),
            ("2026-10-03", "9:30 AM"),
        )
        self.assertEqual(
            submission_deadline_details(
                "Bids due at 2:15 PM on Nov. 12, 2026"
            ),
            ("2026-11-12", "2:15 PM"),
        )

    def test_earlier_dotted_month_addendum_supersedes_later_original(self):
        notice = (
            "Tree removal bids due Nov. 19, 2026 at 3:00 PM. "
            "Addendum No. 2: bids due Oct. 29, 2026 at 1:00 PM."
        )
        self.assertEqual(submission_deadline_details(notice),
                         ("2026-10-29", "1:00 PM"))
        self.assertEqual(submission_deadline(notice), "2026-10-29")
        self.assertTrue(explicit_closing_passed(
            notice, dt.datetime(2026, 11, 1, tzinfo=dt.timezone.utc)
        ))

    def test_dotted_question_deadline_not_bid_deadline(self):
        notice = (
            "Questions due Oct. 2, 2026 at 10:00 AM. "
            "Bids due Nov. 10, 2026 at 4:00 PM."
        )
        self.assertEqual(submission_deadline_details(notice),
                         ("2026-11-10", "4:00 PM"))
        self.assertEqual(
            submission_deadline_details("Questions due Oct. 2, 2026"),
            ("", ""),
        )

    def test_erie_and_owego_regressions_remain_non_live(self):
        today = dt.date(2026, 11, 1)
        self.assertFalse(eligible(
            "Erie tree and stump removal bids due Oct. 28, 2026",
            "PennBid platform", today=today,
        ))
        self.assertFalse(eligible(
            "Owego demolition and site restoration bids due Nov. 13, 2026",
            "Tioga County NY", today=today,
        ))


if __name__ == "__main__":
    unittest.main()
