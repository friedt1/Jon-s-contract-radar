"""Synthetic robots access diagnostics: no live source or bid is implied."""
import unittest

import robots_policy
import scan
import source_health


SOURCE = {
    "name": "Synthetic County", "mode": "direct_page",
    "url": "https://county.example/Bids.aspx", "verified_url": True,
}


class NoticeRobotsDiagnosticsTests(unittest.TestCase):
    def test_scanner_error_label_preserves_permission_distinction(self):
        cases = {
            "robots disallows requested path": "RobotsDenied",
            "robots policy unavailable: URLError": "RobotsPolicyUnavailable",
            "robots HTTP 503": "RobotsPolicyUnavailable",
            "robots redirect blocked: different origin or policy path": "RobotsPolicyUnavailable",
            "robots policy too large": "RobotsPolicyUnavailable",
        }
        for reason, expected in cases.items():
            with self.subTest(reason=reason):
                self.assertEqual(
                    scan.error_label(robots_policy.RobotsDenied(reason)), expected
                )
        self.assertNotIn(
            "secret", scan.error_label(robots_policy.RobotsDenied(
                "robots policy unavailable: token=secret"
            ))
        )

    def test_unknown_policy_is_not_an_explicit_detail_or_pagination_disallow(self):
        status = ("direct fetched; 1 listing pages; 2 details checked; "
                  "0 individual bid details fetched; "
                  "1 detail errors: RobotsPolicyUnavailable; "
                  "1 pagination errors: RobotsPolicyUnavailable")
        row = source_health.classify(SOURCE, status)
        self.assertEqual(row["direct_state"], "fetched_unverified")
        self.assertEqual(row["detail_access_state"], "robots_policy_unavailable")
        self.assertEqual(row["pagination_access_state"], "robots_policy_unavailable")
        self.assertEqual(row["detail_error_types"], ["robots_policy_unavailable"])
        self.assertEqual(row["pagination_error_types"], ["robots_policy_unavailable"])
        counts = source_health.summarize([SOURCE], {SOURCE["name"]: status})["counts"]
        self.assertEqual(counts["detail_robots_policy_unavailable_sources"], 1)
        self.assertEqual(counts["pagination_robots_policy_unavailable_sources"], 1)
        self.assertEqual(counts["detail_robots_blocked_sources"], 0)
        self.assertEqual(counts["pagination_robots_blocked_sources"], 0)
        self.assertEqual(counts["fetched_with_incomplete_extraction_sources"], 1)

    def test_mixed_explicit_denial_and_policy_failure_are_both_visible(self):
        status = ("direct fetched; 2 detail errors: "
                  "RobotsDenied,RobotsPolicyUnavailable; "
                  "2 pagination errors: HTTPError HTTP 403,RobotsPolicyUnavailable")
        row = source_health.classify(SOURCE, status)
        self.assertEqual(row["detail_access_state"], "robots_blocked")
        self.assertEqual(row["detail_error_types"],
                         ["robots_blocked", "robots_policy_unavailable"])
        self.assertEqual(row["pagination_access_state"], "http_blocked")
        self.assertEqual(row["pagination_error_types"],
                         ["robots_policy_unavailable", "http_blocked"])
        counts = source_health.summarize([SOURCE], {SOURCE["name"]: status})["counts"]
        self.assertEqual(counts["detail_robots_blocked_sources"], 1)
        self.assertEqual(counts["detail_robots_policy_unavailable_sources"], 1)
        self.assertEqual(counts["pagination_robots_policy_unavailable_sources"], 1)
        self.assertEqual(counts["pagination_http_blocked_sources"], 1)

    def test_old_robotsdenied_status_remains_readable(self):
        row = source_health.classify(
            SOURCE, "direct fetched; 1 detail errors: RobotsDenied; "
                    "1 pagination errors: RobotsDenied"
        )
        self.assertEqual(row["detail_access_state"], "robots_blocked")
        self.assertEqual(row["pagination_access_state"], "robots_blocked")
        self.assertEqual(row["detail_error_types"], ["robots_blocked"])


if __name__ == "__main__":
    unittest.main()
