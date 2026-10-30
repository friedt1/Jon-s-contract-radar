"""Offline staging regression: legal notices are not verified tree-service bids."""
import datetime as dt
import json
from pathlib import Path
import unittest

from audit_source_coverage import audit
import scan
import source_health


class WatkinsGlenOfficialNoticesTests(unittest.TestCase):
    def test_verified_official_notices_remain_staged_until_permitted_detail_ingestion(self):
        sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        self.assertEqual(len(sources), 102)
        row = next(s for s in sources if s["name"] == "Village of Watkins Glen")
        self.assertEqual(row["mode"], "discovery_pending")
        self.assertFalse(row["verified_url"])
        self.assertFalse(row["url"])
        self.assertEqual(row["candidate_official_url"],
                         "https://watkinsglen.us/public-legal-noticeshearings.php")
        self.assertIn("individual bid notices", row["activation_gate"])
        coverage = audit([row])
        self.assertEqual(coverage["official_urls_staged"], 1)
        self.assertEqual(coverage["direct_fetch_targets"], 0)
        self.assertEqual(coverage["not_directly_monitored"], 1)
        health = source_health.classify(row, "")
        self.assertEqual(health["direct_state"], "staged_official_url")
        self.assertFalse(health["direct_url"])

    def test_non_procurement_and_expired_regressions_cannot_become_live_bids(self):
        today = dt.date(2026, 10, 30)
        for notice in (
            "Village of Watkins Glen tree removal permit application",
            "Village of Watkins Glen 2026-2027 final draft budget hearing April 30 2026",
            "Erie tree and stump removal bid due October 28, 2026",
            "Owego building demolition bid due November 13, 2026",
        ):
            with self.subTest(notice=notice):
                self.assertFalse(scan.eligible(notice, today=today))


if __name__ == "__main__":
    unittest.main()
