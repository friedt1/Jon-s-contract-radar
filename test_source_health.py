"""Offline source-health tests: synthetic statuses never represent real contracts."""
import unittest

import source_health


class SourceHealthTests(unittest.TestCase):
    def test_fetched_homepage_is_not_verified_bid_extraction(self):
        src = {"name": "County", "mode": "direct_page", "url": "https://county.example/Bids.aspx",
               "verified_url": True}
        row = source_health.classify(src, "direct fetched; 1 listing pages; 4 individual bid records; "
                                    "3 relevant details checked; 2 individual bid details fetched; "
                                    "0 unverified candidates; "
                                    "indirect RSS error: RobotsDenied")
        self.assertEqual(row["direct_state"], "fetched_unverified")
        self.assertEqual(row["individual_bid_records_found"], 4)
        self.assertEqual(row["detail_fetches_attempted"], 3)
        self.assertEqual(row["individual_bid_details_fetched"], 2)
        self.assertEqual(row["unverified_candidates"], 0)
        self.assertEqual(row["indirect_state"], "robots_blocked")

    def test_staged_official_url_does_not_count_as_direct(self):
        src = {"name": "Yates County", "mode": "discovery_pending", "url": "",
               "verified_url": False, "candidate_official_url": "https://www.yatescountyny.gov/bids.aspx"}
        summary = source_health.summarize([src], {"Yates County": "indirect RSS error: RobotsDenied"})
        self.assertEqual(summary["counts"]["configured_direct"], 0)
        self.assertEqual(summary["counts"]["staged_official_url"], 1)
        self.assertEqual(summary["counts"]["indirect_robots_blocked"], 1)

    def test_blocked_and_login_only_are_not_successful(self):
        sources = [
            {"name": "PennBid", "mode": "direct_page", "url": "https://pennbid.example", "verified_url": True},
            {"name": "BidNet", "mode": "direct_page", "url": "https://bidnet.example", "verified_url": True},
            {"name": "Other", "mode": "discovery_pending", "url": "", "verified_url": False},
        ]
        status = {
            "PennBid": "direct blocked by robots policy: disallowed",
            "BidNet": "direct fetched; 1 listing pages; 0 candidates; "
                      "individual listing ingestion not connected",
            "Other": "indirect RSS error: RobotsDenied",
        }
        summary = source_health.summarize(sources, status)
        self.assertEqual(summary["counts"]["configured_direct"], 2)
        self.assertEqual(summary["counts"]["configured_access_required"], 1)
        self.assertEqual(summary["counts"]["configured_fetch_targets"], 1)
        self.assertEqual(summary["counts"]["fetched_unverified"], 0)
        self.assertEqual(summary["counts"]["robots_blocked"], 1)
        self.assertEqual(summary["counts"]["access_required"], 1)
        self.assertEqual(summary["counts"]["not_configured"], 1)
        self.assertEqual(summary["counts"]["individual_bid_details_fetched"], 0)

    def test_failed_fetch_and_missing_status_are_visible(self):
        src = {"name": "County", "mode": "direct_page", "url": "https://county.example/bids",
               "verified_url": True}
        self.assertEqual(source_health.classify(src, "direct error: TimeoutError")["direct_state"], "fetch_error")
        self.assertEqual(source_health.classify(src, "")["direct_state"], "not_fetched")

    def test_http_denials_are_not_reported_as_successful_or_generic_errors(self):
        src = {"name": "County", "mode": "direct_page",
               "url": "https://county.example/bids", "verified_url": True}
        for code in (401, 403):
            with self.subTest(code=code):
                row = source_health.classify(src, f"direct error: HTTPError HTTP {code}; indirect RSS ok; 0 candidates")
                self.assertEqual(row["direct_state"], "http_blocked")
                self.assertEqual(row["indirect_state"], "ok")
        # A 404 is not evidence that credentials are required.
        self.assertEqual(source_health.classify(src, "direct error: HTTPError HTTP 404")["direct_state"],
                         "fetch_error")

    def test_redirect_rate_limit_and_non_html_are_distinct_states(self):
        src = {"name": "County", "mode": "direct_page",
               "url": "https://county.example/bids", "verified_url": True}
        cases = {
            "direct error: UnsafeRedirect": "redirect_blocked",
            "direct error: HTTPError HTTP 429": "rate_limited",
            "unsupported content type; indirect RSS ok; 0 candidates": "unsupported_content",
            "direct error: TimeoutError": "fetch_error",
        }
        for status, expected in cases.items():
            with self.subTest(status=status):
                self.assertEqual(source_health.classify(src, status)["direct_state"], expected)

    def test_diagnostic_states_counted_without_activating_staged_sources(self):
        names = ["Denied", "Redirect", "Rate", "NonHTML", "Staged"]
        sources = [{"name": n, "mode": "direct_page", "verified_url": True,
                    "url": "https://county.example/bids"} for n in names[:4]]
        sources.append({"name": "Staged", "mode": "discovery_pending", "verified_url": False,
                        "candidate_official_url": "https://county.example/bids"})
        statuses = {
            "Denied": "direct error: HTTPError HTTP 403",
            "Redirect": "direct error: UnsafeRedirect",
            "Rate": "direct error: HTTPError HTTP 429",
            "NonHTML": "unsupported content type",
            "Staged": "indirect RSS ok; 0 candidates",
        }
        counts = source_health.summarize(sources, statuses)["counts"]
        for state in ("http_blocked", "redirect_blocked", "rate_limited",
                      "unsupported_content", "staged_official_url"):
            self.assertEqual(counts[state], 1)
        self.assertEqual(counts["configured_direct"], 4)
        self.assertEqual(counts["fetched_unverified"], 0)

    def test_civicplus_detail_budget_deferral_is_incomplete_coverage(self):
        src = {"name": "County", "mode": "direct_page",
               "url": "https://county.example/Bids.aspx", "verified_url": True}
        status = ("direct fetched; 1 listing pages; 37 individual bid records; "
                  "36 relevant details checked; "
                  "1 individual bid records deferred at detail budget; "
                  "1 individual bid details fetched; 0 unverified candidates")
        row = source_health.classify(src, status)
        self.assertEqual(row["detail_budget_deferred"], 1)
        self.assertEqual(row["individual_bid_records_found"], 37)
        counts = source_health.summarize([src], {"County": status})["counts"]
        self.assertEqual(counts["detail_budget_deferred"], 1)
        self.assertEqual(counts["detail_budget_incomplete_sources"], 1)
        self.assertEqual(counts["fetched_unverified"], 1)

    def test_pagination_failure_is_not_complete_coverage(self):
        src = {"name": "Tioga fixture", "mode": "direct_page",
               "url": "https://county.example/bids", "verified_url": True}
        status = ("direct fetched; 2 listing pages; 4 individual bid records; "
                  "1 individual bid details fetched; "
                  "2 pagination errors: RobotsDenied,TimeoutError")
        row = source_health.classify(src, status)
        self.assertEqual(row["direct_state"], "fetched_unverified")
        self.assertEqual(row["pagination_errors"], 2)
        self.assertEqual(row["pagination_access_state"], "robots_blocked")
        self.assertEqual(row["individual_bid_details_fetched"], 1)
        counts = source_health.summarize([src], {src["name"]: status})["counts"]
        self.assertEqual(counts["pagination_errors"], 2)
        self.assertEqual(counts["pagination_incomplete_sources"], 1)
        self.assertEqual(counts["pagination_robots_blocked_sources"], 1)

    def test_partial_pagination_failure_without_robots(self):
        src = {"name": "County", "mode": "direct_page",
               "url": "https://county.example/bids", "verified_url": True}
        row = source_health.classify(
            src, "direct fetched; 1 listing pages; 1 pagination errors: TimeoutError")
        self.assertEqual(row["pagination_access_state"], "partial_listing_errors")
        self.assertEqual(row["pagination_errors"], 1)
        clean = source_health.classify(src, "direct fetched; 1 listing pages")
        self.assertEqual(clean["pagination_errors"], 0)
        self.assertEqual(clean["pagination_access_state"], "no_reported_errors")

    def test_mixed_detail_and_pagination_access_failures_are_all_counted(self):
        # Synthetic diagnostics: neither a fetch nor a live bid.
        src = {"name": "County", "mode": "direct_page",
               "url": "https://county.example/bids", "verified_url": True}
        status = ("direct fetched; 1 listing pages; "
                  "3 detail errors: RobotsDenied,HTTPError HTTP 403,HTTPError HTTP 429; "
                  "2 pagination errors: UnsafeRedirect,RobotsDenied")
        row = source_health.classify(src, status)
        self.assertEqual(row["detail_access_state"], "robots_blocked")
        self.assertEqual(row["pagination_access_state"], "robots_blocked")
        self.assertEqual(
            row["detail_error_types"],
            ["robots_blocked", "http_blocked", "rate_limited"])
        self.assertEqual(
            row["pagination_error_types"], ["robots_blocked", "redirect_blocked"])
        counts = source_health.summarize([src], {"County": status})["counts"]
        for key in ("detail_robots_blocked_sources", "detail_http_blocked_sources",
                    "detail_rate_limited_sources", "pagination_robots_blocked_sources",
                    "pagination_redirect_blocked_sources"):
            with self.subTest(key=key):
                self.assertEqual(counts[key], 1)
        self.assertEqual(counts["detail_redirect_blocked_sources"], 0)
        self.assertEqual(counts["pagination_http_blocked_sources"], 0)

    def test_zero_error_count_cannot_create_access_failure_types(self):
        src = {"name": "County", "mode": "direct_page",
               "url": "https://county.example/bids", "verified_url": True}
        status = ("direct fetched; 0 detail errors: RobotsDenied; "
                  "0 pagination errors: HTTPError HTTP 403")
        row = source_health.classify(src, status)
        self.assertEqual(row["detail_error_types"], [])
        self.assertEqual(row["pagination_error_types"], [])
        self.assertEqual(row["detail_access_state"], "not_attempted")
        self.assertEqual(row["pagination_access_state"], "no_reported_errors")
        counts = source_health.summarize([src], {"County": status})["counts"]
        self.assertEqual(counts["detail_robots_blocked_sources"], 0)
        self.assertEqual(counts["pagination_http_blocked_sources"], 0)

    def test_official_feed_and_authorized_api_are_direct_modes(self):
        sources = [
            {"name": "Feed", "mode": "official_feed", "url": "https://county.example/feed.xml",
             "verified_url": True},
            {"name": "API", "mode": "authorized_api", "url": "https://county.example/api/bids",
             "verified_url": True},
        ]
        summary = source_health.summarize(sources, {
            "Feed": "direct fetched; 1 listing pages; 0 individual bid details fetched",
            "API": "direct error: TimeoutError",
        })
        self.assertEqual(summary["counts"]["configured_direct"], 2)
        # A stale/handcrafted status must not make an unimplemented adapter
        # appear to have fetched individual listings.
        self.assertEqual(summary["counts"]["fetched_unverified"], 0)
        self.assertEqual(summary["counts"]["fetch_error"], 0)
        self.assertEqual(summary["counts"]["adapter_not_implemented"], 2)
        self.assertEqual(summary["counts"]["configured_fetch_targets"], 0)
        self.assertEqual(summary["counts"]["not_configured"], 0)


    def test_landing_page_fetches_do_not_imply_individual_bid_coverage(self):
        # All statuses are synthetic. No source is activated and no lead is
        # manufactured by this accounting test.
        sources = [
            {"name": name, "mode": "direct_page",
             "url": f"https://{name.lower()}.example/bids",
             "verified_url": True}
            for name in ("Details", "PdfArchive", "IndexOnly", "Failed")
        ]
        sources.append({"name": "Staged", "mode": "discovery_pending",
                        "candidate_official_url": "https://staged.example/bids"})
        statuses = {
            "Details": ("direct fetched; 1 listing pages; "
                        "2 individual bid details fetched; 0 candidates"),
            "PdfArchive": ("direct fetched; 1 listing pages; "
                           "0 individual bid details fetched; 4 PDFs checked; "
                           "18 PDF requests skipped at budget"),
            "IndexOnly": ("direct fetched; 1 listing pages; "
                          "0 individual bid details fetched"),
            "Failed": "direct error: TimeoutError",
            "Staged": "indirect RSS error: RobotsDenied",
        }
        counts = source_health.summarize(sources, statuses)["counts"]
        self.assertEqual(counts["fetched_unverified"], 3)
        self.assertEqual(counts["individual_bid_details_fetched"], 2)
        self.assertEqual(counts["individual_detail_retrieval_sources"], 1)
        self.assertEqual(counts["fetched_without_individual_details_sources"], 2)
        self.assertEqual(counts["fetched_with_incomplete_extraction_sources"], 1)
        self.assertEqual(counts["staged_official_url"], 1)
        self.assertEqual(counts["fetch_error"], 1)

    def test_failed_detail_and_pagination_fetches_mark_incomplete_coverage(self):
        src = {"name": "County", "mode": "direct_page",
               "url": "https://county.example/bids", "verified_url": True}
        status = ("direct fetched; 1 listing pages; "
                  "1 individual bid details fetched; "
                  "2 detail errors: TimeoutError; "
                  "1 pagination errors: RobotsDenied")
        counts = source_health.summarize([src], {"County": status})["counts"]
        self.assertEqual(counts["individual_detail_retrieval_sources"], 1)
        self.assertEqual(counts["fetched_without_individual_details_sources"], 0)
        self.assertEqual(counts["fetched_with_incomplete_extraction_sources"], 1)


if __name__ == "__main__":
    unittest.main()
