"""Offline regression cases for explicit public-bid submission wording.

All notices below are synthetic, including historical Erie/Owego guards.
No test creates or publishes an opportunity.
"""
import datetime as dt
import unittest

import scan
from submission_deadlines import (
    explicit_closing_passed, submission_deadline, submission_deadline_details,
)


class CloseAcceptedUntilDeadlineTests(unittest.TestCase):
    def test_close_and_accepted_until_are_submission_deadlines(self):
        examples = (
            ("Sealed bids close on November 4, 2026 at 1:30 PM",
             ("2026-11-04", "1:30 PM")),
            ("Tree trimming proposals will close November 4, 2026 by 14:00",
             ("2026-11-04", "2:00 PM")),
            ("Tree removal bids accepted until 11/04/2026 at 3 PM",
             ("2026-11-04", "3:00 PM")),
            ("Vegetation management bids are accepted until 11/04/2026",
             ("2026-11-04", "")),
            ("Brush clearing bid closes on 11/04/2026 at noon",
             ("2026-11-04", "12:00 PM")),
        )
        for notice, expected in examples:
            with self.subTest(notice=notice):
                self.assertEqual(submission_deadline_details(notice), expected)
                self.assertEqual(submission_deadline(notice), expected[0])

    def test_explicit_close_clock_prevents_same_day_expired_candidate(self):
        notice = "Elmira tree removal bid. Bids close on 11/02/2026 at 1 PM"
        before = dt.datetime(2026, 11, 2, 17, 0, tzinfo=dt.timezone.utc)
        after = dt.datetime(2026, 11, 2, 19, 0, tzinfo=dt.timezone.utc)
        self.assertFalse(explicit_closing_passed(notice, before))
        self.assertTrue(explicit_closing_passed(notice, after))
        self.assertFalse(scan.eligible(
            notice, today=dt.date(2026, 11, 2), now=after))

    def test_question_and_opening_dates_are_not_bid_deadlines(self):
        for notice in (
            "Questions about bids close on 11/10/2026 at 4 PM",
            "Pre-bid meeting: proposals close for questions on 11/10/2026",
            "Tree removal bid opening on 11/10/2026 at 2 PM",
        ):
            with self.subTest(notice=notice):
                self.assertEqual(submission_deadline_details(notice), ("", ""))

    def test_amended_close_date_replaces_original_submission_cutoff(self):
        notice = (
            "Tree removal bids close on 11/02/2026 at 1 PM. "
            "Amendment: bids accepted until 11/04/2026 at 3 PM"
        )
        self.assertEqual(submission_deadline_details(notice),
                         ("2026-11-04", "3:00 PM"))

    def test_historical_erie_and_unrelated_owego_stay_excluded(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal. Bids close on 10/28/2026 at 2 PM",
            today=dt.date(2026, 11, 2)))
        self.assertIsNone(scan.category(
            "Owego building demolition and site restoration rebid"))


if __name__ == "__main__":
    unittest.main()
