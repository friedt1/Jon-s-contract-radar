"""Offline amendment regressions. Synthetic examples are not live bids."""
import datetime as dt
import unittest

from submission_deadlines import (
    submission_deadline, submission_deadline_details, explicit_closing_passed,
)


class EarlierAmendmentTests(unittest.TestCase):
    def test_amendment_can_move_future_deadline_into_the_past(self):
        text = ("Tree removal bids due 11/19/2026 at 3:00 PM. "
                "Amendment: bids due 10/29/2026 at 1:00 PM.")
        self.assertEqual(submission_deadline(text), "2026-10-29")
        self.assertEqual(submission_deadline_details(text),
                         ("2026-10-29", "1:00 PM"))
        self.assertTrue(explicit_closing_passed(
            text, dt.datetime(2026, 10, 30, 1, tzinfo=dt.timezone.utc)))

    def test_date_only_earlier_revision_clears_original_clock(self):
        text = ("Tree trimming bids due 11/19/2026 at 3:00 PM; "
                "Revised bids due 10/29/2026")
        self.assertEqual(submission_deadline_details(text), ("2026-10-29", ""))
        self.assertEqual(submission_deadline(text), "2026-10-29")

    def test_addendum_receipt_before_date_earlier(self):
        text = ("Sealed bids will be received until 2:00 PM on Nov 19, 2026. "
                "Addendum 2: sealed bids will be received until 1:00 PM "
                "on Oct 29, 2026.")
        self.assertEqual(submission_deadline_details(text),
                         ("2026-10-29", "1:00 PM"))

    def test_question_revision_cannot_change_bid_submission(self):
        text = ("Bids due 11/19/2026 at 3:00 PM. "
                "Amendment: questions due 10/29/2026 at 1:00 PM.")
        self.assertEqual(submission_deadline_details(text),
                         ("2026-11-19", "3:00 PM"))

    def test_unmarked_dates_keep_latest_date_for_conservative_review(self):
        text = "Bids due 11/19/2026; bids due 10/29/2026"
        self.assertEqual(submission_deadline_details(text),
                         ("2026-11-19", ""))

    def test_erie_expired_and_owego_unrelated_remain_regressions(self):
        import scan
        erie = ("Erie PA tree and stump removal bids due 11/19/2026. "
                "Amended: bids due 10/29/2026 at 1 PM")
        owego = "Owego demolition rebid due 11/19/2026"
        self.assertEqual(submission_deadline(erie), "2026-10-29")
        self.assertFalse(scan.eligible(erie, "PennBid platform"))
        self.assertIsNone(scan.category(owego))


if __name__ == "__main__":
    unittest.main()
