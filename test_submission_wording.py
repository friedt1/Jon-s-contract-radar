"""Synthetic procurement wording tests; no example is a live or open bid."""
import datetime as dt
import unittest

from submission_deadlines import (
    submission_deadline, submission_deadline_details, explicit_closing_passed,
)


class SubmissionWordingTests(unittest.TestCase):
    def test_common_bid_proposal_and_quote_labels(self):
        examples = (
            ("Tree removal sealed proposals will be received by November 12, 2026 at 2:00 PM",
             "2026-11-12", "2:00 PM"),
            ("Tree trimming proposals due November 19, 2026 at 3:00 PM",
             "2026-11-19", "3:00 PM"),
            ("Brush clearing bids must be submitted by November 20, 2026 at 11:00 AM",
             "2026-11-20", "11:00 AM"),
            ("Vegetation management quotes due 11/18/2026 at 2:00 PM",
             "2026-11-18", "2:00 PM"),
            ("Tree removal RFP response deadline 11/17/2026 at 4:00 PM",
             "2026-11-17", "4:00 PM"),
            ("Storm cleanup submission deadline 11/21/2026 at 1 PM",
             "2026-11-21", "1:00 PM"),
        )
        for text, due, clock in examples:
            with self.subTest(text=text):
                self.assertEqual(submission_deadline(text), due)
                self.assertEqual(submission_deadline_details(text), (due, clock))

    def test_receipt_time_before_date_for_proposals_and_quotes(self):
        for noun in ("proposals", "quotes", "responses"):
            text = (
                f"Sealed {noun} will be received at the Purchasing Office "
                "until 1:45 P.M. on November 18, 2026."
            )
            with self.subTest(noun=noun):
                self.assertEqual(
                    submission_deadline_details(text), ("2026-11-18", "1:45 PM")
                )
                self.assertTrue(explicit_closing_passed(
                    text, dt.datetime(2026, 11, 18, 19, tzinfo=dt.timezone.utc)
                ))

    def test_question_and_meeting_deadlines_never_extend_submission(self):
        text = (
            "Questions about proposals will be received until 2:00 P.M. "
            "on November 25, 2026; "
            "Mandatory site visit deadline November 24, 2026; "
            "Sealed proposals will be received until 1:45 P.M. on November 18, 2026."
        )
        self.assertEqual(submission_deadline_details(text),
                         ("2026-11-18", "1:45 PM"))
        for text in (
            "Questions about proposals will be received until 2:00 P.M. on November 25, 2026",
            "Questions about bids must be submitted by November 25, 2026",
            "Site visit proposals due November 25, 2026",
            "Pre-bid meeting deadline November 25, 2026",
            "Tree removal bid opening on November 25, 2026 at 2 PM",
        ):
            with self.subTest(text=text):
                self.assertEqual(submission_deadline(text), "")


if __name__ == "__main__":
    unittest.main()
