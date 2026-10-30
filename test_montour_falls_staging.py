"""Montour Falls source staging and scoped RFP diagnostics (offline only)."""
import datetime as dt
import json
from pathlib import Path
import unittest

import probe_staged_sources as staged
import scan


URL = "https://www.villageofmontourfalls.gov/"
NOW = dt.datetime(2026, 10, 30, 5, 35, tzinfo=dt.timezone.utc)


def montour():
    sources = json.loads((Path(__file__).parent / "sources.json").read_text())
    assert len(sources) == 102
    return next(s for s in sources if s["name"] == "Village of Montour Falls")


class MontourFallsStagingTests(unittest.TestCase):
    def test_official_rfp_section_is_staged_not_direct(self):
        row = montour()
        self.assertEqual(row["candidate_official_url"], URL)
        self.assertEqual(row["mode"], "discovery_pending")
        self.assertEqual(row["url"], "")
        self.assertFalse(row["verified_url"])
        self.assertIn("individual notice", row["activation_gate"])

    def test_explicit_empty_rfp_section_is_not_sitewide_no_bids(self):
        html = ("<h1>Village of Montour Falls</h1>"
                "<h2>Request for Proposals:</h2><p>None at this time.</p>"
                "<h2>Public Notice</h2><p>Village board meeting.</p>")
        calls = []
        def fetch(url, binary=False):
            calls.append(url)
            return html, "text/html", url

        row = staged.probe(montour(), fetch=fetch, now=NOW)
        self.assertEqual(row["state"], "listing_reachable_rfp_section_reports_none")
        self.assertIn("other bid channels", row["section_note"])
        self.assertTrue(row["listing_retrieved"])
        self.assertFalse(row["individual_notice_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertEqual(row["individual_samples_attempted"], 0)
        self.assertEqual(calls, [URL])
        self.assertNotIn("opportunities", row)

    def test_generic_rfp_heading_does_not_claim_empty_section(self):
        html = "<h2>Request for Proposals:</h2><p>Tree trimming RFP deadline November 30, 2026.</p>"
        row = staged.probe(montour(), fetch=lambda url: (html, "text/html", url), now=NOW)
        self.assertEqual(row["state"], "listing_reachable_adapter_required")
        self.assertNotIn("section_note", row)
        self.assertFalse(row["direct_monitoring_activated"])

    def test_provider_delegation_takes_precedence_over_empty_rfp_section(self):
        html = ("<h2>Request for Proposals:</h2><p>None at this time.</p>"
                "<p>All bids and solicitation packets are on BidNet.</p>")
        row = staged.probe(montour(), fetch=lambda url: (html, "text/html", url), now=NOW)
        self.assertEqual(row["state"], "listing_reachable_external_provider_access_required")
        self.assertFalse(row["direct_monitoring_activated"])

    def test_erie_tree_stump_and_owego_demolition_not_seeded(self):
        self.assertEqual(scan.category("Erie tree and stump removal"), "Tree removal")
        self.assertIsNone(scan.category("Owego building demolition"))
        result = staged.build([montour()], fetch=lambda url: (
            "<h2>Request for Proposals:</h2><p>None at this time.</p>",
            "text/html", url), now=NOW)
        self.assertEqual(result["staged_entrypoints"], 1)
        self.assertNotIn("opportunities", result)


if __name__ == "__main__":
    unittest.main()
