"""Offline strict-audit checks for staged procurement gates."""
import unittest

from audit_source_coverage import audit, strict_failures


class StagedStrictGateTests(unittest.TestCase):
    def test_staged_provider_and_homepage_are_not_live_feeds(self):
        report = audit([
            {"name": "Provider gateway", "mode": "discovery_pending",
             "candidate_official_url": "https://supplier.example/bids",
             "provider_access_required": True},
            {"name": "Publisher homepage", "mode": "discovery_pending",
             "candidate_official_url": "https://county.example/",
             "official_page_role": "publisher_entrypoint_only"},
        ])
        self.assertEqual(report["direct_fetch_targets"], 0)
        self.assertEqual(report["staged_provider_access_required"], 1)
        self.assertEqual(report["staged_publisher_entrypoints_only"], 1)
        blockers = strict_failures(report, expected_targets=2)
        self.assertIn("staged provider authorization required: 1", blockers)
        self.assertIn("staged publisher-only pages without bid index: 1", blockers)


if __name__ == "__main__":
    unittest.main()
