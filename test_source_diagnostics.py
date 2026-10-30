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
