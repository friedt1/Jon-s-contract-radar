"""Offline regression: robots.txt HTTP 429 is throttling, not a publisher disallow.

Synthetic sources and notices only; no new source is activated or bid published.
"""
import unittest
from unittest.mock import patch

import robots_policy
import scan
import source_health


SOURCE = {
    "name": "Synthetic County",
    "mode": "direct_page",
    "url": "https://county.example/Bids.aspx",
    "verified_url": True,
}


class RobotsPolicyRateLimitTests(unittest.TestCase):
    def test_scanner_keeps_robots_rate_limit_distinct(self):
        self.assertEqual(
            scan.error_label(robots_policy.RobotsDenied("robots HTTP 429")),
            "RobotsPolicyRateLimited",
        )
        self.assertEqual(
            scan.error_label(robots_policy.RobotsDenied("robots HTTP 503")),
            "RobotsPolicyUnavailable",
        )
        self.assertEqual(
            scan.error_label(robots_policy.RobotsDenied(
                "robots disallows requested path")),
            "RobotsDenied",
        )
        with patch.object(scan, "scan_direct", side_effect=(
            robots_policy.RobotsDenied("robots HTTP 429"))):
            _, status, leads = scan.run(
                SOURCE, news_access=(False, "shared provider unavailable"))
        self.assertEqual(leads, [])
        self.assertIn("direct robots policy rate limited: robots HTTP 429", status)
        row = source_health.classify(SOURCE, status)
        self.assertEqual(row["direct_state"], "rate_limited")
        self.assertEqual(row["individual_bid_details_fetched"], 0)
        self.assertEqual(
            source_health.summarize([SOURCE], {SOURCE["name"]: status})
            ["counts"]["rate_limited"], 1)

    def test_detail_and_pagination_rate_limit_remain_incomplete(self):
        status = (
            "direct fetched; 1 listing pages; 2 details checked; "
            "0 individual bid details fetched; "
            "2 detail errors: RobotsPolicyRateLimited,RobotsPolicyUnavailable; "
            "1 pagination errors: RobotsPolicyRateLimited"
        )
        row = source_health.classify(SOURCE, status)
        self.assertEqual(row["direct_state"], "fetched_unverified")
        self.assertEqual(row["detail_access_state"], "rate_limited")
        self.assertEqual(row["pagination_access_state"], "rate_limited")
        self.assertEqual(
            row["detail_error_types"],
            ["robots_policy_unavailable", "rate_limited"],
        )
        self.assertEqual(
            row["pagination_error_types"],
            ["robots_policy_unavailable", "rate_limited"],
        )
        counts = source_health.summarize(
            [SOURCE], {SOURCE["name"]: status})["counts"]
        self.assertEqual(counts["detail_rate_limited_sources"], 1)
        self.assertEqual(counts["pagination_rate_limited_sources"], 1)
        self.assertEqual(counts["detail_robots_blocked_sources"], 0)
        self.assertEqual(counts["pagination_robots_blocked_sources"], 0)
        self.assertEqual(counts["fetched_with_incomplete_extraction_sources"], 1)


if __name__ == "__main__":
    unittest.main()
