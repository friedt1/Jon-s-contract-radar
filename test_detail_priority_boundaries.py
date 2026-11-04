"""Offline regression boundaries for bounded individual-detail request ordering.

Synthetic fixtures only; never populate a live bid feed.
"""
import datetime as dt
import unittest
from zoneinfo import ZoneInfo

import scan


NY = ZoneInfo("America/New_York")


class DetailPriorityBoundaryTests(unittest.TestCase):
    def test_future_submission_beats_undated_notice(self):
        now = dt.datetime(2026, 11, 4, 10, 0, tzinfo=NY)
        self.assertGreater(
            scan.listing_deadline_priority("Tree removal bid due November 12, 2026", now),
            scan.listing_deadline_priority("Tree removal bid; deadline not listed", now),
        )

    def test_expired_open_label_does_not_get_future_priority(self):
        now = dt.datetime(2026, 11, 4, 10, 0, tzinfo=NY)
        self.assertLess(
            scan.listing_deadline_priority("OPEN tree removal bid due October 22, 2026", now),
            scan.listing_deadline_priority("Tree removal bid; deadline not listed", now),
        )

    def test_question_period_closure_does_not_deprioritize_live_bid(self):
        now = dt.datetime(2026, 11, 4, 10, 0, tzinfo=NY)
        self.assertGreater(
            scan.listing_deadline_priority(
                "Tree removal bid due November 12, 2026; questions closed", now
            ), 0
        )

    def test_awarded_notice_deprioritized_despite_future_date(self):
        now = dt.datetime(2026, 11, 4, 10, 0, tzinfo=NY)
        self.assertLess(
            scan.listing_deadline_priority(
                "Tree removal bid status: awarded; due November 12, 2026", now
            ), 0
        )

    def test_priority_is_only_ordering_not_open_verification(self):
        now = dt.datetime(2026, 11, 4, 10, 0, tzinfo=NY)
        title = "Tree removal bid due November 12, 2026"
        self.assertGreater(scan.listing_deadline_priority(title, now), 0)
        # An explicit award must still override a future date.
        self.assertFalse(scan.eligible(title + "; status: awarded", now=now))


if __name__ == "__main__":
    unittest.main()
