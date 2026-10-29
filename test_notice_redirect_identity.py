"""Synthetic regressions: a redirect must not substitute a different solicitation.

No network requests and no live opportunity claims.
"""
import datetime as dt
import unittest
from unittest.mock import patch

import scan


BASE = "https://example.gov/bids"
SOURCE = {"name": "Test County", "url": BASE, "mode": "direct_page"}


class NoticeRedirectIdentityTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(scan, "NOW", dt.datetime(2026, 10, 28, 18, tzinfo=dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def test_permits_canonicalization_without_changing_notice(self):
        self.assertTrue(scan.redirect_preserves_notice(
            "https://example.gov/bid/42", "https://example.gov/bid/42/?utm_source=county"))
        self.assertTrue(scan.redirect_preserves_notice(
            "https://example.gov/Bids.aspx?bidID=42", "https://example.gov/Bids.aspx?bidID=42&view=full"))
        self.assertTrue(scan.redirect_preserves_notice(
            "https://example.gov/document?id=42", "https://example.gov/document?id=42&format=html"))

    def test_rejects_substitution_or_missing_identity(self):
        cases = [
            ("https://example.gov/bid/42", "https://example.gov/bid/43"),
            ("https://example.gov/bid/42", "https://example.gov/bids"),
            ("https://example.gov/Bids.aspx?bidID=42", "https://example.gov/Bids.aspx?bidID=43"),
            ("https://example.gov/Bids.aspx?bidID=42", "https://example.gov/Bids.aspx"),
            ("https://example.gov/document?id=42", "https://example.gov/document?id=43"),
            ("https://example.gov/document?id=42", "https://example.gov/document"),
            ("https://example.gov/bid/42", "http://example.gov/bid/42"),
            ("https://example.gov/bid/42", "https://other.example/bid/42"),
        ]
        for original, redirected in cases:
            with self.subTest(redirected=redirected):
                self.assertFalse(scan.redirect_preserves_notice(original, redirected))

    def test_wrong_notice_redirect_cannot_enter_active_feed(self):
        listing = '<a href="/bid/42">Tree removal bid due 11/19/2026</a>'
        other_notice = '<h1>Tree removal bid due 11/19/2026</h1>'
        calls = []

        def fake_fetch(url, binary=False):
            calls.append(url)
            if url == BASE:
                return listing, "text/html", url
            return other_notice.encode(), "text/html", "https://example.gov/bid/43"

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(leads, [])
        self.assertEqual(calls, [BASE, "https://example.gov/bid/42"])
        self.assertIn("1 details checked", status)

    def test_same_notice_redirect_remains_unverified_candidate(self):
        listing = '<a href="/bid/42">Tree removal bid due 11/19/2026</a>'
        body = '<h1>Tree removal bid due 11/19/2026</h1>'

        def fake_fetch(url, binary=False):
            if url == BASE:
                return listing, "text/html", url
            return body.encode(), "text/html", "https://example.gov/bid/42/"

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, _ = scan.scan_direct(SOURCE)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["status"], "unverified")


if __name__ == "__main__":
    unittest.main()
