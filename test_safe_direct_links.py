"""Regression tests for bounded, permission-aware direct bid detail URLs.

All notices are synthetic. No live source is fetched by these tests.
"""
import unittest
from unittest.mock import patch

import scan

BASE = "https://example.gov/bids"
SOURCE = {"name": "Test County", "url": BASE, "mode": "direct_page"}


class SafeDirectLinksTests(unittest.TestCase):
    def test_accepts_valid_relative_same_host_and_explicit_platform_links(self):
        self.assertEqual(scan.safe_detail_url(BASE, "/bid/123"),
                         "https://example.gov/bid/123")
        self.assertEqual(scan.safe_detail_url(BASE, "?page=2"),
                         "https://example.gov/bids?page=2")
        self.assertEqual(scan.safe_detail_url(BASE, "https://pennbid.net/bid/123"),
                         "https://pennbid.net/bid/123")

    def test_rejects_malformed_untrusted_or_credentialed_links(self):
        invalid = [
            "", " ", "/bid/1\n", "/bid/1\\extra", "/bid/%0aevil",
            "/bid/%7f", "javascript:alert(1)", "mailto:someone@example.com",
            "https://unrelated.example/bid/1",
            "https://user:password@example.gov/bid/1",
            "https://example.gov:9999/bid/1",
            "http://[broken/bid/1",
        ]
        for href in invalid:
            with self.subTest(href=href):
                self.assertEqual(scan.safe_detail_url(BASE, href), "")

    def test_bad_link_does_not_consume_detail_budget_or_block_valid_bid(self):
        listing = ('<a href="http://[broken/bid">Tree removal bid</a>'
                   '<a href="/bid/123">Tree removal bid due 11/19/2026</a>')
        detail = "<h1>Tree removal bid due 11/19/2026</h1>"
        visited = []

        def fake_fetch(url, binary=False):
            visited.append(url)
            body = listing if url == BASE else detail
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(visited, [BASE, "https://example.gov/bid/123"])
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["url"], "https://example.gov/bid/123")
        self.assertIn("1 details checked", status)
        self.assertEqual(leads[0]["status"], "unverified")


if __name__ == "__main__":
    unittest.main()
