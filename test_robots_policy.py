"""Offline robots-policy tests; no live source is assumed crawlable."""
import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

import robots_policy
import scan


class RobotsPolicyTests(unittest.TestCase):
    def setUp(self):
        robots_policy._CACHE.clear()

    def test_specific_disallow_and_allowed_path(self):
        with patch.object(robots_policy, "urlopen", return_value=io.BytesIO(
                b"User-agent: JonsContractRadar\nDisallow: /Bids.aspx\nAllow: /public/\n")):
            allowed, reason = robots_policy.allowed("https://agency.example/Bids.aspx")
            self.assertFalse(allowed)
            self.assertIn("disallows", reason)
            self.assertTrue(robots_policy.allowed("https://agency.example/public/notice")[0])

    def test_missing_robots_is_allowed_but_403_is_not(self):
        for status, expected in ((404, True), (410, True), (403, False)):
            with self.subTest(status=status):
                robots_policy._CACHE.clear()
                error = HTTPError("https://agency.example/robots.txt", status, "test", {}, None)
                with patch.object(robots_policy, "urlopen", side_effect=error):
                    self.assertEqual(robots_policy.allowed("https://agency.example/Bids.aspx")[0], expected)

    def test_network_failure_fails_closed(self):
        with patch.object(robots_policy, "urlopen", side_effect=URLError("timeout")):
            ok, reason = robots_policy.allowed("https://agency.example/Bids.aspx")
            self.assertFalse(ok)
            self.assertIn("unavailable", reason)

    def test_robots_policy_is_cached_per_origin(self):
        with patch.object(robots_policy, "urlopen", return_value=io.BytesIO(
                b"User-agent: *\nDisallow: /private\n")) as download:
            self.assertTrue(robots_policy.allowed("https://agency.example/Bids.aspx")[0])
            self.assertFalse(robots_policy.allowed("https://agency.example/private")[0])
            self.assertEqual(download.call_count, 1)

    def test_fetch_never_opens_disallowed_url(self):
        with patch.object(robots_policy, "assert_allowed",
                          side_effect=robots_policy.RobotsDenied("blocked")):
            with patch.object(scan.ur, "build_opener") as opener:
                with self.assertRaises(robots_policy.RobotsDenied):
                    scan.fetch("https://agency.example/Bids.aspx")
                opener.assert_not_called()

    def test_redirect_target_must_pass_robots(self):
        with patch.object(robots_policy, "assert_allowed",
                          side_effect=robots_policy.RobotsDenied("redirect blocked")):
            handler = scan.RobotsAwareRedirect()
            with self.assertRaises(robots_policy.RobotsDenied):
                handler.redirect_request(Request("https://agency.example/Bids.aspx"),
                                         None, 302, "Found", {},
                                         "https://other.example/private")


if __name__ == "__main__":
    unittest.main()
