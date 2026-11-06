"""Regression guards: one shared procurement gateway is not 102 working feeds."""
import unittest

from audit_source_coverage import audit, strict_failures


class SharedEntrypointGateTests(unittest.TestCase):
    def test_shared_staged_gateway_does_not_activate_agencies(self):
        rows = [
            {"name": "County A", "mode": "discovery_pending",
             "candidate_official_url": "https://procurement.example/bids?utm_source=email",
             "delegated_provider": "supplier portal"},
            {"name": "County B", "mode": "discovery_pending",
             "candidate_official_url": "https://procurement.example/bids",
             "delegated_provider": "supplier portal"},
        ]
        report = audit(rows)
        self.assertEqual(report["direct_configured"], 0)
        self.assertEqual(report["direct_fetch_targets"], 0)
        self.assertEqual(report["official_urls_staged"], 2)
        self.assertEqual(report["staged_provider_access_required"], 2)
        self.assertEqual(report["distinct_official_entrypoints"], 1)
        self.assertEqual(report["shared_official_entrypoint_targets"], 2)
        self.assertTrue(all(r["shared_official_entrypoint"] for r in report["sources"]))
        self.assertTrue(all("authorization required" in r["status"] for r in report["sources"]))
        self.assertTrue(any("not directly configured: 2" in b
                            for b in strict_failures(report, expected_targets=2)))

    def test_distinct_notice_ids_do_not_count_as_shared_entrypoint(self):
        rows = [
            {"name": "County A", "mode": "discovery_pending",
             "candidate_official_url": "https://county.example/Bids.aspx?bidID=100"},
            {"name": "County B", "mode": "discovery_pending",
             "candidate_official_url": "https://county.example/Bids.aspx?bidID=101"},
        ]
        report = audit(rows)
        self.assertEqual(report["distinct_official_entrypoints"], 2)
        self.assertEqual(report["shared_official_entrypoint_groups"], {})
        self.assertEqual(report["shared_official_entrypoint_targets"], 0)

    def test_shared_direct_supplier_portal_is_not_fetchable(self):
        rows = [
            {"name": "Agency A", "mode": "direct_page", "verified_url": True,
             "url": "https://supplier.example/portal", "provider_access_required": True},
            {"name": "Agency B", "mode": "direct_page", "verified_url": True,
             "url": "https://supplier.example/portal?utm_campaign=alerts",
             "provider_access_required": True},
        ]
        report = audit(rows)
        self.assertEqual(report["direct_configured"], 2)
        self.assertEqual(report["direct_fetch_targets"], 0)
        self.assertEqual(report["configured_provider_access_required"], 2)
        self.assertEqual(report["shared_official_entrypoint_targets"], 2)
        self.assertTrue(any("provider access required: 2" in b
                            for b in strict_failures(report, expected_targets=2)))


if __name__ == "__main__":
    unittest.main()
