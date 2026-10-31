"""Synthetic ISO submission-time regressions; no live bid records or seeds."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan
from submission_deadlines import submission_deadline_details, explicit_closing_passed


class ISOClosingTests(unittest.TestCase):
    def test_local_iso_clock_and_seconds(self):
        self.assertEqual(
            submission_deadline_details("Tree removal bids due 2026-11-03T14:30:00"),
            ("2026-11-03", "2:30 PM"),
        )
        self.assertEqual(
            submission_deadline_details("Tree trimming submission deadline: 2026-11-03T09:15"),
            ("2026-11-03", "9:15 AM"),
        )

    def test_utc_offset_converts_to_eastern_local_day(self):
        self.assertEqual(
            submission_deadline_details("Tree removal bid due 2026-11-01T00:30:00Z"),
            ("2026-10-31", "8:30 PM"),
        )
        self.assertEqual(
            submission_deadline_details("Brush clearing bids due 2026-11-03T14:30:00Z"),
            ("2026-11-03", "9:30 AM"),
        )
        self.assertEqual(
            submission_deadline_details("Tree trimming bids due 2026-11-03T14:30:00-05:00"),
            ("2026-11-03", "2:30 PM"),
        )

    def test_same_day_expired_iso_notice_is_excluded(self):
        now = dt.datetime(2026, 10, 31, 20, 40, tzinfo=dt.timezone.utc)
        text = "Tree and stump removal bid due 2026-10-31T16:30:00-04:00"
        self.assertTrue(explicit_closing_passed(text, now))
        with patch.object(scan, "NOW", now):
            self.assertFalse(scan.eligible(text))
            found = {}
            scan.add_lead(found, "Synthetic county", text, "https://county.example/bid/44")
            self.assertEqual(found, {})

    def test_question_time_and_bid_opening_are_not_submission_cutoffs(self):
        self.assertEqual(
            submission_deadline_details(
                "Questions due 2026-11-02T08:00:00Z; "
                "tree trimming bids due 2026-11-05T15:00:00-05:00"
            ),
            ("2026-11-05", "3:00 PM"),
        )
        self.assertEqual(
            submission_deadline_details("Tree removal bid opening 2026-11-02T08:00:00Z"),
            ("", ""),
        )

    def test_malformed_iso_time_does_not_invent_closing_hour(self):
        for stamp in ("2026-11-03T25:30:00Z", "2026-11-03T14:99:00Z",
                      "2026-11-03T14:30:00+99:00"):
            with self.subTest(stamp=stamp):
                self.assertEqual(
                    submission_deadline_details("Tree removal bids due " + stamp),
                    ("2026-11-03", ""),
                )

    def test_erie_expired_and_owego_unrelated_remain_excluded(self):
        today = dt.date(2026, 10, 31)
        self.assertFalse(scan.eligible(
            "Erie tree & stump removal bid due 2025-11-03T14:00:00-05:00",
            today=today,
        ))
        self.assertFalse(scan.eligible(
            "Owego building demolition and site preparation bid due "
            "2026-11-05T15:00:00-05:00",
            today=today,
        ))


if __name__ == "__main__":
    unittest.main()
