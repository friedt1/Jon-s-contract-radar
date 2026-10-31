"""Official Williamsport procurement index staging; no live-bid assertions."""
import datetime as dt
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_source_coverage
import scan
import source_config
import source_health


class WilliamsportOfficialIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads(
            (Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
        cls.source = next(row for row in cls.sources
                          if row["name"] == "Williamsport City")

    def test_official_rfp_category_staged_without_false_monitoring(self):
        row = self.source
        self.assertEqual(row["mode"], "discovery_pending")
        self.assertEqual(row["url"], "")
        self.assertIs(row["verified_url"], False)
        self.assertEqual(
            row["candidate_official_url"],
            "https://cityofwilliamsport.org/news/document-category/request-for-proposal/")
        self.assertEqual(row["official_page_role"],
                         "mixed_rfp_index_and_archived_responses")
        self.assertIn("historical responses", row["activation_gate"])
        self.assertIn("robots", row["activation_gate"])
        self.assertIn("submission deadlines", row["activation_gate"])
        self.assertTrue(source_config.valid_public_https_url(
            row["candidate_official_url"]))
        self.assertFalse(source_config.direct_fetch_target(row))
        self.assertEqual(source_health.classify(row, "")["direct_state"],
                         "staged_official_url")
        with patch.object(scan, "scan_direct",
                          side_effect=AssertionError("staged source fetched")) as direct:
            with patch.object(scan, "scan_news", return_value=[]):
                _, status, leads = scan.run(row)
        direct.assert_not_called()
        self.assertEqual(leads, [])
        self.assertNotIn("direct fetched", status)

    def test_audit_preserves_all_sources_and_distinguishes_staged_from_active(self):
        audit = audit_source_coverage.audit(self.sources)
        self.assertEqual(audit["total"], 102)
        self.assertEqual(audit["direct_configured"], 18)
        self.assertEqual(audit["not_directly_monitored"], 84)
        self.assertGreaterEqual(audit["official_urls_staged"], 40)
        self.assertEqual(audit["discovery_required"], 84 - audit["official_urls_staged"])
        row = next(x for x in audit["sources"] if x["source"] == "Williamsport City")
        self.assertTrue(row["official_url_staged"])
        self.assertFalse(row["direct_configured"])

    def test_historical_or_unrelated_notices_not_live(self):
        today = dt.date(2026, 10, 30)
        self.assertFalse(scan.eligible(
            "Williamsport PA tree and stump removal bid due 09/30/2026",
            "Williamsport City", today=today))
        self.assertFalse(scan.eligible(
            "Williamsport City Hall property sale RFP due 11/20/2026",
            "Williamsport City", today=today))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due 11/19/2026",
            "Tioga County NY", today=today))


if __name__ == "__main__":
    unittest.main()
