"""Only successfully read individual public notices may create direct candidates.

Synthetic fixtures. These tests do not claim any live or authorized feed.
"""
import unittest
from unittest.mock import patch

import scan


SOURCE = {"name": "Test County", "url": "https://example.gov/bids", "mode": "direct_page"}
LISTING = (
    '<table><tr><td>Tree removal bid due 11/19/2026</td>'
    '<td><a href="/bid/1">Details</a></td></tr></table>'
)


class IndividualDetailGateTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(
            scan, "NOW", scan.dt.datetime(2026, 10, 28, 18, tzinfo=scan.dt.timezone.utc)
        )
        clock.start()
        self.addCleanup(clock.stop)

    def test_listing_only_does_not_publish_when_detail_fetch_fails(self):
        def fake_fetch(url, binary=False):
            if url == SOURCE["url"]:
                return LISTING, "text/html", url
            raise OSError("individual notice unavailable")

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(leads, [])
        self.assertIn("1 details checked", status)
        self.assertIn("detail errors", status)

    def test_nested_listing_does_not_publish_when_bid_detail_fails(self):
        def fake_fetch(url, binary=False):
            if url == SOURCE["url"]:
                return '<a href="/procurement">Current bids</a>', "text/html", url
            if url == "https://example.gov/procurement":
                body = ('<table><tr><td>Tree removal bid due 11/19/2026</td>'
                        '<td><a href="/bid/2">Details</a></td></tr></table>')
                return body.encode() if binary else body, "text/html", url
            raise OSError("individual notice unavailable")

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(leads, [])
        self.assertIn("detail errors", status)

    def test_relevant_fetched_notice_still_emits_unverified_candidate(self):
        def fake_fetch(url, binary=False):
            if url == SOURCE["url"]:
                return LISTING, "text/html", url
            body = "<h1>Tree removal bid due 11/19/2026</h1>"
            return body.encode() if binary else body, "text/html", url

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["url"], "https://example.gov/bid/1")
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertEqual(leads[0]["deadline"], "2026-11-19")
        self.assertIn("1 details checked", status)


if __name__ == "__main__":
    unittest.main()
