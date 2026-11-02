"""Synthetic receipt-deadline boundary tests; no fixtures are live bids."""
import datetime as dt
import unittest

import scan
from submission_deadlines import submission_deadline_details


class ReceiptMilestoneBoundaryTests(unittest.TestCase):
    def test_questions_cutoff_cannot_be_borrowed_from_receipt_sentence(self):
        notice = (
            "Sealed bids shall be received at the County Purchasing Office. "
            "Questions must be submitted no later than 2:00 PM on "
            "November 20, 2026."
        )
        self.assertEqual(submission_deadline_details(notice), ("", ""))

    def test_site_visit_and_addendum_cutoffs_are_not_bid_cutoffs(self):
        for milestone in (
            "Mandatory site visit",
            "Addenda",
            "Clarifications",
            "Bid opening",
        ):
            notice = (
                "Bids shall be received at the Purchasing Office. "
                f"{milestone} no later than 11:00 AM on November 20, 2026."
            )
            with self.subTest(milestone=milestone):
                self.assertEqual(submission_deadline_details(notice), ("", ""))

    def test_semicolon_separates_receipt_from_questions(self):
        notice = (
            "Sealed bids will be received at the County Office; "
            "questions no later than 3:00 PM on November 20, 2026."
        )
        self.assertEqual(submission_deadline_details(notice), ("", ""))

    def test_valid_long_address_and_separate_later_questions(self):
        notice = (
            "Sealed bids shall be received at the Department of Public "
            "Works, P.O. Box 25, 477 State Route 96, Owego, NY 13827, "
            "no later than 11:00 AM local time on November 13, 2026. "
            "Questions shall be received no later than 2:00 PM on "
            "November 20, 2026."
        )
        self.assertEqual(
            submission_deadline_details(notice), ("2026-11-13", "11:00 AM")
        )

    def test_historical_erie_and_unrelated_owego_remain_negative(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bids due October 28, 2026",
            today=dt.date(2026, 11, 2),
        ))
        self.assertIsNone(scan.category(
            "Owego demolition and site restoration rebid"
        ))


if __name__ == "__main__":
    unittest.main()
