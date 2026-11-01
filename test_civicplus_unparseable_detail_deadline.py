"""Synthetic CivicPlus deadline regressions; never publish test notices as live bids."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan

BASE = "https://county.example/Bids.aspx"
DETAIL = BASE + "?bidID=91"
SOURCE = {"name": "Chemung County bids", "url": BASE, "mode": "direct_page"}
NOW = dt.datetime(2026, 10, 30, 20, tzinfo=dt.timezone.utc)
LISTING = (
    '<article><a href="/Bids.aspx?bidID=91">Tree removal bid</a>'
    '<p>Status: Closes: Open 11/19/2026 2:00 PM</p></article>'
)


def run_detail(detail):
    def fake_fetch(url, binary=False):
        body = LISTING if url == BASE else detail if url == DETAIL else None
        if body is None:
            raise AssertionError("Unexpected fetch " + url)
        return (body.encode() if binary else body, "text/html", url)

    with patch.object(scan, "NOW", NOW), patch.object(scan, "fetch", side_effect=fake_fetch):
        return scan.scan_direct(SOURCE)


class CivicPlusDetailDeadlineFallbackTests(unittest.TestCase):
    def test_unparseable_detail_cutoff_cannot_borrow_future_listing_deadline(self):
        detail = (
            "<p>Bid Title: Tree removal bid</p><p>Status: Open</p>"
            "<p>Description: Tree removal along county roads</p>"
            "<p>Closing Date/Time: Pending amendment</p>"
        )
        leads, diagnostic = run_detail(detail)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["deadline"], "")
        self.assertEqual(leads[0]["deadline_time"], "")
        self.assertEqual(leads[0]["deadline_source"], "unknown")
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("1 individual bid details fetched", diagnostic)

    def test_missing_detail_closing_field_allows_explicit_listing_fallback(self):
        detail = (
            "<p>Bid Title: Tree removal bid</p><p>Status: Open</p>"
            "<p>Description: Tree removal along county roads</p>"
        )
        leads, _ = run_detail(detail)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["deadline"], "2026-11-19")
        self.assertEqual(leads[0]["deadline_time"], "2:00 PM")
        self.assertEqual(leads[0]["deadline_source"], "listing")

    def test_expired_detail_cutoff_overrides_future_listing(self):
        detail = (
            "<p>Bid Title: Tree removal bid</p><p>Status: Open</p>"
            "<p>Description: Tree removal along county roads</p>"
            "<p>Closing Date/Time: 10/22/2026 2:00 PM</p>"
        )
        leads, diagnostic = run_detail(detail)
        self.assertEqual(leads, [])
        self.assertIn("1 expired", diagnostic)

    def test_historical_erie_and_unrelated_owego_not_live(self):
        self.assertFalse(scan.eligible(
            "Erie PA tree and stump removal bids due 10/29/2026",
            "PennBid platform", today=dt.date(2026, 10, 30)))
        self.assertIsNone(scan.category(
            "Owego NY building demolition and site restoration rebid"))


if __name__ == "__main__":
    unittest.main()
