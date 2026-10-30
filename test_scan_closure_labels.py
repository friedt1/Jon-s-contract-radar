"""Synthetic scanner closure regressions; none are actual live solicitations."""
import datetime as dt
import unittest

import scan


class ScannerClosureLabelTests(unittest.TestCase):
    TODAY = dt.date(2026, 10, 29)

    def test_question_only_status_does_not_close_bidding(self):
        for label in (
            "Status: Closed for questions",
            "Status: Closed - for questions",
            "Status: Closed: Q&A",
            "Status: Closed (questions)",
            "Status is Closed – to inquiries",
            "Status: Closed for RFIs",
            "Status: Closed for addenda",
        ):
            with self.subTest(label=label):
                self.assertFalse(scan.closed(label))
                self.assertTrue(scan.eligible(
                    "Tree and stump removal bid. " + label,
                    source="Chemung County bids", today=self.TODAY))

    def test_actual_submission_closure_still_excludes(self):
        for label in (
            "Status: Closed",
            "Status: Closed - no longer accepting bids",
            "Bids are closed",
            "Bid is closed",
            "Closed for bids",
            "Status: Closed for questions; bids are closed",
            "Status: Awarded",
        ):
            with self.subTest(label=label):
                self.assertTrue(scan.closed(label))
                self.assertFalse(scan.eligible(
                    "Tree removal bid. " + label,
                    source="Chemung County bids", today=self.TODAY))

    def test_erie_expired_and_owego_demolition_are_not_promoted(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid. Bids due October 28, 2026.",
            today=self.TODAY))
        self.assertFalse(scan.eligible(
            "Owego demolition rebid. Building demolition and site restoration.",
            today=self.TODAY))


if __name__ == "__main__":
    unittest.main()
