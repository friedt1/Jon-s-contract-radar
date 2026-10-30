"""Offline robots-policy tests; no live source is assumed crawlable."""
import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

import robots_policy
import scan


class RobotsResponse(io.BytesIO):
    status = 200


class RobotsPolicyTests(unittest.TestCase):
    def setUp(self):
        robots_policy._CACHE.clear()

    def test_specific_disallow_and_allowed_path(self):
        with patch.object(robots_policy, "urlopen", return_value=RobotsResponse(
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
        with patch.object(robots_policy, "urlopen", return_value=RobotsResponse(
                b"User-agent: *\nDisallow: /private\n")) as download:
            self.assertTrue(robots_policy.allowed("https://agency.example/Bids.aspx")[0])
            self.assertFalse(robots_policy.allowed("https://agency.example/private")[0])
            self.assertEqual(download.call_count, 1)

    def test_robots_redirect_rejects_unapproved_destinations_before_fetch(self):
        handler = robots_policy._SameOriginRobotsRedirect()
        original = Request("https://agency.example/robots.txt")
        for target in (
            "https://other.example/robots.txt",
            "http://agency.example/robots.txt",
            "https://agency.example/private",
            "https://agency.example/Account/Login",
            "https://agency.example/robots.txt?redirect=1",
            "https://agency.example/robots.txt#section",
            "https://user:secret@agency.example/robots.txt",
            "https://agency.example:8443/robots.txt",
            "https://agency.example:broken/robots.txt",
        ):
            with self.subTest(target=target):
                with self.assertRaisesRegex(
                        robots_policy.RobotsDenied, "robots redirect blocked"):
                    handler.redirect_request(
                        original, None, 302, "Found", {}, target)

    def test_same_origin_robots_redirect_can_be_followed(self):
        handler = robots_policy._SameOriginRobotsRedirect()
        request = handler.redirect_request(
            Request("https://agency.example/robots.txt"),
            None, 301, "Moved", {},
            "https://agency.example:443/robots.txt")
        self.assertEqual(request.full_url, "https://agency.example:443/robots.txt")

    def test_redirect_rejection_remains_a_distinct_robots_block(self):
        with patch.object(robots_policy, "urlopen", side_effect=(
                robots_policy.RobotsDenied("robots redirect blocked: different origin"))):
            ok, reason = robots_policy.allowed("https://agency.example/Bids.aspx")
        self.assertFalse(ok)
        self.assertIn("robots redirect blocked", reason)

    def test_policy_uses_restricted_redirect_handler(self):
        with patch.object(robots_policy, "build_opener") as builder:
            builder.return_value.open.return_value = RobotsResponse(
                b"User-agent: *\\nAllow: /\\n")
            ok, _ = robots_policy.allowed("https://agency.example/Bids.aspx")
        self.assertTrue(ok)
        self.assertIsInstance(builder.call_args.args[0],
                              robots_policy._SameOriginRobotsRedirect)

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
                                         "https://agency.example/private")


if __name__ == "__main__":
    unittest.main()
