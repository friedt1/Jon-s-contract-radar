"""Town of Union official bid index staging and provider-access diagnostics.

Fixtures are historical/synthetic; this test never publishes a solicitation.
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


UNION_URL = "https://www.townofunion.com/government/public_notices/bid_opportunities.php"


class TownOfUnionOfficialStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads(
            (Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
        cls.source = next(row for row in cls.sources
                          if row["name"] == "Town of Union NY")

    def test_historical_official_index_is_staged_not_active(self):
        self.assertEqual(len(self.sources), 102)
        self.assertEqual(len({row["name"] for row in self.sources}), 102)
        row = self.source
        self.assertEqual(row["mode"], "discovery_pending")
        self.assertEqual(row["url"], "")
        self.assertIs(row["verified_url"], False)
        self.assertEqual(row["candidate_official_url"], UNION_URL)
        self.assertEqual(row["official_page_role"],
                         "stale_public_bid_index_detail_access_unverified")
        for marker in ("2024", "HTTP 403", "robots", "before activation"):
            self.assertIn(marker, row["activation_gate"])
        self.assertTrue(source_config.valid_public_https_url(UNION_URL))
        self.assertFalse(source_config.direct_configured(row))
        self.assertFalse(source_config.direct_fetch_target(row))
        self.assertEqual(source_health.classify(row, "")["direct_state"],
                         "staged_official_url")
        with patch.object(scan, "scan_direct",
                          side_effect=AssertionError("staged source fetched")) as direct, \\
             patch.object(scan, "scan_news", return_value=[]):
            _, status, leads = scan.run(row)
        direct.assert_not_called()
        self.assertEqual(leads, [])
        self.assertNotIn("direct fetched", status)

    def test_coverage_counts_distinguish_staged_from_monitored(self):
        audit = audit_source_coverage.audit(self.sources)
        self.assertEqual(audit["total"], 102)
        self.assertEqual(audit["direct_configured"], 18)
        self.assertEqual(audit["not_directly_monitored"], 84)
        self.assertEqual(audit["official_urls_staged"], 41)
        self.assertEqual(audit["discovery_required"], 43)
        row = next(x for x in audit["sources"] if x["source"] == "Town of Union NY")
        self.assertTrue(row["official_url_staged"])
        self.assertFalse(row["direct_fetch_target"])

    def test_provider_approval_remains_blocker_despite_old_robots_error(self):
        gateway = {
            "name": "Example delegated county",
            "mode": "direct_page",
            "url": "https://example.gov/bids",
            "verified_url": True,
            "provider_access_required": True,
            "delegated_provider": "Provider requiring approved access",
        }
        stale = "direct blocked by robots policy: disallowed"
        health = source_health.classify(gateway, stale)
        self.assertEqual(health["direct_state"], "access_required")
        self.assertTrue(health["provider_access_required"])
        self.assertIn("robots policy", health["diagnostic"])
        # Ordinary non-provider pages still report a robots block.
        ordinary = {**gateway, "provider_access_required": False,
                    "delegated_provider": ""}
        self.assertEqual(source_health.classify(ordinary, stale)["direct_state"],
                         "robots_blocked")

    def test_expired_erie_and_unrelated_owego_stay_excluded(self):
        today = dt.date(2026, 10, 31)
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            "PennBid platform", today=today))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            "Tioga County NY", today=today))


if __name__ == "__main__":
    unittest.main()
