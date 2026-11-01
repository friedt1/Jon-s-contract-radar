"""Synthetic regressions for a shared Google News RSS robots/access failure.

No real solicitation is fetched, published, or labeled open by these tests.
"""
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import scan
import source_diagnostics
import source_health


class SharedNewsProviderTests(unittest.TestCase):
    def test_preflight_uses_the_exact_per_source_news_url(self):
        src = {"name": "Tioga County NY", "discovery_query": "Tioga County procurement"}
        url = scan.news_url(src)
        parsed = urlsplit(url)
        self.assertEqual((parsed.scheme, parsed.netloc, parsed.path),
                         ("https", "news.google.com", "/rss/search"))
        self.assertIn("Tioga County procurement", parse_qs(parsed.query)["q"][0])

    def test_provider_refusal_skips_news_without_suppressing_direct_scan(self):
        src = {"name": "Tioga County NY", "mode": "direct_page",
               "verified_url": True, "url": "https://county.example/bids"}
        with patch.object(scan, "scan_direct", return_value=([], "direct fetched; 1 listing pages")) as direct, \
             patch.object(scan, "scan_news", side_effect=AssertionError("disallowed request")) as news:
            name, status, leads = scan.run(
                src, news_access=(False, "robots disallows requested path"))
        self.assertEqual(name, src["name"])
        direct.assert_called_once_with(src)
        news.assert_not_called()
        self.assertIn("direct fetched", status)
        self.assertIn("indirect RSS provider unavailable (Google News)", status)
        self.assertNotIn("indirect RSS error: RobotsDenied", status)
        self.assertEqual(leads, [])

    def test_unknown_provider_policy_fails_closed_without_claiming_publisher_denial(self):
        src = {"name": "School district", "mode": "discovery_pending"}
        with patch.object(scan, "scan_news", side_effect=AssertionError("must not fetch")) as news:
            _, status, leads = scan.run(
                src, news_access=(False, "robots policy unavailable: TimeoutError"))
        news.assert_not_called()
        self.assertIn("Google News", status)
        self.assertIn("TimeoutError", status)
        self.assertNotIn("direct blocked", status)
        self.assertEqual(leads, [])

    def test_allowed_provider_still_uses_normal_news_discovery(self):
        src = {"name": "County", "mode": "discovery_pending"}
        with patch.object(scan, "scan_news", return_value=[]) as news:
            _, status, leads = scan.run(src, news_access=(True, "robots permits requested path"))
        news.assert_called_once_with(src)
        self.assertIn("indirect RSS ok; 0 candidates", status)
        self.assertEqual(leads, [])

    def test_health_and_diagnostics_count_one_shared_provider_not_publisher_blocks(self):
        src = {"name": "Tioga County NY", "mode": "discovery_pending"}
        status = ("indirect RSS provider unavailable (Google News): "
                  "robots disallows requested path")
        health = source_health.summarize([src], {src["name"]: status})
        self.assertEqual(health["sources"][0]["indirect_state"], "provider_unavailable")
        self.assertEqual(health["counts"]["indirect_provider_unavailable_targets"], 1)
        self.assertEqual(health["counts"]["indirect_robots_blocked"], 0)
        report = source_diagnostics.report({
            "source_status": {src["name"]: status},
            "source_health": health,
            "source_coverage": {"total_targets": 1, "expected_source_names": [src["name"]]},
            "opportunities": [],
        })
        self.assertTrue(report["sources"][0]["indirect_shared_provider_unavailable"])
        self.assertTrue(report["sources"][0]["indirect_error"])
        self.assertFalse(report["sources"][0]["direct_error"])
        self.assertFalse(report["sources"][0]["error"])
        self.assertEqual(report["verified_open_opportunities"], 0)


if __name__ == "__main__":
    unittest.main()
