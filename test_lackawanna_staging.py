"""Lackawanna PA official listing staging is not authorized live monitoring."""
import json
from pathlib import Path
import unittest

import probe_staged_sources
import source_health


class LackawannaStagingTests(unittest.TestCase):
    def test_official_rfp_listing_is_staged_not_direct(self):
        sources = json.loads((Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
        self.assertEqual(len(sources), 102)
        self.assertEqual(len({s["name"] for s in sources}), 102)
        source = next(s for s in sources if s["name"] == "Lackawanna County")
        self.assertEqual(source["mode"], "discovery_pending")
        self.assertIs(source["verified_url"], False)
        self.assertEqual(source["url"], "")
        self.assertEqual(
            source["candidate_official_url"],
            "https://www.lackawannacounty.org/government/departments/rfp_rfq.php",
        )
        self.assertIn("HTTP 404", source["activation_gate"])
        row = source_health.classify(source, "indirect RSS error: RobotsDenied")
        self.assertEqual(row["direct_state"], "staged_official_url")
        self.assertEqual(row["direct_url"], "")
        self.assertEqual(row["indirect_state"], "robots_blocked")

    def test_listing_access_does_not_fetch_unverified_detail_links(self):
        # The official index can list expired/unrelated bids and stale detail
        # URLs. Its existence is NOT evidence of a working extraction adapter.
        source = {
            "name": "Lackawanna County",
            "mode": "discovery_pending",
            "candidate_official_url":
                "https://www.lackawannacounty.org/government/departments/rfp_rfq.php",
            "activation_gate": "Verify individual detail links and publisher terms",
        }
        calls = []

        def fake_fetch(url, binary=False):
            calls.append((url, binary))
            if binary:
                raise AssertionError("unapproved individual detail request")
            return (
                '<table><tr><td><a href="bid_detail_T17_R255.php">'
                'Historical unrelated property-data RFP</a></td>'
                '<td>September 30, 2026</td></tr></table>',
                "text/html", url,
            )

        result = probe_staged_sources.probe(source, fetch=fake_fetch)
        self.assertEqual(result["state"], "listing_reachable_adapter_required")
        self.assertTrue(result["listing_retrieved"])
        self.assertFalse(result["individual_notice_retrieved"])
        self.assertFalse(result["direct_monitoring_activated"])
        self.assertNotIn("opportunities", result)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
