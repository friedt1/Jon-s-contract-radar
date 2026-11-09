"""Regression checks for agency counts versus unique fetch entrypoints."""
import unittest

from audit_source_coverage import audit


class DistinctDirectEntrypointTests(unittest.TestCase):
    def test_shared_direct_gateway_is_one_fetch_entrypoint(self):
        report = audit([
            {"name": "Agency A", "mode": "direct_page", "verified_url": True,
             "url": "https://bids.example.gov/notices"},
            {"name": "Agency B", "mode": "direct_page", "verified_url": True,
             "url": "https://bids.example.gov/notices"},
        ])
        self.assertEqual(report["direct_fetch_targets"], 2)
        self.assertEqual(report["distinct_direct_fetch_entrypoints"], 1)
        self.assertEqual(report["shared_official_entrypoint_targets"], 2)

    def test_access_required_gateway_is_not_fetchable(self):
        report = audit([
            {"name": "Agency A", "mode": "direct_page", "verified_url": True,
             "url": "https://bids.example.gov/notices",
             "provider_access_required": True},
            {"name": "Agency B", "mode": "direct_page", "verified_url": True,
             "url": "https://bids.example.gov/notices"},
        ])
        self.assertEqual(report["direct_fetch_targets"], 1)
        self.assertEqual(report["distinct_direct_fetch_entrypoints"], 1)

    def test_staged_candidate_is_not_direct_fetch(self):
        report = audit([
            {"name": "Agency A", "mode": "discovery_pending",
             "candidate_official_url": "https://bids.example.gov/notices"},
        ])
        self.assertEqual(report["direct_fetch_targets"], 0)
        self.assertEqual(report["distinct_direct_fetch_entrypoints"], 0)


if __name__ == "__main__":
    unittest.main()
