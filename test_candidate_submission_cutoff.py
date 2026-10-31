"""Synthetic regression fixtures only; never seed these as live contracts.

The generic eligibility gate is shared by direct pages, local RSS and news RSS.
A same-day cutoff must not be bypassed by a second discovery channel.
"""
import datetime as dt
import unittest
from unittest.mock import patch

import scan


class CandidateSubmissionCutoffTests(unittest.TestCase):
    NOW = dt.datetime(2026, 10, 31, 18, 0, tzinfo=dt.timezone.utc)
    TODAY = dt.date(2026, 10, 31)

    def test_expired_same_day_clock_is_rejected_at_generic_gate(self):
        text = "Elmira tree removal bid. Bids due 10/31/2026 at 1:00 PM"
        self.assertFalse(scan.eligible(text, today=self.TODAY, now=self.NOW))

    def test_future_same_day_clock_is_unverified_not_expired(self):
        text = "Elmira tree removal bid. Bids due 10/31/2026 at 4:00 PM"
        self.assertTrue(scan.eligible(text, today=self.TODAY, now=self.NOW))

    def test_exact_closing_minute_is_not_open(self):
        clock = dt.datetime(2026, 10, 31, 17, 0, tzinfo=dt.timezone.utc)
        text = "Elmira tree trimming bid. Bids due 10/31/2026 at 1 PM"
        self.assertFalse(scan.eligible(text, today=self.TODAY, now=clock))

    def test_date_only_does_not_invent_an_hour(self):
        text = "Elmira vegetation management bid. Bids due 10/31/2026"
        self.assertTrue(scan.eligible(text, today=self.TODAY, now=self.NOW))

    def test_questions_clock_does_not_expire_submission(self):
        text = ("Elmira tree removal bid. Questions due 10/31/2026 at 9 AM. "
                "Bids due 10/31/2026 at 4 PM")
        self.assertTrue(scan.eligible(text, today=self.TODAY, now=self.NOW))

    def test_revised_deadline_supersedes_expired_original(self):
        text = ("Elmira tree removal bid. Bids due 10/31/2026 at 1 PM. "
                "Amendment: bids due 11/02/2026 at 10 AM")
        self.assertTrue(scan.eligible(text, today=self.TODAY, now=self.NOW))

    def test_explicit_historical_date_does_not_use_unrelated_live_clock(self):
        text = "Elmira tree removal bid. Bids due 10/29/2026 at 1 PM"
        self.assertTrue(scan.eligible(
            text, today=dt.date(2026, 10, 29), now=self.NOW))

    def test_local_rss_cannot_republish_elapsed_cutoff(self):
        source = {"name": "Elmira Next local bids", "mode": "discovery_pending"}
        records = [
            {"title": "Elmira tree removal bid",
             "description": "Bids due 10/31/2026 at 1 PM",
             "url": "https://example.gov/bids/expired",
             "published": "2026-10-30"},
            {"title": "Elmira tree trimming bid",
             "description": "Bids due 10/31/2026 at 4 PM",
             "url": "https://example.gov/bids/future",
             "published": "2026-10-30"},
            {"title": "Elmira vegetation management bid",
             "description": "Bids due 10/31/2026",
             "url": "https://example.gov/bids/date-only",
             "published": "2026-10-30"},
        ]
        with patch.object(scan, "NOW", self.NOW), patch.object(
                scan, "fetch", return_value=("<rss/>", "application/rss+xml",
                                            "https://example.gov/feed")), patch.object(
                scan.local_bid_rss, "parse", return_value=records), patch.object(
                scan, "scan_news", return_value=[]):
            _, status, leads = scan.run(source)
        self.assertEqual({lead["url"] for lead in leads}, {
            "https://example.gov/bids/future",
            "https://example.gov/bids/date-only",
        })
        self.assertTrue(all(lead["status"] == "unverified" for lead in leads))
        self.assertIn("2 unverified tree-service candidates", status)

    def test_erie_expiration_and_owego_demolition_remain_excluded(self):
        self.assertFalse(scan.eligible(
            "Erie PA tree & stump removal bid. Bids due 10/29/2026",
            today=self.TODAY, now=self.NOW))
        self.assertFalse(scan.eligible(
            "Owego demolition rebid. Building demolition and site restoration. "
            "Bids due 11/13/2026", today=self.TODAY, now=self.NOW))


if __name__ == "__main__":
    unittest.main()
