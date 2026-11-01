"""Structured source diagnostics must not resurrect stale direct-ingestion counts.

All statuses below are synthetic; historical Erie/Owego labels are regression
names only. No opportunity is inserted into the production feed.
"""
import unittest

from source_diagnostics import report


STALE = (
    "direct fetched; 9 listing pages; 51 individual bid records; "
    "37 relevant details checked; 5 individual bid records deferred at detail budget; "
    "17 detail candidates deferred at request budget; 12 unverified candidates"
)


class StructuredEvidenceBoundaryTests(unittest.TestCase):
    def test_missing_or_inactive_health_cannot_inherit_raw_counts(self):
        payload = {
            "source_status": {
                "Historical Erie tree/stump removal": STALE,
                "Owego demolition (unrelated)": STALE,
                "Missing health": STALE,
                "Fetched county": "direct fetched; 2 listing pages; " + STALE,
            },
            "source_health": {
                "sources": [
                    {"name": "Historical Erie tree/stump removal",
                     "direct_state": "staged_official_url"},
                    {"name": "Owego demolition (unrelated)",
                     "direct_state": "http_blocked"},
                    {"name": "Fetched county", "direct_state": "fetched_unverified",
                     "individual_bid_records_found": 1,
                     "detail_fetches_attempted": 1,
                     "unverified_candidates": 0},
                ]
            },
            "opportunities": [],
        }
        result = report(payload)
        rows = {row["source"]: row for row in result["sources"]}
        for name in ("Historical Erie tree/stump removal",
                     "Owego demolition (unrelated)", "Missing health"):
            with self.subTest(source=name):
                row = rows[name]
                self.assertIsNone(row["listing_pages"])
                self.assertIsNone(row["individual_records"])
                self.assertIsNone(row["details_checked"])
                self.assertIsNone(row["candidates"])
                self.assertEqual(row["detail_budget_deferred"], 0)
                self.assertEqual(row["detail_candidates_deferred"], 0)
                self.assertIn("51 individual bid records", row["raw_status"])
        self.assertTrue(rows["Missing health"]["health_missing"])
        self.assertTrue(rows["Missing health"]["error"])
        self.assertEqual(result["diagnostic_gaps"], 1)
        self.assertEqual(result["detail_budget_deferred"], 0)
        self.assertEqual(result["detail_candidates_deferred"], 0)
        self.assertEqual(result["verified_open_opportunities"], 0)
        self.assertEqual(rows["Fetched county"]["listing_pages"], 2)
        self.assertEqual(rows["Fetched county"]["individual_records"], 1)
        self.assertEqual(rows["Fetched county"]["details_checked"], 1)
        self.assertEqual(rows["Fetched county"]["candidates"], 0)

    def test_legacy_status_only_feed_still_parses_counts(self):
        result = report({
            "source_status": {"Legacy county": STALE},
            "opportunities": [],
        })
        row = result["sources"][0]
        self.assertEqual(row["listing_pages"], 9)
        self.assertEqual(row["individual_records"], 51)
        self.assertEqual(row["details_checked"], 37)
        self.assertEqual(row["candidates"], 12)
        self.assertEqual(row["detail_budget_deferred"], 5)
        self.assertEqual(row["detail_candidates_deferred"], 17)
        self.assertEqual(result["verified_open_opportunities"], 0)


if __name__ == "__main__":
    unittest.main()
