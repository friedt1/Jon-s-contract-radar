"""Publisher-gateway regressions: official pages are not individual-bid monitors.

All cases are source configuration checks, not live bid fixtures.
"""
import json
import unittest
from unittest.mock import patch

import audit_source_coverage
import scan
import source_config
import source_health


UTILITY_GATEWAYS = (
    "NYSEG",
    "New York State DOT Region 9",
    "New York Power Authority",
    "FirstEnergy Penelec",
)


class UtilityGatewayStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads(scan.SOURCES.read_text(encoding="utf-8"))
        cls.by_name = {source["name"]: source for source in cls.sources}

    def test_official_gateways_remain_unmonitored(self):
        for name in UTILITY_GATEWAYS:
            with self.subTest(name=name):
                source = self.by_name[name]
                self.assertEqual(source["mode"], "discovery_pending")
                self.assertFalse(source["verified_url"])
                self.assertEqual(source["url"], "")
                self.assertTrue(source_config.valid_public_https_url(
                    source["candidate_official_url"]))
                self.assertTrue(source.get("official_page_role"))
                self.assertTrue(source.get("activation_gate"))
                self.assertFalse(source_config.direct_configured(source))
                self.assertFalse(source_config.direct_fetch_target(source))
                row = source_health.classify(
                    source, "indirect RSS error: RobotsDenied")
                self.assertEqual(row["direct_state"], "staged_official_url")
                self.assertEqual(row["direct_url"], "")

    def test_invitation_only_and_project_page_are_explicitly_labeled(self):
        firstenergy = self.by_name["FirstEnergy Penelec"]
        self.assertTrue(firstenergy["provider_access_required"])
        self.assertEqual(firstenergy["delegated_provider"], "Coupa")
        self.assertIn("does NOT publish", firstenergy["activation_gate"])
        nypa = self.by_name["New York Power Authority"]
        self.assertTrue(nypa["provider_access_required"])
        self.assertEqual(nypa["delegated_provider"], "SAP Ariba")
        self.assertIn("registration", nypa["activation_gate"])
        dot = self.by_name["New York State DOT Region 9"]
        self.assertIn("NOT an active contract", dot["official_page_role"])
        self.assertIn("not an individual", self.by_name["NYSEG"]["official_page_role"])

    def test_staging_does_not_increase_direct_coverage(self):
        coverage = audit_source_coverage.audit(self.sources)
        self.assertEqual(coverage["total"], 102)
        self.assertEqual(coverage["direct_configured"], 18)
        self.assertEqual(coverage["pending_direct"], 84)
        self.assertGreaterEqual(coverage["official_urls_staged"], len(UTILITY_GATEWAYS))

    def test_no_direct_requests_for_staged_gateways(self):
        for name in UTILITY_GATEWAYS:
            with self.subTest(name=name):
                with patch.object(scan, "scan_direct") as direct, patch.object(
                    scan, "scan_news", return_value=[]
                ):
                    _, status, leads = scan.run(self.by_name[name])
                direct.assert_not_called()
                self.assertIn("direct not configured", status)
                self.assertEqual(leads, [])


if __name__ == "__main__":
    unittest.main()
