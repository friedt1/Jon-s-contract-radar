"""Sullivan PA official notices are staged, never counted as live contracts."""
import json
from pathlib import Path
import unittest

import probe_staged_sources
import source_health


class SullivanPAStagingTests(unittest.TestCase):
    def test_official_public_notices_staged_not_activated(self):
        sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        self.assertEqual(len(sources), 102)
        src = next(s for s in sources if s["name"] == "Sullivan County PA")
        self.assertEqual(src["mode"], "discovery_pending")
        self.assertFalse(src["verified_url"])
        self.assertEqual(src["url"], "")
        self.assertEqual(src["candidate_official_url"],
                         "https://www.sullivancountypa.gov/public-notices")
        self.assertIn("historical bids", src["activation_gate"])
        self.assertIn("individual-notice adapter", src["activation_gate"])
        health = source_health.classify(src, "")
        self.assertEqual(health["direct_state"], "staged_official_url")
        self.assertEqual(health["direct_url"], "")

    def test_public_notices_index_does_not_create_bid_records(self):
        src = {
            "name": "Sullivan County PA",
            "mode": "discovery_pending",
            "candidate_official_url": "https://www.sullivancountypa.gov/public-notices",
            "activation_gate": "Individual notice validation required",
        }
        # This synthetic fixture contains a historical bid and unrelated news.
        # Fetching a broad index cannot establish an open contract.
        page = ("<h1>Public Notices</h1>"
                "<a href='/public-notices/2024/3/25/invitation-to-bid-mowing-and-trimming-2024'>"
                "Invitation to Bid: Mowing and Trimming 2024</a>"
                "<a href='/public-notices/job-opening'>Employment Opportunity</a>")
        row = probe_staged_sources.probe(
            src, fetch=lambda url: (page, "text/html", url))
        self.assertEqual(row["state"], "listing_reachable_adapter_required")
        self.assertTrue(row["listing_retrieved"])
        self.assertFalse(row["individual_notice_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertEqual(row["individual_records_discovered"], 0)


if __name__ == "__main__":
    unittest.main()
