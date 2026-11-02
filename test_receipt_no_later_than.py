"""Offline regression tests for long-address bid receipt cutoffs.

Synthetic examples modeled on county public-work notice formatting; none
is a live procurement opportunity. Erie/Owego are negative controls.
"""
import datetime as dt
import unittest

import scan
from submission_deadlines import (
    explicit_closing_passed, submission_deadline, submission_deadline_details,
)


class ReceiptNoLaterThanTests(unittest.TestCase):
    def test_long_address_no_later_than_with_weekday_and_ordinal(self):
        notice = (
            "Sealed bids shall be received at: Tioga County Department of "
            "Public Works, 477 State Route 96, Owego, New York 13827, "
            "Attn: Purchasing Clerk, no later than 11:00 AM local time "
            "on Friday, November 13th, 2026."
        )
        self.assertEqual(submission_deadline_details(notice),
                         ("2026-11-13", "11:00 AM"))
        self.assertEqual(submission_deadline(notice), "2026-11-13")

    def test_24_hour_cutoff_and_until_wording_remain_supported(self):
        for text, expected in (
            ("Bids will be received at the Department of Public Works, "
             "477 State Route 96, Owego, New York 13827, Purchasing "
             "Office, no later than 14:30 on November 13, 2026",
             ("2026-11-13", "2:30 PM")),
            ("Bids shall be received at the Department of Public Works, "
             "477 State Route 96, Owego, New York 13827, Purchasing "
             "Office, until 11:00 AM local time on November 13, 2026",
             ("2026-11-13", "11:00 AM")),
        ):
            with self.subTest(text=text):
                self.assertEqual(submission_deadline_details(text), expected)

    def test_questions_and_prebid_milestones_do_not_override_receipt(self):
        notice = (
            "Mandatory pre-bid inspection October 29, 2026 at 9 AM. "
            "Questions shall be received no later than November 5, 2026 "
            "at noon. Sealed bids shall be received at the Tioga County "
            "Department of Public Works, 477 State Route 96, Owego, "
            "New York 13827, no later than 11:00 AM local time on "
            "November 13, 2026."
        )
        self.assertEqual(submission_deadline_details(notice),
                         ("2026-11-13", "11:00 AM"))

    def test_same_day_expired_receipt_not_actionable(self):
        notice = (
            "Tree trimming sealed bids shall be received at the "
            "Purchasing Department, 477 State Route 96, Owego, New "
            "York 13827, no later than 11:00 AM on November 13, 2026"
        )
        before = dt.datetime(2026, 11, 13, 15, 30, tzinfo=dt.timezone.utc)
        after = dt.datetime(2026, 11, 13, 16, 30, tzinfo=dt.timezone.utc)
        self.assertFalse(explicit_closing_passed(notice, before))
        self.assertTrue(explicit_closing_passed(notice, after))
        self.assertFalse(scan.eligible(notice, today=after.date(), now=after))

    def test_negative_erie_and_owego_cases_never_live(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bids due October 28, 2026",
            today=dt.date(2026, 11, 2)))
        self.assertIsNone(scan.category(
            "Owego 67 Central Ave demolition and site restoration rebid"))


if __name__ == "__main__":
    unittest.main()
