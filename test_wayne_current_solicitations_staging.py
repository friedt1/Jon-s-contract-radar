"""Wayne County's post-transition procurement gateway is staged, not a bid feed.

Official county source verified 2026-11-02. All network fixtures here are
synthetic and never publish or seed an opportunity.
"""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_source_coverage
import probe_staged_sources as staged
import scan
import source_config
import source_health


OFFICIAL = "https://www.waynecountyny.gov/922/Solicitations-After-192026"


class WayneCurrentSolicitationsStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads(
            (Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
        cls.source = next(row for row in cls.sources
                          if row["name"] == "Wayne County")

    def test_official_current_gateway_remains_unactivated(self):
        row = self.source
        self.assertEqual(len(self.sources), 102)
        self.assertEqual(row["candidate_official_url"], OFFICIAL)
        self.assertTrue(source_config.valid_public_https_url(OFFICIAL))
        self.assertEqual(row["mode"], "discovery_pending")
        self.assertEqual(row["url"], "")
        self.assertIs(row["verified_url"], False)
        self.assertEqual(row["delegated_provider"], "OpenGov")
        self.assertIs(row["provider_access_required"], True)
        self.assertIn("iframe", row["activation_gate"])
        self.assertIn("per-notice", row["activation_gate"])
        self.assertFalse(source_config.direct_fetch_target(row))
        self.assertEqual(source_health.classify(row, "")["direct_state"],
                         "staged_official_url")

    def test_county_gateway_is_not_open_gov_notice_extraction(self):
        html = (
            "<h1>Solicitations After 1/9/2026</h1>"
            "<p>Wayne County has partnered with OpenGov. "
            "Below is a list of our current solicitations.</p>"
            '<iframe src="https://procurement.opengov.com/portal/co-wayne-ny-us">'
            "</iframe>"
        )
        calls = []

        def fetch(url, binary=False):
            calls.append(url)
            return html, "text/html", url

        report = staged.build([self.source], fetch=fetch)
        row = report["probes"][0]
        self.assertEqual(calls, [OFFICIAL])
        self.assertEqual(row["state"],
                         "listing_reachable_external_provider_access_required")
        self.assertTrue(row["listing_retrieved"])
        self.assertFalse(row["individual_notice_retrieved"])
        self.assertEqual(row["individual_records_discovered"], 0)
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertNotIn("opportunities", report)

    def test_staged_gateway_is_not_a_live_scan_target(self):
        with patch.object(scan, "scan_direct",
                          side_effect=AssertionError("gateway fetched")) as direct:
            with patch.object(scan, "scan_news", return_value=[]):
                _, _status, leads = scan.run(self.source)
        direct.assert_not_called()
        self.assertEqual(leads, [])
        audit = audit_source_coverage.audit(self.sources)
        self.assertEqual(audit["total"], 102)
        self.assertEqual(audit["direct_configured"], 18)
        self.assertEqual(audit["not_directly_monitored"], 84)
        self.assertFalse(next(row for row in audit["sources"]
                              if row["source"] == "Wayne County")["direct_configured"])

    def test_historical_erie_and_unrelated_owego_not_live(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal sealed bid due October 28, 2026",
            today=staged.dt.date(2026, 11, 2)))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            today=staged.dt.date(2026, 11, 2)))


if __name__ == "__main__":
    unittest.main()
