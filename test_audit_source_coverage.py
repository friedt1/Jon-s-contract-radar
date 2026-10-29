import unittest

from audit_source_coverage import audit


class CoverageAuditTests(unittest.TestCase):
    def test_indirect_is_not_direct(self):
        result = audit([{"name": "County", "mode": "discovery_pending", "url": "",
                         "verified_url": False}])
        self.assertEqual(result["not_directly_monitored"], 1)

    def test_homepage_without_verified_url_is_not_direct(self):
        result = audit([{"name": "County", "mode": "direct_page",
                         "url": "https://example.org", "verified_url": False}])
        self.assertEqual(result["direct_configured"], 0)

    def test_direct_configuration_is_not_live_verification(self):
        result = audit([{"name": "County", "mode": "direct_page",
                         "url": "https://example.org/bids", "verified_url": True}])
        self.assertEqual(result["direct_configured"], 1)
        self.assertIn("not independently verified", result["sources"][0]["status"])


if __name__ == "__main__":
    unittest.main()
