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
