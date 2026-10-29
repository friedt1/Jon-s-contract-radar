"""Synthetic fixtures only: no example is a real or open procurement notice."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan
from submission_deadlines import submission_deadline_details, explicit_closing_passed


class ExplicitClosingTimeTests(unittest.TestCase):
    def setUp(self):
        self.clock = patch.object(scan, "NOW", dt.datetime(2026, 10, 29, 18, tzinfo=dt.timezone.utc))
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def test_after_date_and_before_date_times(self):
        examples = (
            "Bids due 10/29/2026 at 1:00 PM",
            "Closing Date/Time: 10/29/2026 1:00 PM",
            "Submission deadline October 29, 2026, 1 PM",
            "Bids due at 1:00 PM on Oct 29, 2026",
        )
        for example in examples:
            with self.subTest(example=example):
                self.assertEqual(submission_deadline_details(example), ("2026-10-29", "1:00 PM"))
                self.assertTrue(explicit_closing_passed(example, scan.NOW))

    def test_question_and_walkthrough_times_do_not_close_bid(self):
        example = ("Questions due 10/29/2026 at 9:00 AM; "
                   "Site visit deadline 10/29/2026 at 10:00 AM; "
                   "Bids due 10/29/2026 at 4:00 PM")
        self.assertEqual(submission_deadline_details(example), ("2026-10-29", "4:00 PM"))
        self.assertFalse(explicit_closing_passed(example, scan.NOW))
        self.assertEqual(submission_deadline_details("Questions due 10/29/2026 at 9:00 AM"), ("", ""))

    def test_date_only_same_day_is_not_expired_by_inference(self):
        self.assertEqual(submission_deadline_details("Tree removal bids due 10/29/2026"), ("2026-10-29", ""))
        self.assertFalse(explicit_closing_passed("Tree removal bids due 10/29/2026", scan.NOW))

    def test_revised_submission_date_takes_precedence(self):
        example = ("Bids due 10/29/2026 at 1:00 PM. "
                   "Amended: bids due 11/02/2026 at 10:00 AM.")
        self.assertEqual(submission_deadline_details(example), ("2026-11-02", "10:00 AM"))
        self.assertFalse(explicit_closing_passed(example, scan.NOW))

    def test_generic_html_bid_expired_at_explicit_local_time(self):
        src = {"name": "Test County", "url": "https://example.org/bids", "mode": "direct_page"}
        listing = '<a href="/bid/1">Tree removal bid</a>'
        def fake(url, binary=False):
            value = '<h1>Tree removal bid</h1><p>Bids due 10/29/2026 at 1:00 PM</p>' if binary else listing
            return (value.encode() if binary else value, "text/html", url)
        with patch.object(scan, "fetch", side_effect=fake):
            leads, status = scan.scan_direct(src)
        self.assertEqual(leads, [])
        self.assertIn("1 details checked", status)

    def test_generic_html_future_time_is_preserved_as_unverified(self):
        src = {"name": "Test County", "url": "https://example.org/bids", "mode": "direct_page"}
        listing = '<a href="/bid/1">Tree removal bid</a>'
        def fake(url, binary=False):
            value = '<h1>Tree removal bid</h1><p>Bids due 10/29/2026 at 4:00 PM</p>' if binary else listing
            return (value.encode() if binary else value, "text/html", url)
        with patch.object(scan, "fetch", side_effect=fake):
            leads, _ = scan.scan_direct(src)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["deadline_time"], "4:00 PM")
        self.assertEqual(leads[0]["deadline"], "2026-10-29")
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("assumption", leads[0]["deadline_timezone"])

    def test_pdf_bid_expired_at_explicit_local_time(self):
        src = {"name": "Test County", "url": "https://example.org/bids", "mode": "direct_page"}
        def fake(url, binary=False):
            if binary:
                return b"%PDF fake", "application/pdf", url
            return '<a href="/bids/tree-bid.pdf">Tree removal bid</a>', "text/html", url
        with patch.object(scan, "fetch", side_effect=fake), patch.object(
                scan, "pdf_text", return_value="Tree removal bid. Bids due 10/29/2026 at 1:00 PM"):
            leads, _ = scan.scan_direct(src)
        self.assertEqual(leads, [])


if __name__ == "__main__":
    unittest.main()
