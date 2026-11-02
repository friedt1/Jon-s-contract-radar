"""Nested publisher result tabs must not be fetched or advertised as live bids.

All HTML fixtures and bid URLs are synthetic; none are live opportunities.
"""
import datetime as dt
import unittest
from unittest.mock import patch

import scan


BASE = "https://example.gov/bids"
INDEX = "https://example.gov/procurement"
RESULT = "https://example.gov/media/opaque-result.pdf"
NOTICE = "https://example.gov/bid/123"
SOURCE = {"name": "Test County", "url": BASE, "mode": "direct_page"}


class NestedResultLinksTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(scan, "NOW", dt.datetime(
            2026, 11, 2, 18, tzinfo=dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def scan_fixture(self, include_notice=False):
        nested = (
            "<h1>Tree removal procurement</h1>"
            '<a href="/media/opaque-result.pdf">Tree Removal 2026 Bid Results</a>'
        )
        if include_notice:
            nested += '<a href="/bid/123">Tree removal bid due 11/19/2026</a>'
        pages = {
            BASE: '<a href="/procurement">Current bids</a>',
            INDEX: nested,
            NOTICE: "<h1>Tree removal bid due November 19, 2026</h1>",
        }
        fetched = []

        def fake_fetch(url, binary=False):
            fetched.append(url)
            if url == RESULT:
                raise AssertionError("Historical bid results PDF was fetched")
            if url not in pages:
                raise AssertionError("Unexpected request: " + url)
            body = pages[url]
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(SOURCE)
        return leads, status, fetched

    def test_results_only_nested_index_is_not_a_live_tree_notice(self):
        leads, status, fetched = self.scan_fixture()
        self.assertEqual(leads, [])
        self.assertEqual(fetched, [BASE, INDEX])
        self.assertIn("1 result/award links excluded", status)
        self.assertIn("1 nested listing pages excluded as notices", status)

    def test_results_skip_preserves_individual_tree_bid(self):
        leads, status, fetched = self.scan_fixture(include_notice=True)
        self.assertEqual(fetched, [BASE, INDEX, NOTICE])
        self.assertEqual([lead["url"] for lead in leads], [NOTICE])
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("1 result/award links excluded", status)


if __name__ == "__main__":
    unittest.main()
