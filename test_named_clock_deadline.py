"""Synthetic deadline wording only; never seed or assert live opportunities."""
import datetime as dt
import unittest

from submission_deadlines import submission_deadline_details, explicit_closing_passed


class NamedSubmissionClockTests(unittest.TestCase):
    def test_noon_date_first(self):
        for wording in (
            "Sealed bids due November 3, 2026 at noon.",
            "Bids due November 3, 2026 at 12 noon.",
            "Proposals due November 3, 2026 at 12:00 noon.",
            "Submission deadline: 2026-11-03, at NOON",
        ):
            with self.subTest(wording=wording):
                self.assertEqual(
                    submission_deadline_details(wording),
                    ("2026-11-03", "12:00 PM"),
                )

    def test_noon_clock_first(self):
        self.assertEqual(
            submission_deadline_details(
                "Sealed bids due at noon on November 3, 2026"
            ),
            ("2026-11-03", "12:00 PM"),
        )

    def test_midnight_date_first_and_received_before_date(self):
        self.assertEqual(
            submission_deadline_details(
                "Bids due November 3, 2026 at midnight."
            ),
            ("2026-11-03", "12:00 AM"),
        )
        self.assertEqual(
            submission_deadline_details(
                "Sealed bids will be received until 12 midnight on November 3, 2026"
            ),
            ("2026-11-03", "12:00 AM"),
        )

    def test_same_day_noon_cutoff_is_eastern_local(self):
        notice = "Tree removal bids due November 3, 2026 at noon."
        before = dt.datetime(2026, 11, 3, 16, 59, tzinfo=dt.timezone.utc)
        after = dt.datetime(2026, 11, 3, 17, 1, tzinfo=dt.timezone.utc)
        self.assertFalse(explicit_closing_passed(notice, before))
        self.assertTrue(explicit_closing_passed(notice, after))

    def test_opening_and_question_clocks_do_not_become_submission_times(self):
        self.assertEqual(
            submission_deadline_details(
                "Questions due November 3, 2026 at noon. "
                "Bids due November 5, 2026. Bid opening at 2 PM."
            ),
            ("2026-11-05", ""),
        )
        self.assertEqual(
            submission_deadline_details(
                "Bid opening November 3, 2026 at noon."
            ),
            ("", ""),
        )

    def test_not_partial_named_clock_or_unlabelled_time(self):
        self.assertEqual(
            submission_deadline_details(
                "Bids due November 3, 2026 at noontime."
            ),
            ("2026-11-03", ""),
        )
        self.assertEqual(
            submission_deadline_details(
                "Bids due November 3, 2026. Site visit at midnight."
            ),
            ("2026-11-03", ""),
        )


if __name__ == "__main__":
    unittest.main()
