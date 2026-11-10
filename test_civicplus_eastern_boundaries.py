"""Offline boundary tests for NY/PA CivicPlus closing times.

Synthetic fixtures only; no solicitation is added to the live feed.
"""
import datetime as dt
import unittest

from zoneinfo import ZoneInfo

from civicplus_bids import closing_passed, detail_closing_of, closing_of


class EasternDeadlineBoundaryTests(unittest.TestCase):
    def test_fall_dst_transition_uses_eastern_local_clock(self):
        # November 1, 2026 is the Eastern fall-back date.
        due = "2026-11-01"
        for utc_hour, expected in ((17, False), (18, True), (19, True)):
            with self.subTest(utc_hour=utc_hour):
                now = dt.datetime(2026, 11, 1, utc_hour, tzinfo=dt.timezone.utc)
                self.assertEqual(closing_passed(due, "1:00 PM", now), expected)

    def test_spring_dst_transition_uses_eastern_local_clock(self):
        # March 8, 2026 is the Eastern spring-forward date.
        due = "2026-03-08"
        before = dt.datetime(2026, 3, 8, 16, 59, tzinfo=dt.timezone.utc)
        at = dt.datetime(2026, 3, 8, 17, 0, tzinfo=dt.timezone.utc)
        self.assertFalse(closing_passed(due, "1:00 PM", before))
        self.assertTrue(closing_passed(due, "1:00 PM", at))

    def test_missing_same_day_time_is_not_invented(self):
        now = dt.datetime(2026, 11, 10, 23, 59, tzinfo=dt.timezone.utc)
        self.assertFalse(closing_passed("2026-11-10", "", now))
        self.assertTrue(closing_passed("2026-11-09", "", now))

    def test_publication_date_does_not_become_deadline(self):
        text = "Publication Date/Time: 11/10/2026 1:00 PM"
        self.assertEqual(closing_of(text), ("", ""))
        self.assertEqual(detail_closing_of(text), ("", ""))


if __name__ == "__main__":
    unittest.main()
