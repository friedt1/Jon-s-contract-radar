"""PennDOT ECMS official gateway staging; no live bids or automated portal access."""
import datetime as dt
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_source_coverage
import scan
import source_config
import source_health


ECMS = "https://www.ecmssyst.penndot.pa.gov/ECMS/"


class PennDotEcmsStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads(
            (Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
        cls.row = next(x for x in cls.sources if x["name"] == "PennDOT District 4")

    def test_statewide_official_gateway_is_not_direct_district_monitoring(self):
        row = self.row
        self.assertEqual(len(self.sources), 102)
        self.assertEqual(len({x["name"] for x in self.sources}), 102)
        self.assertEqual(row["candidate_official_url"], ECMS)
        self.assertTrue(source_config.valid_public_https_url(ECMS))
        self.assertEqual(row["mode"], "discovery_pending")
        self.assertEqual(row["url"], "")
        self.assertIs(row["verified_url"], False)
        self.assertTrue(row["require_local_evidence"])
        self.assertIn("statewide", row["official_page_role"])
        for word in ("guest", "robots/terms", "District 4",
                     "submission deadline", "before activation"):
            self.assertIn(word.lower(), row["activation_gate"].lower())
        self.assertFalse(source_config.direct_configured(row))
        self.assertFalse(source_config.direct_fetch_target(row))
        self.assertEqual(source_health.classify(row, "")["direct_state"],
                         "staged_official_url")

    def test_staged_gateway_does_not_fetch_or_publish_notices(self):
        with (patch.object(scan, "scan_direct",
                           side_effect=AssertionError("staged portal fetched")) as direct,
              patch.object(scan, "scan_news", return_value=[])):
            _, status, leads = scan.run(self.row)
        direct.assert_not_called()
        self.assertEqual(leads, [])
        self.assertNotIn("direct fetched", status)
        audit = audit_source_coverage.audit(self.sources)
        self.assertEqual(audit["total"], 102)
        self.assertEqual(audit["direct_configured"], 18)
        self.assertEqual(audit["not_directly_monitored"], 84)
        self.assertGreaterEqual(audit["official_urls_staged"], 43)
        self.assertEqual(audit["discovery_required"],
                         84 - audit["official_urls_staged"])

    def test_erie_expired_and_owego_demolition_are_not_live(self):
        today = dt.date(2026, 10, 31)
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            "PennBid platform", today=today))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            "Tioga County NY", today=today))


if __name__ == "__main__":
    unittest.main()
