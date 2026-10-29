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

    def test_staged_urls_are_not_active_connections(self):
        result = audit([
            {"name": "Staged", "mode": "discovery_pending", "url": "",
             "verified_url": False, "candidate_official_url": "https://county.example/bids",
             "activation_gate": "Review robots and individual bid extraction"},
            {"name": "Unknown", "mode": "discovery_pending", "url": "",
             "verified_url": False},
            {"name": "Broken direct", "mode": "direct_page", "url": "",
             "verified_url": True},
        ])
        self.assertEqual(result["not_directly_monitored"], 3)
        self.assertEqual(result["official_urls_staged"], 1)
        self.assertEqual(result["discovery_required"], 1)
        self.assertEqual(result["invalid_direct_configurations"], 1)
        self.assertFalse(result["sources"][0]["direct_fetch_target"])
        self.assertIn("not verified", result["sources"][0]["status"])
        self.assertEqual(result["sources"][0]["candidate_official_url"],
                         "https://county.example/bids")
        self.assertIn("robots", result["sources"][0]["activation_gate"])

    def test_current_102_source_inventory_is_accounted_for(self):
        import json
        from pathlib import Path
        sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        result = audit(sources)
        self.assertEqual(result["total"], 102)
        self.assertEqual(
            result["direct_configured"] + result["official_urls_staged"]
            + result["invalid_direct_configurations"] + result["discovery_required"],
            102,
        )
        self.assertEqual(result["not_directly_monitored"],
                         result["official_urls_staged"] + result["invalid_direct_configurations"]
                         + result["discovery_required"])


if __name__ == "__main__":
    unittest.main()
