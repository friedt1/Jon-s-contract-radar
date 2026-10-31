"""Athens district official bid entrypoint is not an activated monitor."""
import json
from pathlib import Path
import unittest

import audit_source_coverage
import source_health


class AthensSchoolBidStagingTests(unittest.TestCase):
    def test_official_bid_page_is_staged_without_activation(self):
        sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        self.assertEqual(len(sources), 102)
        source = next(x for x in sources
                      if x["name"] == "Athens Area School District")
        self.assertEqual(source["candidate_official_url"],
                         "https://www.athensasd.k12.pa.us/PublicBidNotices.aspx")
        self.assertEqual(source["mode"], "discovery_pending")
        self.assertFalse(source["url"])
        self.assertFalse(source["verified_url"])
        self.assertIn("individual notice", source["activation_gate"])
        self.assertEqual(source_health.classify(source, "")["direct_state"],
                         "staged_official_url")
        audit = audit_source_coverage.audit(sources)
        row = next(x for x in audit["sources"]
                   if x["source"] == "Athens Area School District")
        self.assertTrue(row["official_url_staged"])
        self.assertFalse(row["direct_fetch_target"])
        self.assertFalse(row["direct_configured"])

    def test_empty_visible_page_is_not_an_open_contract(self):
        # The publisher's page had a Public Bid Notice heading but no
        # individual bid notices in the visible HTML on October 31.
        # This synthetic sample is NOT a live scan or a claim of no bids.
        import scan
        sample = "<h1>Public Bid Notice</h1><p>Business Office</p>"
        self.assertIsNone(scan.category(sample))
        self.assertFalse(scan.eligible(sample, "Athens Area School District"))


if __name__ == "__main__":
    unittest.main()
