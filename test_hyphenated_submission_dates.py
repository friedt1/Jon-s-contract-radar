"""Offline tests: dash-separated agency deadlines are not live bid claims."""
import datetime as dt
import unittest

import scan
from submission_deadlines import (
    submission_deadline, submission_deadline_details, explicit_closing_passed,
)


class HyphenatedSubmissionDateTests(unittest.TestCase):
    def test_dash_date_with_explicit_clock(self):
        text = "Tree removal bids due 11-02-2026 at 2:30 PM"
        self.assertEqual(
            submission_deadline_details(text), ("2026-11-02", "2:30 PM"))
        self.assertTrue(explicit_closing_passed(
            text, dt.datetime(2026, 11, 2, 19, 31,
                              tzinfo=dt.timezone.utc)))

    def test_short_year_and_iso_remain_distinct(self):
        self.assertEqual(
            submission_deadline("Tree trimming proposals due 11-02-26"),
            "2026-11-02")
        self.assertEqual(
            submission_deadline("Tree trimming proposals due 2026-11-02"),
            "2026-11-02")
        self.assertEqual(
            submission_deadline("Tree trimming proposals due 11/02/2026"),
            "2026-11-02")

    def test_question_date_does_not_extend_bid_cutoff(self):
        text = ("Tree removal bids due 10-29-2026 at 1:00 PM; "
                "Questions due 11-20-2026; site visit due 11-05-2026")
        self.assertEqual(
            submission_deadline_details(text), ("2026-10-29", "1:00 PM"))

    def test_earlier_dash_amendment_supersedes_original(self):
        text = ("Tree removal bids due 11/19/2026 at 3:00 PM. "
                "Amendment 2: bids due 10-29-2026 at 1:00 PM.")
        self.assertEqual(
            submission_deadline_details(text), ("2026-10-29", "1:00 PM"))

    def test_invalid_dash_dates_are_not_guessed(self):
        for text in (
            "Tree removal bids due 13-02-2026",
            "Tree removal bids due 02-30-2026",
        ):
            with self.subTest(text=text):
                self.assertEqual(submission_deadline(text), "")

    def test_historical_erie_and_unrelated_owego_stay_excluded(self):
        erie = "Erie PA tree and stump removal bids due 10-29-2026"
        owego = "Owego NY demolition rebid due 11-13-2026"
        self.assertEqual(submission_deadline(erie), "2026-10-29")
        self.assertFalse(scan.eligible(
            erie, today=dt.date(2026, 11, 1)))
        self.assertIsNone(scan.category(owego))


if __name__ == "__main__":
    unittest.main()
