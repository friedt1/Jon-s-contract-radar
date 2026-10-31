"""Synthetic numbered-addendum deadline regressions; no live bids are seeded."""
import datetime as dt
import unittest

import scan
from submission_deadlines import (
    explicit_closing_passed, submission_deadline, submission_deadline_details,
)


class NumberedAddendumDeadlineTests(unittest.TestCase):
    def test_numbered_addendum_can_move_bid_deadline_earlier(self):
        notice = (
            "Tree removal bids due 11/19/2026 at 3:00 PM. "
            "Addendum No. 2: bids due 10/29/2026 at 1:00 PM."
        )
        self.assertEqual(submission_deadline_details(notice),
                         ("2026-10-29", "1:00 PM"))
        self.assertEqual(submission_deadline(notice), "2026-10-29")
        self.assertTrue(explicit_closing_passed(
            notice, dt.datetime(2026, 10, 30, tzinfo=dt.timezone.utc)))
        self.assertFalse(scan.eligible(notice, "Test County",
                                      today=dt.date(2026, 10, 31)))

    def test_numbered_amendment_receipt_before_date(self):
        notice = (
            "Sealed bids will be received until 2:00 PM on Nov 19, 2026. "
            "Amendment No. 3: sealed bids will be received until 1:00 PM "
            "on Oct 29, 2026."
        )
        self.assertEqual(submission_deadline_details(notice),
                         ("2026-10-29", "1:00 PM"))

    def test_numbered_question_addendum_does_not_replace_bid_cutoff(self):
        notice = (
            "Tree trimming bids due 11/19/2026 at 3:00 PM. "
            "Addendum No. 2: questions due 10/29/2026 at 1:00 PM."
        )
        self.assertEqual(submission_deadline_details(notice),
                         ("2026-11-19", "3:00 PM"))

    def test_unmarked_dates_and_historical_scope_exclusions_unchanged(self):
        self.assertEqual(submission_deadline(
            "Bids due 11/19/2026; bids due 10/29/2026"), "2026-11-19")
        erie = "Erie PA tree & stump removal bids due 10/29/2026"
        owego = "Owego demolition rebid due 11/19/2026"
        self.assertFalse(scan.eligible(erie, "PennBid platform",
                                      today=dt.date(2026, 10, 31)))
        self.assertIsNone(scan.category(owego))


if __name__ == "__main__":
    unittest.main()
