"""Offline redirect regressions: reject unsafe destinations before any GET.

These tests invoke the actual urllib redirect handler; no network requests,
provider credentials, real bid records, or live opportunities are involved.
"""
import unittest
import urllib.request as ur
from unittest.mock import patch

import scan


class RedirectPreflightTests(unittest.TestCase):
    def redirect(self, original, target):
        request = ur.Request(original)
        handler = scan.RobotsAwareRedirect()
        with patch.object(scan.robots_policy, "assert_allowed") as robots:
            try:
                result = handler.redirect_request(
                    request, None, 302, "Found", {}, target
                )
            except scan.UnsafeRedirect:
                robots.assert_not_called()
                raise
            robots.assert_called_once_with(target)
            return result

    def test_blocks_external_provider_before_robots_or_http(self):
        original = "https://example.gov/bids"
        for target in (
            "https://pennbid.bonfirehub.com/opportunities/123",
            "https://www.bidnetdirect.com/solicitations/42",
            "https://publicpurchase.com/bid/1",
            "https://example.gov.evil.test/bids",
            "https://unrelated-county.gov/bid/42",
        ):
            with self.subTest(target=target):
                with self.assertRaisesRegex(
                    scan.UnsafeRedirect, "cross-host"
                ):
                    self.redirect(original, target)

    def test_blocks_changed_bid_id_before_fetch(self):
        for original, target in (
            ("https://example.gov/bid/42", "https://example.gov/bid/43"),
            ("https://example.gov/bids.aspx?bidID=42",
             "https://example.gov/bids.aspx?bidID=43"),
            ("https://example.gov/bids.aspx?bidID=42",
             "https://example.gov/bids.aspx"),
        ):
            with self.subTest(target=target):
                with self.assertRaisesRegex(
                    scan.UnsafeRedirect, "solicitation identity"
                ):
                    self.redirect(original, target)

    def test_blocks_unsafe_redirect_targets(self):
        for original, target in (
            ("https://example.gov/bids", "http://example.gov/bids"),
            ("https://example.gov/bids", "https://user:pass@example.gov/bids"),
            ("https://example.gov/bids", "https://example.gov:8443/bids"),
            ("https://example.gov/bids", "javascript:alert(1)"),
        ):
            with self.subTest(target=target):
                with self.assertRaises(scan.UnsafeRedirect):
                    self.redirect(original, target)

    def test_allows_safe_canonical_and_same_notice_redirects(self):
        for original, target in (
            ("http://example.gov/bids", "https://www.example.gov/bids"),
            ("https://www.example.gov/bids", "https://example.gov/bids"),
            ("https://example.gov/bid/42", "https://example.gov/bid/42/"),
            ("https://example.gov/bids.aspx?bidID=42",
             "https://example.gov/bids.aspx?bidID=42&utm_source=site"),
        ):
            with self.subTest(target=target):
                self.assertEqual(self.redirect(original, target).full_url, target)


if __name__ == "__main__":
    unittest.main()
