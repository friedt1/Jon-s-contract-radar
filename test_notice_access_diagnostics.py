"""Offline regression cases for individual-notice and listing-page access diagnostics.

These synthetic statuses do not represent actual solicitations or live bids.
"""
import unittest
from urllib.error import HTTPError

import scan
import source_health


def configured(name):
    return {
        "name": name, "mode": "direct_page", "verified_url": True,
        "url": "https://county.example/bids",
    }


class NoticeAccessDiagnosticsTests(unittest.TestCase):
    def test_http_status_is_retained_without_leaking_url(self):
        error = HTTPError("https://county.example/private?token=secret", 403,
                          "Forbidden", {}, None)
        self.assertEqual(scan.error_label(error), "HTTPError HTTP 403")
        self.assertNotIn("token", scan.error_label(error))

    def test_detail_http_access_is_not_reported_as_generic_failure(self):
        for token, state in (
            ("HTTPError HTTP 401", "http_blocked"),
            ("HTTPError HTTP 403", "http_blocked"),
            ("HTTPError HTTP 429", "rate_limited"),
            ("UnsafeRedirect", "redirect_blocked"),
            ("RobotsDenied", "robots_blocked"),
            ("TimeoutError", "fetch_error"),
        ):
            with self.subTest(token=token):
                row = source_health.classify(
                    configured("Synthetic"), "direct fetched; 1 listing pages; "
                    "2 details checked; 0 individual bid details fetched; "
                    "1 detail errors: " + token)
                self.assertEqual(row["direct_state"], "fetched_unverified")
                self.assertEqual(row["detail_errors"], 1)
                self.assertEqual(row["detail_access_state"], state)
                self.assertEqual(row["individual_bid_details_fetched"], 0)

    def test_pagination_http_access_does_not_claim_complete_listing(self):
        for token, state in (
            ("HTTPError HTTP 403", "http_blocked"),
            ("HTTPError HTTP 429", "rate_limited"),
            ("UnsafeRedirect", "redirect_blocked"),
            ("RobotsDenied", "robots_blocked"),
            ("TimeoutError", "partial_listing_errors"),
        ):
            with self.subTest(token=token):
                row = source_health.classify(
                    configured("Synthetic"), "direct fetched; 1 listing pages; "
                    "1 pagination errors: " + token)
                self.assertEqual(row["direct_state"], "fetched_unverified")
                self.assertEqual(row["pagination_errors"], 1)
                self.assertEqual(row["pagination_access_state"], state)

    def test_counts_separate_detail_and_pagination_blockers(self):
        sources = [configured(name) for name in ("Denied", "Rate", "Redirect")]
        statuses = {
            "Denied": "direct fetched; 1 detail errors: HTTPError HTTP 403; "
                      "1 pagination errors: HTTPError HTTP 401",
            "Rate": "direct fetched; 1 detail errors: HTTPError HTTP 429; "
                    "1 pagination errors: HTTPError HTTP 429",
            "Redirect": "direct fetched; 1 detail errors: UnsafeRedirect; "
                        "1 pagination errors: UnsafeRedirect",
        }
        counts = source_health.summarize(sources, statuses)["counts"]
        for prefix in ("detail", "pagination"):
            for state in ("http_blocked", "rate_limited", "redirect_blocked"):
                self.assertEqual(counts[prefix + "_" + state + "_sources"], 1)
        self.assertEqual(counts["pagination_incomplete_sources"], 3)
        self.assertEqual(counts["individual_bid_details_fetched"], 0)

    def test_staged_source_cannot_become_monitored_through_error_diagnostics(self):
        staged = {
            "name": "Staged", "mode": "discovery_pending",
            "candidate_official_url": "https://county.example/bids",
            "verified_url": False,
        }
        counts = source_health.summarize(
            [staged], {"Staged": "1 detail errors: HTTPError HTTP 403"}
        )["counts"]
        self.assertEqual(counts["configured_direct"], 0)
        self.assertEqual(counts["staged_official_url"], 1)
        # Staged sources have no authorized direct-detail adapter; an old\n        # status string cannot be treated as a new direct HTTP refusal.\n        self.assertEqual(counts["detail_http_blocked_sources"], 0)\n        self.assertEqual(counts["detail_errors"], 0)


if __name__ == "__main__":
    unittest.main()
