"""Offline coverage and fetch-gating tests; no fixtures are live bids."""
import unittest
from unittest.mock import patch

import audit_source_coverage
import scan
import source_config
import source_health


class SourceConfigurationTests(unittest.TestCase):
    def test_https_host_hygiene(self):
        for url in (
            "https://county.example/Bids.aspx",
            "https://county.example:443/Bids.aspx?year=2026",
            "https://www.cortlandcountyny.gov/Bids.aspx",
        ):
            with self.subTest(url=url):
                self.assertTrue(source_config.valid_public_https_url(url))
        for url in (
            "", None, "http://county.example/bids", "https://localhost/bids",
            "https://county.example:8443/bids",
            "https://user:password@county.example/bids",
            "https://county.example/bids#old",
            "https://county.example.evil\\@other.example/bids",
            "https://county.example/%0aevil",
            "https://county.example/bids\nInjected",
            "https://county..example/bids",
            "https://county.example./bids",
            "https://county.example:broken/bids",
            "javascript:alert(1)",
        ):
            with self.subTest(url=url):
                self.assertFalse(source_config.valid_public_https_url(url))

    def test_unverified_and_malformed_direct_sources_not_counted(self):
        sources = [
            {"name": "Unverified", "mode": "direct_page",
             "url": "https://county.example/bids", "verified_url": False},
            {"name": "Unsafe", "mode": "direct_page",
             "url": "https://user:pw@county.example/bids", "verified_url": True},
            {"name": "Valid", "mode": "direct_page",
             "url": "https://county.example/bids", "verified_url": True},
        ]
        audit = audit_source_coverage.audit(sources)
        health = source_health.summarize(sources, {})
        self.assertEqual(audit["direct_configured"], 1)
        self.assertEqual(audit["invalid_direct_configurations"], 2)
        self.assertEqual(health["counts"]["configured_direct"], 1)
        self.assertEqual(health["counts"]["not_configured"], 2)

    def test_malformed_staged_url_does_not_claim_official_staging(self):
        source = {"name": "Bad staged", "mode": "discovery_pending",
                  "candidate_official_url": "http://county.example/bids"}
        self.assertEqual(audit_source_coverage.audit([source])["official_urls_staged"], 0)
        self.assertEqual(source_health.classify(source, "")["direct_state"], "not_configured")

    def test_unverified_and_unsafe_direct_urls_never_fetched(self):
        for url, verified in (
            ("https://county.example/bids", False),
            ("http://county.example/bids", True),
            ("https://user:pw@county.example/bids", True),
        ):
            source = {"name": "Synthetic", "mode": "direct_page",
                      "url": url, "verified_url": verified}
            with self.subTest(url=url, verified=verified):
                with patch.object(scan, "scan_direct") as direct, patch.object(
                    scan, "scan_news", return_value=[]
                ) as news:
                    _, status, leads = scan.run(source)
                direct.assert_not_called()
                news.assert_called_once_with(source)
                self.assertIn("direct not configured", status)
                self.assertEqual(leads, [])

    def test_valid_direct_source_still_fetches(self):
        source = {"name": "Synthetic", "mode": "direct_page",
                  "url": "https://county.example/bids", "verified_url": True}
        with patch.object(scan, "scan_direct", return_value=([], "direct fetched")) as direct, patch.object(
            scan, "scan_news", return_value=[]
        ):
            _, status, leads = scan.run(source)
        direct.assert_called_once_with(source)
        self.assertIn("direct fetched", status)
        self.assertEqual(leads, [])

    def test_current_direct_inventory_remains_valid(self):
        import json
        sources = json.loads(scan.SOURCES.read_text(encoding="utf-8"))
        for source in sources:
            if source.get("mode") == "direct_page":
                with self.subTest(source=source["name"]):
                    self.assertTrue(source_config.direct_configured(source))


if __name__ == "__main__":
    unittest.main()
