"""Offline gates for verified Pennsylvania procurement entrypoints.

An official business office or supplier-registration page is not a permitted
individual-notice monitor. Erie/Owego examples remain negative fixtures.
"""
import datetime as dt
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_source_coverage
import scan
import source_config
import source_health


GATEWAYS = {
    "Sayre Area School District":
        "https://www.sayresd.org/page/business/",
    "Mansfield University":
        "https://www.commonwealthu.edu/offices-directory/procurement-shared-services",
    "Pennsylvania American Water":
        "https://amwater.com/paaw/about-us/Suppliers-Vendors/supplier-diversity",
}
ACCESS_REQUIRED = {"Mansfield University", "Pennsylvania American Water"}


class PennsylvaniaProcurementGatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads(
            (Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
        cls.by_name = {row["name"]: row for row in cls.sources}

    def test_official_gateway_urls_are_staged_not_activated(self):
        for name, url in GATEWAYS.items():
            with self.subTest(name=name):
                row = self.by_name[name]
                self.assertEqual(row["mode"], "discovery_pending")
                self.assertEqual(row["url"], "")
                self.assertIs(row["verified_url"], False)
                self.assertEqual(row["candidate_official_url"], url)
                self.assertTrue(source_config.valid_public_https_url(url))
                self.assertIn("NOT", row["official_page_role"])
                for required in ("robots/terms", "scope", "deadline", "open status"):
                    self.assertIn(required, row["activation_gate"])
                self.assertFalse(source_config.direct_configured(row))
                self.assertFalse(source_config.direct_fetch_target(row))
                health = source_health.classify(row, "")
                self.assertEqual(health["direct_state"], "staged_official_url")
                self.assertEqual(health["direct_url"], "")
                self.assertEqual(health["staged_provider_access_required"],
                                 name in ACCESS_REQUIRED)

    def test_supplier_registration_is_not_a_public_notice_feed(self):
        for name in ACCESS_REQUIRED:
            with self.subTest(name=name):
                row = self.by_name[name]
                self.assertIs(row["provider_access_required"], True)
                self.assertIn("registration", row["activation_gate"].lower())
        self.assertIn("SourcePoint", self.by_name["Mansfield University"]["delegated_provider"])
        self.assertIn("404", self.by_name["Pennsylvania American Water"]["activation_gate"])

    def test_staged_pages_are_not_directly_fetched_or_published(self):
        for name in GATEWAYS:
            with self.subTest(name=name):
                with (patch.object(scan, "scan_direct",
                                   side_effect=AssertionError("staged direct fetch")),
                      patch.object(scan, "scan_news", return_value=[])):
                    _, status, leads = scan.run(self.by_name[name])
                self.assertEqual(leads, [])
                self.assertNotIn("direct fetched", status)

    def test_coverage_distinguishes_staging_from_monitoring(self):
        audit = audit_source_coverage.audit(self.sources)
        self.assertEqual(audit["total"], 102)
        self.assertEqual(audit["direct_configured"], 18)
        self.assertEqual(audit["not_directly_monitored"], 84)
        self.assertEqual(audit["official_urls_staged"], 66)
        self.assertEqual(audit["discovery_required"], 19)
        for name in GATEWAYS:
            entry = next(x for x in audit["sources"] if x["source"] == name)
            self.assertTrue(entry["official_url_staged"])
            self.assertFalse(entry["direct_fetch_target"])
            self.assertEqual(entry["staged_provider_access_required"],
                             name in ACCESS_REQUIRED)
            if name in ACCESS_REQUIRED:
                self.assertIn("registration/authorization required", entry["status"])
        self.assertGreaterEqual(audit["staged_provider_access_required"], 2)
        health = source_health.summarize(self.sources, {})
        self.assertGreaterEqual(health["counts"]["staged_provider_access_required"], 2)

    def test_historical_erie_and_unrelated_owego_not_live(self):
        today = dt.date(2026, 11, 1)
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            "PennBid platform", today=today))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            "Tioga County NY", today=today))


if __name__ == "__main__":
    unittest.main()
