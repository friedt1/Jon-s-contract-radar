"""Regression coverage for independently reported source activation gates."""
import unittest

from audit_source_coverage import audit


class ActivationBlockerTests(unittest.TestCase):
    def test_configured_html_is_not_claimed_live(self):
        row = audit([{
            "name": "Sample county", "mode": "direct_page",
            "verified_url": True, "url": "https://county.example.gov/Bids.aspx",
        }])["sources"][0]
        self.assertEqual(row["activation_blockers"], ["live_ingestion_unverified"])
        self.assertTrue(row["direct_fetch_target"])

    def test_feed_and_provider_access_are_independent(self):
        row = audit([{
            "name": "Sample county", "mode": "official_feed",
            "verified_url": True, "url": "https://county.example.gov/feed",
            "provider_access_required": True,
        }])["sources"][0]
        self.assertEqual(row["activation_blockers"], [
            "provider_authorization_required", "adapter_not_implemented",
        ])
        self.assertFalse(row["direct_fetch_target"])

    def test_staged_publisher_homepage_needs_bid_index(self):
        row = audit([{
            "name": "Sample township", "mode": "discovery_pending",
            "candidate_official_url": "https://township.example.gov/",
            "official_page_role": "publisher_entrypoint_only",
        }])["sources"][0]
        self.assertEqual(row["activation_blockers"], ["procurement_index_not_identified"])
        self.assertFalse(row["direct_configured"])

    def test_staged_supplier_gateway_reports_access_and_extraction(self):
        row = audit([{
            "name": "Sample city", "mode": "discovery_pending",
            "candidate_official_url": "https://city.example.gov/bids",
            "provider_access_required": True,
        }])["sources"][0]
        self.assertEqual(row["activation_blockers"], [
            "provider_authorization_required", "individual_notice_extraction_unverified",
        ])


if __name__ == "__main__":
    unittest.main()
