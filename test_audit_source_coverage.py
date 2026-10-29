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

    def test_unconnected_portal_urls_are_not_fetch_targets(self):
        result = audit([
            {"name": "PennBid platform", "mode": "direct_page",
             "url": "https://pennbid.bonfirehub.com", "verified_url": True},
            {"name": "BidNet NY platform", "mode": "direct_page",
             "url": "https://www.bidnetdirect.com/new-york", "verified_url": True},
            {"name": "Chemung County bids", "mode": "direct_page",
             "url": "https://chemungcountyny.gov/Bids.aspx", "verified_url": True},
            {"name": "Pending", "mode": "discovery_pending", "url": "",
             "verified_url": False},
        ])
        self.assertEqual(result["total"], 4)
        self.assertEqual(result["direct_configured"], 3)
        self.assertEqual(result["direct_fetch_targets"], 1)
        self.assertEqual(result["configured_provider_access_required"], 2)
        self.assertEqual(result["not_directly_monitored"], 1)
        for row in result["sources"][:2]:
            self.assertTrue(row["provider_access_required"])
            self.assertFalse(row["direct_fetch_target"])
            self.assertIn("not connected", row["status"])
        self.assertTrue(result["sources"][2]["direct_fetch_target"])
        self.assertFalse(result["sources"][3]["direct_fetch_target"])


if __name__ == "__main__":
    unittest.main()
