"""Wellsboro Borough official bid index staging; synthetic offline probes only."""
import datetime as dt
import json
from pathlib import Path
import unittest

import probe_staged_sources as staged
import scan


URL = "https://www.wellsboroborough.com/blank-12"
NOW = dt.datetime(2026, 10, 30, 6, 30, tzinfo=dt.timezone.utc)


def wellsboro():
    sources = json.loads((Path(__file__).parent / "sources.json").read_text())
    assert len(sources) == 102
    return next(row for row in sources if row["name"] == "Wellsboro Borough")


class WellsboroStagingTests(unittest.TestCase):
    def test_official_bid_index_is_staged_not_a_live_feed(self):
        row = wellsboro()
        self.assertEqual(row["candidate_official_url"], URL)
        self.assertEqual(row["mode"], "discovery_pending")
        self.assertEqual(row["url"], "")
        self.assertFalse(row["verified_url"])
        self.assertIn("individual", row["activation_gate"])

    def test_explicit_empty_listing_is_scoped_to_visible_page(self):
        html = "<html><h1>Bids &amp; Bid Packets</h1><h2>No Current Open Bids</h2></html>"
        calls = []

        def fetch(url, binary=False):
            calls.append((url, binary))
            return html, "text/html", url

        row = staged.probe(wellsboro(), fetch=fetch, now=NOW)
        self.assertEqual(row["state"], "listing_reachable_no_open_bids_reported")
        self.assertIn("other channels", row["section_note"])
        self.assertTrue(row["listing_retrieved"])
        self.assertFalse(row["individual_notice_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertEqual(row["individual_samples_attempted"], 0)
        self.assertEqual(calls, [(URL, False)])
        self.assertNotIn("opportunities", row)

    def test_empty_banner_with_individual_pdf_is_not_authoritative(self):
        html = ('<h1>No Current Open Bids</h1>'
                '<a href="/images/2026-tree-removal.pdf">Tree Removal Bid Packet</a>')
        row = staged.probe(wellsboro(), fetch=lambda url: (
            html, "text/html", url), now=NOW)
        self.assertEqual(row["state"], "listing_reachable_adapter_required")
        self.assertNotIn("section_note", row)
        self.assertFalse(row["direct_monitoring_activated"])

    def test_generic_bid_heading_without_explicit_empty_message(self):
        row = staged.probe(wellsboro(), fetch=lambda url: (
            "<h1>Open Bids & Bid Packets</h1>", "text/html", url), now=NOW)
        self.assertEqual(row["state"], "listing_reachable_adapter_required")
        self.assertNotIn("section_note", row)

    def test_provider_delegation_overrides_empty_listing(self):
        html = ("<h1>No Current Open Bids</h1>"
                "<p>All bids and solicitation packets are on BidNet.</p>")
        row = staged.probe(wellsboro(), fetch=lambda url: (
            html, "text/html", url), now=NOW)
        self.assertEqual(row["state"],
                         "listing_reachable_external_provider_access_required")
        self.assertNotIn("section_note", row)
        self.assertFalse(row["direct_monitoring_activated"])

    def test_historical_tree_bid_and_owego_demolition_not_live(self):
        # Official Wellsboro 2025 street-tree PDFs are historical evidence,
        # NOT an active 2026 solicitation. Erie and Owego remain regression
        # examples only, never seeded into any feed.
        old = "Bids due November 21, 2025 for street tree removal"
        self.assertEqual(scan.category(old), "Tree removal")
        self.assertFalse(scan.eligible(old, today=NOW.date()))
        self.assertEqual(scan.category("Owego building demolition"), None)
        result = staged.build([wellsboro()], fetch=lambda url: (
            "<h1>No Current Open Bids</h1>", "text/html", url), now=NOW)
        self.assertEqual(result["staged_entrypoints"], 1)
        self.assertNotIn("opportunities", result)


if __name__ == "__main__":
    unittest.main()
