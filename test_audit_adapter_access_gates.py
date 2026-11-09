"""Regression tests for independent source adapter and authorization gates."""
import unittest

from audit_source_coverage import audit


class AdapterAuthorizationAuditTests(unittest.TestCase):
    def test_html_provider_gate_does_not_imply_missing_adapter(self):
        report = audit([{
            "name": "Provider gated HTML",
            "mode": "direct_page",
            "url": "https://example.org/bids",
            "verified_url": True,
            "provider_access_required": True,
        }])
        row = report["sources"][0]
        self.assertTrue(row["provider_access_required"])
        self.assertFalse(row["adapter_not_implemented"])
        self.assertFalse(row["direct_fetch_target"])
        self.assertEqual(report["configured_unimplemented_adapters"], 0)

    def test_feed_requires_adapter_even_without_provider_gate(self):
        report = audit([{
            "name": "Official feed without adapter",
            "mode": "official_feed",
            "url": "https://example.org/bids.xml",
            "verified_url": True,
        }])
        row = report["sources"][0]
        self.assertFalse(row["provider_access_required"])
        self.assertTrue(row["adapter_not_implemented"])
        self.assertFalse(row["direct_fetch_target"])

    def test_feed_and_provider_gate_are_two_distinct_blockers(self):
        report = audit([{
            "name": "Authorized feed not implemented",
            "mode": "authorized_api",
            "url": "https://example.org/api/bids",
            "verified_url": True,
            "provider_access_required": True,
        }])
        row = report["sources"][0]
        self.assertTrue(row["provider_access_required"])
        self.assertTrue(row["adapter_not_implemented"])
        self.assertFalse(row["direct_fetch_target"])


if __name__ == "__main__":
    unittest.main()
