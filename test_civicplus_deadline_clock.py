"""Synthetic CivicPlus deadline regression cases; no live bid assertions."""
import datetime as dt
import unittest
from unittest.mock import patch

import civicplus_bids
import scan

BASE = "https://example.gov/Bids.aspx"
SOURCE = {"name": "Chemung County bids", "url": BASE, "mode": "direct_page"}
LISTING = ('<article><a href="/Bids.aspx?bidID=19">Tree removal bid</a>'
           '<p>Status: Open</p><p>Closes: 10/29/2026 1:30 PM</p></article>')
DETAIL = ('<p>Bid Number: RFB-19</p><p>Bid Title: Tree removal bid</p>'
          '<p>Status: Open</p><p>Description: Tree and stump removal along road.</p>'
          '<p>Closing Date/Time: 10/29/2026 1:30 PM</p>')


class SameDayDeadlineTests(unittest.TestCase):
    def scan_at(self, clock):
        def fetch(url, binary=False):
            body = DETAIL if binary else LISTING
            return (body.encode() if binary else body, "text/html", url)
        with patch.object(scan, "NOW", clock), patch.object(scan, "fetch", side_effect=fetch):
            return scan.scan_direct(SOURCE)

    def test_after_same_day_cutoff_is_expired(self):
        leads, status = self.scan_at(dt.datetime(2026, 10, 29, 19, 0, tzinfo=dt.timezone.utc))
        self.assertEqual(leads, [])
        self.assertIn("1 expired", status)

    def test_before_same_day_cutoff_is_still_unverified_candidate(self):
        leads, status = self.scan_at(dt.datetime(2026, 10, 29, 16, 0, tzinfo=dt.timezone.utc))
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertEqual(leads[0]["deadline"], "2026-10-29")
        self.assertEqual(leads[0]["deadline_time"], "1:30 PM")

    def test_exact_cutoff_is_expired(self):
        now = dt.datetime(2026, 10, 29, 17, 30, tzinfo=dt.timezone.utc)
        self.assertTrue(civicplus_bids.closing_passed("2026-10-29", "1:30 PM", now))

    def test_winter_dst_offset(self):
        before = dt.datetime(2026, 12, 1, 18, 0, tzinfo=dt.timezone.utc)
        after = dt.datetime(2026, 12, 1, 19, 0, tzinfo=dt.timezone.utc)
        self.assertFalse(civicplus_bids.closing_passed("2026-12-01", "1:30 PM", before))
        self.assertTrue(civicplus_bids.closing_passed("2026-12-01", "1:30 PM", after))

    def test_missing_or_bad_time_does_not_invent_cutoff(self):
        now = dt.datetime(2026, 10, 29, 23, 0, tzinfo=dt.timezone.utc)
        self.assertFalse(civicplus_bids.closing_passed("2026-10-29", "", now))
        self.assertFalse(civicplus_bids.closing_passed("2026-10-29", "TBD", now))
        self.assertTrue(civicplus_bids.closing_passed("2026-10-28", "", now))


if __name__ == "__main__":
    unittest.main()
