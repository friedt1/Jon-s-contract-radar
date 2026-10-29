"""Offline synthetic public-bid wording; no real or open contracts are asserted."""
import datetime as dt
import unittest

import scan
from submission_deadlines import (
    submission_deadline,
    submission_deadline_details,
    explicit_closing_passed,
)


class BidReceiptDeadlineTests(unittest.TestCase):
    def test_sealed_bids_will_be_received_until(self):
        text = ("Sealed bids will be received until November 13, 2026 "
                "at 11:00 AM for tree removal.")
        self.assertEqual(submission_deadline_details(text),
                         ("2026-11-13", "11:00 AM"))
        self.assertEqual(scan.deadline(text), "2026-11-13")

    def test_proposals_must_be_submitted_by(self):
        text = "Tree trimming proposals must be submitted by 11/18/2026 at 2 PM"
        self.assertEqual(submission_deadline_details(text),
                         ("2026-11-18", "2:00 PM"))

    def test_shall_be_received_and_future_deadline(self):
        text = "Tree removal bids shall be received until 2026-11-10"
        self.assertEqual(submission_deadline(text), "2026-11-10")
        self.assertTrue(scan.eligible(text, "Test County",
                         today=dt.date(2026, 10, 29)))

    def test_questions_about_bids_not_submission(self):
        text = ("Questions about bids must be received by 11/20/2026 at 4 PM. "
                "Sealed bids will be received until 11/13/2026 at 11 AM.")
        self.assertEqual(submission_deadline_details(text),
                         ("2026-11-13", "11:00 AM"))
        self.assertEqual(submission_deadline(
            "Questions about bids must be received by 11/20/2026"), "")

    def test_bid_opening_not_assumed_submission(self):
        self.assertEqual(submission_deadline(
            "Tree removal bid opening November 13, 2026 at 11 AM"), "")

    def test_receipt_cutoff_expires_same_day(self):
        text = "Sealed bids will be received until 10/29/2026 at 11 AM"
        before = dt.datetime(2026, 10, 29, 14, tzinfo=dt.timezone.utc)
        after = dt.datetime(2026, 10, 29, 16, tzinfo=dt.timezone.utc)
        self.assertFalse(explicit_closing_passed(text, before))
        self.assertTrue(explicit_closing_passed(text, after))


if __name__ == "__main__":
    unittest.main()
