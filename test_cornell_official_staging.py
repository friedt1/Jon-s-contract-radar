"""Cornell's publisher-linked construction index is staged, not live monitoring.

All regression examples are synthetic or explicitly unrelated Cornell notices.
No contract is manually inserted into the published feed.
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

INDEX = "https://fcs.cornell.edu/projects-out-to-bid"
DETAIL = "https://fcs.cornell.edu/bid-projects/replace-roofs-various-buildings-sucf-161061"


class CornellOfficialIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads(
            (Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
        cls.source = next(row for row in cls.sources if row["name"] == "Cornell University")

    def test_official_index_is_staged_not_fetched(self):
        row = self.source
        self.assertEqual(len(self.sources), 102)
        self.assertEqual(row["mode"], "discovery_pending")
        self.assertEqual(row["url"], "")
        self.assertIs(row["verified_url"], False)
        self.assertEqual(row["candidate_official_url"], INDEX)
        self.assertEqual(row["official_page_role"],
                         "official_construction_project_index_with_individual_pages")
        for phrase in ("robots/terms", "Trimble Unity", "NYSCR", "submission deadlines"):
            self.assertIn(phrase, row["activation_gate"])
        self.assertTrue(source_config.valid_public_https_url(INDEX))
        self.assertFalse(source_config.direct_configured(row))
        self.assertFalse(source_config.direct_fetch_target(row))
        self.assertEqual(source_health.classify(row, "")["direct_state"],
                         "staged_official_url")
        with (patch.object(scan, "scan_direct",
                           side_effect=AssertionError("staged source fetched")) as direct,
              patch.object(scan, "scan_news", return_value=[])):
            _, status, leads = scan.run(row)
        direct.assert_not_called()
        self.assertEqual(leads, [])
        self.assertNotIn("direct fetched", status)

    def test_coverage_is_not_inflated_by_staging(self):
        audit = audit_source_coverage.audit(self.sources)
        self.assertEqual(audit["total"], 102)
        self.assertEqual(audit["direct_configured"], 18)
        self.assertEqual(audit["not_directly_monitored"], 84)
        # Additional publisher gateways may be staged independently;
        # Cornell must remain staged, not counted as a direct fetch target.
        self.assertGreaterEqual(audit["official_urls_staged"], 42)
        self.assertEqual(audit["discovery_required"],
                         84 - audit["official_urls_staged"])
        row = next(x for x in audit["sources"] if x["source"] == "Cornell University")
        self.assertTrue(row["official_url_staged"])
        self.assertFalse(row["direct_fetch_target"])

    def test_bid_project_shape_is_individual_but_index_is_not(self):
        self.assertTrue(scan.is_individual_notice_link(DETAIL))
        self.assertFalse(scan.is_individual_notice_link(INDEX))
        self.assertFalse(scan.is_individual_notice_link(
            "https://fcs.cornell.edu/bid-projects/"))
        self.assertFalse(scan.is_individual_notice_link(DETAIL + "/award"))
        self.assertFalse(scan.is_individual_notice_link(DETAIL + ".pdf"))
        self.assertTrue(scan.redirect_preserves_notice(DETAIL, DETAIL + "/"))
        self.assertFalse(scan.redirect_preserves_notice(
            DETAIL, "https://fcs.cornell.edu/bid-projects/another-project"))
        self.assertFalse(scan.redirect_preserves_notice(
            DETAIL, "https://fcs.cornell.edu/projects-out-to-bid"))

    def test_bid_opening_is_not_automatically_a_submission_deadline(self):
        # Publisher detail pages distinguish bid opening from RFI/pre-bid dates.
        # Do not assume a bid-opening date is the submission cutoff.
        text = ("Pre-Bid Meeting 10/15/2026 at 10:00am "
                "Deadline for RFI 10/22/2026 at 12:00pm "
                "Bid Opening 11/03/2026 at 2:00pm")
        self.assertEqual(scan.deadline(text), "")
        self.assertFalse(scan.explicit_closing_passed(
            text, dt.datetime(2026, 11, 4, 12, tzinfo=dt.timezone.utc)))

    def test_unrelated_and_expired_regression_cases(self):
        today = dt.date(2026, 10, 31)
        self.assertIsNone(scan.category(
            "Replace roofs at Ives Hall; supporting HVAC, plumbing and asbestos work"))
        self.assertIsNone(scan.category(
            "Renovate Plant Science Building - Phase 2"))
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            "PennBid platform", today=today))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            "Tioga County NY", today=today))


if __name__ == "__main__":
    unittest.main()
