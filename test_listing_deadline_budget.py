"""Synthetic deadline-aware detail-budget regressions; no live bids or network."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan

BASE = "https://example.gov/bids"
SOURCE = {"name": "Test County", "url": BASE, "mode": "direct_page"}
NOW = dt.datetime(2026, 10, 30, 18, tzinfo=dt.timezone.utc)
CURRENT = "https://example.gov/bid/999"


def listing(old_label, current_label):
    rows = [
        '<tr><td>%s</td><td><a href="/bid/%s">Details</a></td></tr>'
        % (old_label, n)
        for n in range(scan.MAX_DETAIL)
    ]
    rows.append('<tr><td>%s</td><td><a href="/bid/999">Details</a></td></tr>'
                % current_label)
    return "<table>" + "".join(rows) + "</table>"


class ListingDeadlineBudgetTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(scan, "NOW", NOW)
        clock.start()
        self.addCleanup(clock.stop)

    def run_listing(self, old_label, current_label, current_detail):
        requested = []
        page = listing(old_label, current_label)

        def fake_fetch(url, binary=False):
            requested.append(url)
            if url == BASE:
                body = page
            elif url == CURRENT:
                body = current_detail
            else:
                body = "<h1>Historical tree removal bid due 09/01/2026</h1>"
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(SOURCE)
        return leads, status, requested

    def test_future_tree_bid_beats_expired_open_archive_at_cap(self):
        leads, status, requested = self.run_listing(
            "Tree removal bid — Status: Open — bids due 09/01/2026",
            "Tree removal bid — bids due 11/19/2026",
            "<h1>Tree removal bid due 11/19/2026</h1>",
        )
        self.assertEqual(requested[1], CURRENT)
        self.assertEqual(len(requested), scan.MAX_DETAIL + 1)
        self.assertEqual([item["url"] for item in leads], [CURRENT])
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("1 detail candidates deferred at request budget", status)

    def test_unknown_deadline_beats_explicit_closed_archive(self):
        leads, _, requested = self.run_listing(
            "Tree removal bid — Status: Closed",
            "Tree removal bid — submission deadline to be confirmed",
            "<h1>Tree removal bid</h1><p>Bid Number: 999</p>",
        )
        self.assertEqual(requested[1], CURRENT)
        self.assertEqual([item["url"] for item in leads], [CURRENT])
        self.assertEqual(leads[0]["deadline"], "")
        self.assertEqual(leads[0]["status"], "unverified")

    def test_questions_date_is_not_a_submission_deadline(self):
        self.assertEqual(scan.listing_deadline_priority(
            "Tree removal bid; Questions due 12/01/2026", NOW), 0)
        self.assertEqual(scan.listing_deadline_priority(
            "Tree removal bid; bids due 11/19/2026", NOW), 8)
        self.assertEqual(scan.listing_deadline_priority(
            "Tree removal bid; bids due 09/01/2026", NOW), -10)

    def test_same_day_elapsed_submission_time_is_deprioritized(self):
        self.assertEqual(scan.listing_deadline_priority(
            "Tree removal bid; bids due 10/30/2026 at 1:00 PM", NOW), -10)
        self.assertEqual(scan.listing_deadline_priority(
            "Tree removal bid; bids due 10/30/2026 at 4:00 PM", NOW), 8)

    def test_expired_listing_is_not_suppressed_if_detail_amends_date(self):
        # Prioritization is never a hard eligibility gate: a later amendment
        # may have moved the original expired submission deadline.
        self.assertEqual(scan.listing_deadline_priority(
            "Tree removal bid; bids due 09/01/2026", NOW), -10)
        leads, status, requested = self.run_listing(
            "Tree removal bid; bids due 09/01/2026",
            "Tree removal bid; bids due 11/19/2026",
            "<h1>Tree removal bid due 11/19/2026</h1>",
        )
        self.assertTrue(any("/bid/" in url and url != CURRENT for url in requested))
        self.assertEqual([item["url"] for item in leads], [CURRENT])
        self.assertIn("deferred at request budget", status)


if __name__ == "__main__":
    unittest.main()
