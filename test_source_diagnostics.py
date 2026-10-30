import unittest
import source_diagnostics


class SourceDiagnosticsTests(unittest.TestCase):
    def test_zero_results_are_not_success(self):
        result = source_diagnostics.report({
            "updated": "2026-10-29T00:00:00Z",
            "opportunities": [],
            "source_status": {
                "County": "direct fetched; 1 listing pages; 2 individual bid records; 2 relevant details checked; 0 unverified candidates",
                "Other": "blocked: HTTP 403"
            }
        })
        self.assertEqual(result["verified_open_opportunities"], 0)
        self.assertEqual(result["sources"][0]["individual_records"], 2)
        self.assertTrue(result["sources"][1]["error"])

    def test_indirect_robots_failure_is_not_direct_fetch_failure(self):
        result = source_diagnostics.report({
            "source_status": {
                "County": "direct fetched; 1 listing pages; 1 details checked; indirect RSS error: RobotsDenied",
                "Portal": "direct access required: individual listing ingestion not connected",
                "Blocked": "direct blocked by robots policy: disallowed",
            },
            "source_health": {
                "counts": {"configured_direct": 3, "fetched_unverified": 1},
                "sources": [
                    {"name": "County", "direct_state": "fetched_unverified",
                     "indirect_state": "robots_blocked",
                     "detail_access_state": "retrieved_unverified",
                     "detail_fetches_attempted": 1, "detail_errors": 0},
                    {"name": "Portal", "direct_state": "access_required",
                     "indirect_state": "not_run", "detail_errors": 0},
                    {"name": "Blocked", "direct_state": "robots_blocked",
                     "indirect_state": "not_run", "detail_errors": 0},
                ],
            },
            "source_coverage": {"total_targets": 3},
            "opportunities": [],
        })
        rows = {x["source"]: x for x in result["sources"]}
        self.assertFalse(rows["County"]["error"])
        self.assertTrue(rows["County"]["indirect_error"])
        self.assertEqual(rows["County"]["details_checked"], 1)
        self.assertTrue(rows["Portal"]["access_required"])
        self.assertFalse(rows["Portal"]["error"])
        self.assertTrue(rows["Blocked"]["direct_error"])
        self.assertTrue(rows["Blocked"]["error"])
        self.assertEqual(result["health_counts"]["configured_direct"], 3)
        self.assertEqual(result["source_coverage"]["total_targets"], 3)
        self.assertEqual(result["verified_open_opportunities"], 0)

    def test_direct_access_failures_are_not_hidden_by_indirect_success(self):
        # Synthetic publisher states, not real contract opportunities.
        statuses = {
            "Denied": ("http_blocked", "direct error: HTTPError HTTP 403"),
            "Redirect": ("redirect_blocked", "direct error: UnsafeRedirect"),
            "Rate": ("rate_limited", "direct error: HTTPError HTTP 429"),
            "NonHTML": ("unsupported_content", "unsupported content type"),
            "Robots": ("robots_blocked", "direct blocked by robots policy"),
            "Timeout": ("fetch_error", "direct error: TimeoutError"),
            "Portal": ("access_required", "individual listing ingestion not connected"),
            "Working": ("fetched_unverified", "direct fetched; 1 listing pages"),
        }
        payload = {
            "source_status": {
                name: message + "; indirect RSS ok; 0 candidates"
                for name, (_, message) in statuses.items()
            },
            "source_health": {
                "sources": [
                    {"name": name, "direct_state": state,
                     "indirect_state": "ok", "detail_errors": 0}
                    for name, (state, _) in statuses.items()
                ]
            },
            "opportunities": [],
        }
        rows = {row["source"]: row for row in source_diagnostics.report(payload)["sources"]}
        for name in ("Denied", "Redirect", "Rate", "NonHTML", "Robots", "Timeout"):
            with self.subTest(source=name):
                self.assertTrue(rows[name]["direct_error"])
                self.assertTrue(rows[name]["error"])
                self.assertFalse(rows[name]["indirect_error"])
        for name in ("Portal", "Working"):
            with self.subTest(source=name):
                self.assertFalse(rows[name]["direct_error"])
                self.assertFalse(rows[name]["error"])
        self.assertTrue(rows["Portal"]["access_required"])

    def test_pdf_budget_and_provider_skips_visible_per_source(self):
        payload = {
            "source_status": {"Tioga test fixture": "direct fetched; 0 candidates"},
            "source_health": {"sources": [{
                "name": "Tioga test fixture", "direct_state": "fetched_unverified",
                "indirect_state": "not_run", "detail_errors": 0,
                "pdf_fetch_attempts": 5, "pdf_budget_skips": 31,
                "result_award_links_excluded": 22,
                "external_provider_links_skipped": 3,
            }]},
            "opportunities": [],
        }
        row = source_diagnostics.report(payload)["sources"][0]
        self.assertEqual(row["pdf_fetch_attempts"], 5)
        self.assertEqual(row["pdf_budget_skips"], 31)
        self.assertEqual(row["result_award_links_excluded"], 22)
        self.assertEqual(row["external_provider_links_skipped"], 3)
        self.assertFalse(row["error"])

    def test_partial_listing_pagination_counts_as_error(self):
        payload = {
            "source_status": {
                "County": ("direct fetched; 1 listing pages; 1 individual bid records; "
                           "1 pagination errors: TimeoutError")
            },
            "source_health": {"sources": [{
                "name": "County", "direct_state": "fetched_unverified",
                "indirect_state": "ok", "detail_errors": 0,
                "pagination_errors": 1,
                "pagination_access_state": "partial_listing_errors",
            }]},
            "opportunities": [],
        }
        row = source_diagnostics.report(payload)["sources"][0]
        self.assertFalse(row["direct_error"])
        self.assertTrue(row["error"])
        self.assertEqual(row["pagination_errors"], 1)
        self.assertEqual(row["pagination_access_state"], "partial_listing_errors")

    def test_historical_status_without_structured_health(self):
        payload = {
            "source_status": {
                "Legacy non-HTML": "unsupported content type; indirect RSS ok",
                "Legacy denied": "direct error: HTTPError HTTP 403",
                "Legacy indirect": "direct fetched; indirect RSS error: RobotsDenied",
            },
            "opportunities": [],
        }
        rows = {r["source"]: r for r in source_diagnostics.report(payload)["sources"]}
        self.assertTrue(rows["Legacy non-HTML"]["direct_error"])
        self.assertTrue(rows["Legacy denied"]["direct_error"])
        self.assertFalse(rows["Legacy indirect"]["direct_error"])
        self.assertTrue(rows["Legacy indirect"]["indirect_error"])

    def test_rejects_invalid_source_health_schema(self):
        with self.assertRaises(ValueError):
            source_diagnostics.report({
                "source_status": {}, "opportunities": [],
                "source_health": {"sources": {}}
            })

    def test_unverified_is_not_verified(self):
        result = source_diagnostics.report({
            "opportunities": [{"status": "unverified", "open_status": "listing_open"}],
            "source_status": {}
        })
        self.assertEqual(result["published_opportunities"], 1)
        self.assertEqual(result["verified_open_opportunities"], 0)

    def test_rejects_invalid_schema(self):
        with self.assertRaises(ValueError):
            source_diagnostics.report({"source_status": [], "opportunities": {}})


if __name__ == "__main__":
    unittest.main()
