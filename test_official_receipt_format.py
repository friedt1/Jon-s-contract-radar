"""Historical/related notice formatting regressions; never publish as live bids."""
import datetime as dt
import unittest

import scan
from submission_deadlines import (
    submission_deadline, submission_deadline_details, explicit_closing_passed,
)


class OfficialReceiptFormatTests(unittest.TestCase):
    def test_chemung_historical_tree_stump_notice(self):
        # Format based on the official awarded RFB-2816 notice, not a live lead.
        text = (
            "RFB-2816 TREE AND STUMP REMOVAL (2026-2027). Status: Awarded. "
            "Sealed Bids will be received in the Chemung County - City of "
            "Elmira Purchasing Department, Third Floor, Room 308, "
            "150 Lake Street, Elmira, New York 14901, until "
            "1:45 P.M. on October 23,2025, where they will be opened at 2:00 PM."
        )
        self.assertEqual(submission_deadline_details(text),
                         ("2025-10-23", "1:45 PM"))
        self.assertFalse(scan.eligible(text, "Chemung County bids",
                         today=dt.date(2026, 10, 29)))

    def test_owego_demolition_remains_related_not_tree(self):
        # Date/time wording from Tioga County's official demolition rebid.
        text = (
            "67 Central Avenue Demolition Rebid. Bids shall be received at: "
            "Tioga County Public Works Department, 477 NY-96, Owego, NY, 13827, "
            "until 11:00 AM local time on Friday, November 13th, 2026, "
            "at which time bids will be publicly opened and read aloud."
        )
        self.assertEqual(submission_deadline_details(text),
                         ("2026-11-13", "11:00 AM"))
        self.assertIsNone(scan.category(text))

    def test_questions_about_bids_not_received_deadline(self):
        text = ("Questions about bids will be received until "
                "1:45 P.M. on October 30,2026.")
        self.assertEqual(submission_deadline(text), "")

    def test_opening_time_alone_not_submission_deadline(self):
        self.assertEqual(submission_deadline_details(
            "Tree removal bid will be publicly opened at 2:00 PM on "
            "October 23,2025"), ("", ""))

    def test_receipt_cutoff_expires_same_day_in_eastern(self):
        text = "Tree removal bids will be received until 1:00 P.M. on Oct 29,2026"
        self.assertEqual(submission_deadline_details(text),
                         ("2026-10-29", "1:00 PM"))
        self.assertFalse(explicit_closing_passed(
            text, dt.datetime(2026, 10, 29, 16, tzinfo=dt.timezone.utc)))
        self.assertTrue(explicit_closing_passed(
            text, dt.datetime(2026, 10, 29, 18, tzinfo=dt.timezone.utc)))


if __name__ == "__main__":
    unittest.main()
