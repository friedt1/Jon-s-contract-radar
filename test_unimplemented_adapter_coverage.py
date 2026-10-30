"""Synthetic adapter-coverage tests; no real solicitations are created."""

import unittest
from unittest.mock import patch

import audit_source_coverage
import scan
import source_config
import source_health


class UnimplementedAdapterCoverageTests(unittest.TestCase):
    def setUp(self):
        self.sources = [
            {"name": "Synthetic official feed", "mode": "official_feed",
             "url": "https://county.example/bids.xml", "verified_url": True},
            {"name": "Synthetic authorized API", "mode": "authorized_api",
             "url": "https://county.example/api/bids", "verified_url": True},
        ]

    def test_verified_feed_and_api_are_configured_but_not_fetch_targets(self):
        for source in self.sources:
            with self.subTest(mode=source["mode"]):
                self.assertTrue(source_config.direct_configured(source))
                self.assertFalse(source_config.direct_fetch_target(source))
        report = audit_source_coverage.audit(self.sources)
        self.assertEqual(report["direct_configured"], 2)
        self.assertEqual(report["direct_fetch_targets"], 0)
        self.assertEqual(report["configured_unimplemented_adapters"], 2)
        self.assertEqual(report["not_directly_monitored"], 0)
        self.assertTrue(all(row["adapter_not_implemented"] for row in report["sources"]))
        self.assertTrue(all(not row["direct_fetch_target"] for row in report["sources"]))

    def test_scanner_reports_unsupported_modes_without_fetching(self):
        for source in self.sources:
            with self.subTest(mode=source["mode"]):
                with patch.object(scan, "scan_direct") as direct, patch.object(
                    scan, "scan_news", return_value=[]
                ) as indirect:
                    _, status, leads = scan.run(source)
                direct.assert_not_called()
                indirect.assert_called_once_with(source)
                self.assertIn("direct adapter not implemented", status)
                self.assertEqual(leads, [])

    def test_source_health_never_calls_unimplemented_mode_fetched(self):
        health = source_health.summarize(self.sources, {
            source["name"]: "direct adapter not implemented: feed/API URL configured"
            for source in self.sources
        })
        self.assertEqual(health["counts"]["configured_direct"], 2)
        self.assertEqual(health["counts"]["configured_fetch_targets"], 0)
        self.assertEqual(health["counts"]["configured_unimplemented_adapters"], 2)
        self.assertEqual(health["counts"]["fetched_unverified"], 0)
        self.assertEqual([row["direct_state"] for row in health["sources"]],
                         ["adapter_not_implemented", "adapter_not_implemented"])

    def test_implemented_page_still_eligible_for_direct_fetch(self):
        source = {"name": "Synthetic county", "mode": "direct_page",
                  "url": "https://county.example/Bids.aspx", "verified_url": True}
        self.assertTrue(source_config.direct_fetch_target(source))
        with patch.object(scan, "scan_direct", return_value=([], "direct fetched")) as direct, patch.object(
            scan, "scan_news", return_value=[]
        ):
            _, status, leads = scan.run(source)
        direct.assert_called_once_with(source)
        self.assertIn("direct fetched", status)
        self.assertEqual(leads, [])

    def test_provider_access_flag_blocks_even_implemented_page(self):
        source = {"name": "Synthetic delegated county", "mode": "direct_page",
                  "url": "https://county.example/purchasing", "verified_url": True,
                  "delegated_provider": "BidNet"}
        audit = audit_source_coverage.audit([source])
        self.assertEqual(audit["direct_fetch_targets"], 0)
        self.assertEqual(audit["configured_provider_access_required"], 1)
        with patch.object(scan, "scan_direct") as direct, patch.object(
            scan, "scan_news", return_value=[]
        ):
            _, status, _ = scan.run(source)
        direct.assert_not_called()
        self.assertIn("direct access required", status)
        health = source_health.summarize([source], {source["name"]: status})
        self.assertEqual(health["counts"]["configured_fetch_targets"], 0)
        self.assertEqual(health["sources"][0]["direct_state"], "access_required")


if __name__ == "__main__":
    unittest.main()
