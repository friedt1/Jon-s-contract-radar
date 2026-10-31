"""Synthetic inline-revision deadline regressions; never publish these as bids."""
import datetime as dt
import unittest

import scan
from submission_deadlines import submission_deadline_details


class InlineRevisedSubmissionTests(unittest.TestCase):
    NOW = dt.datetime(2026, 10, 31, 18, tzinfo=dt.timezone.utc)

    def test_revised_field_can_move_deadline_earlier(self):
        text = ("Elmira tree removal bid. Bids due November 6, 2026 at 2 PM. "
                "Bid submission deadline (revised): October 30, 2026 at 1 PM")
        self.assertEqual(submission_deadline_details(text),
                         ("2026-10-30", "1:00 PM"))
        self.assertFalse(scan.eligible(text, today=dt.date(2026, 10, 31),
                                       now=self.NOW))

    def test_amended_field_can_move_deadline_later(self):
        text = ("Elmira tree trimming bid. Bids due October 30, 2026 at 1 PM. "
                "Bid submission deadline: (amended) November 6, 2026 at 3 PM")
        self.assertEqual(submission_deadline_details(text),
                         ("2026-11-06", "3:00 PM"))
        self.assertTrue(scan.eligible(text, today=dt.date(2026, 10, 31),
                                      now=self.NOW))

    def test_revised_date_only_does_not_inherit_old_clock(self):
        text = ("Elmira tree removal bid. Bids due November 6, 2026 at 2 PM. "
                "Closing date (updated): October 30, 2026")
        self.assertEqual(submission_deadline_details(text),
                         ("2026-10-30", ""))

    def test_revised_question_deadline_is_not_submission(self):
        text = ("Elmira vegetation management bid. Bids due November 6, 2026 at 2 PM. "
                "Questions deadline (revised): October 30, 2026 at 1 PM")
        self.assertEqual(submission_deadline_details(text),
                         ("2026-11-06", "2:00 PM"))

    def test_unmarked_earlier_date_does_not_override_latest(self):
        text = ("Elmira tree removal bid. Bids due November 6, 2026 at 2 PM. "
                "Bid submission deadline: October 30, 2026 at 1 PM")
        self.assertEqual(submission_deadline_details(text),
                         ("2026-11-06", "2:00 PM"))

    def test_erie_expired_and_owego_demolition_stay_excluded(self):
        self.assertFalse(scan.eligible(
            "Erie PA tree & stump removal bid. Bids due October 29, 2026",
            today=dt.date(2026, 10, 31), now=self.NOW))
        self.assertFalse(scan.eligible(
            "Owego demolition rebid. Building demolition and site restoration. "
            "Bids due November 13, 2026",
            today=dt.date(2026, 10, 31), now=self.NOW))


if __name__ == "__main__":
    unittest.main()
