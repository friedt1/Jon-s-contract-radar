"""Regression: unsafe staged URLs must be visible in strict coverage blockers."""
import unittest

from audit_source_coverage import audit, strict_failures


class InvalidStagedCandidateAuditTests(unittest.TestCase):
    def test_invalid_staged_candidate_is_explicit_strict_blocker(self):
        report = audit([{
            "name": "Synthetic Municipal Procurement Office",
            "mode": "discovery_pending",
            "candidate_official_url": "http://example.invalid/procurement",
        }])
        self.assertEqual(report["invalid_staged_candidate_urls"], 1)
        self.assertEqual(report["official_urls_staged"], 0)
        self.assertTrue(report["sources"][0]["invalid_staged_candidate_url"])
        self.assertIn("invalid staged candidate URLs: 1",
                      strict_failures(report, expected_targets=1))

    def test_missing_candidate_is_discovery_not_invalid_url(self):
        report = audit([{
            "name": "Synthetic Municipal Procurement Office",
            "mode": "discovery_pending",
        }])
        self.assertEqual(report["invalid_staged_candidate_urls"], 0)
        self.assertEqual(report["discovery_required"], 1)
        self.assertFalse(any("invalid staged candidate URLs" in failure
                             for failure in strict_failures(report, expected_targets=1)))


if __name__ == "__main__":
    unittest.main()
