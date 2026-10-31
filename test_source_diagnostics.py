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


    def test_deferred_detail_requests_are_visible_without_claiming_open_bids(self):
        # Synthetic scanner evidence; no live solicitation is inserted.
        payload = {
            "source_status": {
                "PA statewide": ("direct fetched; 2 listing pages; "
                                 "87 detail candidates deferred at request budget; "
                                 "4 individual bid records deferred at detail budget; "
                                 "0 unverified candidates"),
                "County": "direct fetched; 1 listing pages; 0 candidates",
            },
            "source_health": {"sources": [
                {"name": "PA statewide", "direct_state": "fetched_unverified",
                 "detail_candidates_deferred": 87, "detail_budget_deferred": 4,
                 "pdf_budget_skips": 2, "detail_errors": 0, "pagination_errors": 0},
                {"name": "County", "direct_state": "fetched_unverified",
                 "detail_candidates_deferred": 0, "detail_budget_deferred": 0,
                 "detail_errors": 0, "pagination_errors": 0},
            ]},
            "opportunities": [],
        }
        result = source_diagnostics.report(payload)
        rows = {row["source"]: row for row in result["sources"]}
        self.assertEqual(result["detail_candidates_deferred"], 87)
        self.assertEqual(result["detail_budget_deferred"], 4)
        self.assertEqual(result["incomplete_detail_sources"], 1)
        self.assertTrue(rows["PA statewide"]["coverage_incomplete"])
        self.assertFalse(rows["PA statewide"]["error"])
        self.assertFalse(rows["County"]["coverage_incomplete"])
        self.assertEqual(result["verified_open_opportunities"], 0)

    def test_structured_health_and_status_gaps_are_not_silently_omitted(self):
        payload = {
            "source_status": {
                "County": "direct fetched; 1 listing pages",
                "Missing health": "direct fetched; 1 listing pages",
                "SAM.gov": "deferred",
            },
            "source_health": {"sources": [
                {"name": "County", "direct_state": "fetched_unverified"},
                {"name": "Missing status", "direct_state": "not_fetched"},
            ]},
            "opportunities": [],
        }
        result = source_diagnostics.report(payload)
        rows = {row["source"]: row for row in result["sources"]}
        self.assertEqual(len(rows), 4)
        self.assertTrue(rows["Missing status"]["status_missing"])
        self.assertTrue(rows["Missing status"]["error"])
        self.assertTrue(rows["Missing health"]["health_missing"])
        self.assertTrue(rows["Missing health"]["error"])
        self.assertFalse(rows["SAM.gov"]["health_missing"])
        self.assertFalse(rows["SAM.gov"]["error"])
        self.assertEqual(result["diagnostic_gaps"], 2)

    def test_legacy_status_fallback_reports_deferred_budget(self):
        result = source_diagnostics.report({
            "source_status": {
                "Legacy": ("direct fetched; 1 listing pages; "
                           "60 detail candidates deferred at request budget; "
                           "3 individual bid records deferred at detail budget"),
            },
            "opportunities": [],
        })
        row = result["sources"][0]
        self.assertEqual(row["detail_candidates_deferred"], 60)
        self.assertEqual(row["detail_budget_deferred"], 3)
        self.assertTrue(row["coverage_incomplete"])
        self.assertFalse(row["health_missing"])
        self.assertFalse(row["error"])

    def test_inventory_count_exposes_sources_missing_from_both_diagnostics(self):
        # All names are synthetic. A source absent from both structures must
        # not make the claimed three-target scan appear complete.
        result = source_diagnostics.report({
            "source_coverage": {"total_targets": 3},
            "source_status": {"County A": "direct fetched", "County B": "direct fetched"},
            "source_health": {"sources": [
                {"name": "County A", "direct_state": "fetched_unverified"},
                {"name": "County B", "direct_state": "fetched_unverified"},
            ]},
            "opportunities": [],
        })
        self.assertEqual(result["unaccounted_targets"], 1)
        self.assertEqual(result["health_inventory_shortfall"], 1)
        self.assertEqual(result["diagnostic_gaps"], 1)
        self.assertEqual(result["verified_open_opportunities"], 0)

    def test_duplicate_health_row_is_an_error_not_a_second_source(self):
        result = source_diagnostics.report({
            "source_coverage": {"total_targets": 2},
            "source_status": {"County A": "direct fetched", "County B": "direct fetched"},
            "source_health": {"sources": [
                {"name": "County A", "direct_state": "fetched_unverified"},
                {"name": "County A", "direct_state": "fetched_unverified"},
                {"name": "County B", "direct_state": "fetched_unverified"},
            ]},
            "opportunities": [],
        })
        rows = {row["source"]: row for row in result["sources"]}
        self.assertEqual(result["duplicate_health_rows"], ["County A"])
        self.assertTrue(rows["County A"]["duplicate_health_row"])
        self.assertTrue(rows["County A"]["error"])
        self.assertFalse(rows["County B"]["error"])
        self.assertEqual(result["diagnostic_gaps"], 1)
        self.assertEqual(result["unaccounted_targets"], 0)

    def test_named_inventory_detects_swapped_source_despite_matching_count(self):
        # Synthetic inventory: a missing source is masked by an unexpected
        # row when only counts are compared. SAM.gov is outside this inventory.
        result = source_diagnostics.report({
            "source_coverage": {
                "total_targets": 3,
                "expected_source_names": ["County A", "County B", "County C"],
            },
            "source_status": {
                "County A": "direct fetched",
                "County B": "direct fetched",
                "Unexpected": "direct fetched",
                "SAM.gov": "deferred",
            },
            "source_health": {"sources": [
                {"name": "County A", "direct_state": "fetched_unverified"},
                {"name": "County B", "direct_state": "fetched_unverified"},
                {"name": "Unexpected", "direct_state": "fetched_unverified"},
            ]},
            "opportunities": [],
        })
        self.assertEqual(result["missing_inventory_sources"], ["County C"])
        self.assertEqual(result["unexpected_inventory_sources"], ["Unexpected"])
        self.assertEqual(result["unaccounted_targets"], 1)
        self.assertEqual(result["health_inventory_shortfall"], 1)
        self.assertEqual(result["diagnostic_gaps"], 2)
        rows = {row["source"]: row for row in result["sources"]}
        self.assertTrue(rows["Unexpected"]["unexpected_inventory_source"])
        self.assertTrue(rows["Unexpected"]["error"])
        self.assertNotIn("SAM.gov", result["unexpected_inventory_sources"])
        self.assertEqual(result["verified_open_opportunities"], 0)

    def test_named_inventory_reconciles_complete_scan(self):
        result = source_diagnostics.report({
            "source_coverage": {
                "total_targets": 2,
                "expected_source_names": ["County B", "County A"],
            },
            "source_status": {
                "County A": "direct fetched",
                "County B": "direct fetched",
            },
            "source_health": {"sources": [
                {"name": "County A", "direct_state": "fetched_unverified"},
                {"name": "County B", "direct_state": "fetched_unverified"},
            ]},
            "opportunities": [],
        })
        self.assertEqual(result["missing_inventory_sources"], [])
        self.assertEqual(result["unexpected_inventory_sources"], [])
        self.assertEqual(result["diagnostic_gaps"], 0)

    def test_invalid_named_inventory_rejected(self):
        for names, total in [
            (["County A", "County A"], 2),
            (["County A", ""], 2),
            (["County A", 123], 2),
            ("County A", 1),
            (["County A"], 2),
        ]:
            with self.subTest(names=names, total=total):
                with self.assertRaises(ValueError):
                    source_diagnostics.report({
                        "source_coverage": {
                            "total_targets": total,
                            "expected_source_names": names,
                        },
                        "source_status": {},
                        "source_health": {"sources": []},
                        "opportunities": [],
                    })

    def test_legacy_feed_does_not_claim_inventory_reconciliation(self):
        result = source_diagnostics.report({
            "source_coverage": {"total_targets": 102},
            "source_status": {"Legacy": "direct fetched"},
            "opportunities": [],
        })
        self.assertEqual(result["unaccounted_targets"], 0)
        self.assertEqual(result["health_inventory_shortfall"], 0)
        self.assertEqual(result["duplicate_health_rows"], [])

    def test_staged_provider_gate_is_access_required_but_not_direct_failure(self):
        result = source_diagnostics.report({
            "source_status": {"Utility": "indirect RSS error: RobotsDenied"},
            "source_health": {"sources": [{
                "name": "Utility", "direct_state": "staged_official_url",
                "indirect_state": "robots_blocked",
                "staged_provider_access_required": True,
            }]},
            "opportunities": [],
        })
        row = result["sources"][0]
        self.assertTrue(row["access_required"])
        self.assertTrue(row["staged_access_required"])
        self.assertFalse(row["direct_error"])
        self.assertFalse(row["error"])
        self.assertEqual(result["verified_open_opportunities"], 0)


if __name__ == "__main__":
    unittest.main()
