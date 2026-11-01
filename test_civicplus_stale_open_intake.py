"""Synthetic CivicPlus stale-open badge regressions; never seed live bids."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan

BASE = "https://county.example/Bids.aspx"
DETAIL = BASE + "?bidID=91"
SOURCE = {"name": "Chemung County bids", "url": BASE, "mode": "direct_page"}
NOW = dt.datetime(2026, 10, 31, 16, tzinfo=dt.timezone.utc)
LISTING = (
    '<article><a href="/Bids.aspx?bidID=91">Tree removal bid</a>'
    '<p>Status: Closes: Open 11/19/2026 2:00 PM</p></article>'
)


def run_notice(extra):
    detail = (
        "<p>Bid Title: Tree removal bid</p><p>Status: Open</p>"
        "<p>Description: Remove hazardous trees along county roads.</p>"
        "<p>Closing Date/Time: 11/19/2026 2:00 PM</p>"
        "<p>" + extra + "</p>"
    )
    requested = []

    def fake_fetch(url, binary=False):
        requested.append(url)
        if url == BASE:
            body = LISTING
        elif url == DETAIL:
            body = detail
        else:
            raise AssertionError("Unexpected fetch " + url)
        return (body.encode() if binary else body, "text/html", url)

    with patch.object(scan, "NOW", NOW), patch.object(
        scan, "fetch", side_effect=fake_fetch
    ):
        leads, diagnostic = scan.scan_direct(SOURCE)
    return leads, diagnostic, requested


class CivicPlusStaleOpenBadgeTests(unittest.TestCase):
    def test_stale_open_badge_cannot_override_closed_bid_intake(self):
        for notice in (
            "Bids are no longer accepted for this solicitation.",
            "The bid was awarded to another vendor.",
            "Status: Closed",
        ):
            with self.subTest(notice=notice):
                leads, diagnostic, requested = run_notice(notice)
                self.assertEqual(leads, [])
                self.assertEqual(requested, [BASE, DETAIL])
                self.assertIn("1 individual bid details fetched", diagnostic)
                self.assertIn("1 closed", diagnostic)

    def test_questions_closed_does_not_close_bid_submission(self):
        leads, diagnostic, _ = run_notice(
            "Questions closed for this RFP. Bid submissions remain open."
        )
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertEqual(leads[0]["deadline"], "2026-11-19")
        self.assertIn("0 closed", diagnostic)

    def test_future_conditional_cutoff_does_not_close_notice(self):
        leads, diagnostic, _ = run_notice(
            "Bids will not be accepted after November 19, 2026."
        )
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("0 closed", diagnostic)

    def test_erie_and_owego_remain_regression_only(self):
        self.assertFalse(scan.eligible(
            "Erie PA tree and stump removal bids due October 29, 2026",
            today=dt.date(2026, 10, 31)
        ))
        self.assertIsNone(scan.category(
            "Owego building demolition and site restoration rebid"
        ))


if __name__ == "__main__":
    unittest.main()
