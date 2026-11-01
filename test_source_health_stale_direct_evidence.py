"""Synthetic source diagnostics: stale status must not manufacture ingestion."""
import unittest

from source_health import classify, summarize


class StaleDirectEvidenceTests(unittest.TestCase):
    STALE = (
        "direct fetched; 2 listing pages; 5 individual bid records; "
        "3 relevant details checked; 2 individual bid details fetched; "
        "1 detail errors: HTTPError HTTP 403; "
        "1 pagination errors: RobotsDenied; "
        "2 PDF-shaped requests attempted; 1 unverified candidates"
    )

    def test_staged_source_cannot_inherit_old_direct_counts(self):
        src = {"name": "Staged", "mode": "discovery_pending",
               "candidate_official_url": "https://county.example/bids",
               "verified_url": False, "url": ""}
        row = classify(src, self.STALE + "; indirect RSS ok; 0 candidates")
        self.assertEqual(row["direct_state"], "staged_official_url")
        self.assertEqual(row["indirect_state"], "ok")
        self.assertEqual(row["diagnostic"].split(";")[0], "direct fetched")
        for key in ("individual_bid_records_found", "detail_fetches_attempted",
                    "individual_bid_details_fetched", "detail_errors",
                    "pagination_errors", "pdf_fetch_attempts", "unverified_candidates"):
            with self.subTest(key=key):
                self.assertEqual(row[key], 0)
        self.assertEqual(row["detail_error_types"], [])
        self.assertEqual(row["pagination_error_types"], [])

    def test_access_required_and_unimplemented_sources_do_not_count_stale_fetch(self):
        sources = [
            {"name": "Gateway", "mode": "direct_page", "verified_url": True,
             "url": "https://vendor.example/bids", "provider_access_required": True},
            {"name": "Unimplemented", "mode": "official_feed", "verified_url": True,
             "url": "https://county.example/feed.xml"},
        ]
        summary = summarize(sources, {src["name"]: self.STALE for src in sources})
        self.assertEqual(summary["counts"]["individual_bid_details_fetched"], 0)
        self.assertEqual(summary["counts"]["individual_bid_records_found"], 0)
        self.assertEqual(summary["counts"]["detail_errors"], 0)
        self.assertEqual(summary["counts"]["pagination_errors"], 0)
        self.assertEqual(summary["counts"]["fetched_unverified"], 0)
        self.assertEqual(summary["counts"]["access_required"], 1)
        self.assertEqual(summary["counts"]["adapter_not_implemented"], 1)

    def test_blocked_direct_page_does_not_claim_retrieved_notices(self):
        src = {"name": "Denied", "mode": "direct_page", "verified_url": True,
               "url": "https://county.example/bids"}
        row = classify(src, "direct error: HTTPError HTTP 403; " + self.STALE)
        self.assertEqual(row["direct_state"], "http_blocked")
        self.assertEqual(row["individual_bid_details_fetched"], 0)
        self.assertEqual(row["detail_errors"], 0)
        self.assertIn("direct fetched", row["diagnostic"])

    def test_successful_direct_page_still_reports_real_attempts(self):
        src = {"name": "County", "mode": "direct_page", "verified_url": True,
               "url": "https://county.example/bids"}
        row = classify(src, self.STALE)
        self.assertEqual(row["direct_state"], "fetched_unverified")
        self.assertEqual(row["individual_bid_records_found"], 5)
        self.assertEqual(row["individual_bid_details_fetched"], 2)
        self.assertEqual(row["detail_errors"], 1)
        self.assertEqual(row["pagination_errors"], 1)
        self.assertEqual(row["detail_error_types"], ["http_blocked"])
        self.assertEqual(row["pagination_error_types"], ["robots_blocked"])


if __name__ == "__main__":
    unittest.main()
