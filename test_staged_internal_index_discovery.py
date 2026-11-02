"""Offline discovery hints for staged publisher pages: never activate or fetch links."""
import unittest

import probe_staged_sources as staged

SOURCE = {
    "name": "Town of Erwin",
    "mode": "discovery_pending",
    "candidate_official_url": "https://town.example/",
    "official_page_role": "publisher_entrypoint_only",
    "activation_gate": "Find verified bid index and review permissions",
}


class StagedInternalIndexDiscoveryTests(unittest.TestCase):
    def test_labeled_same_host_bid_index_is_a_hint_only(self):
        calls = []
        html = (
            '<h1>Town Hall</h1>'
            '<a href="/Bids.aspx">Bids &amp; RFPs</a>'
            '<a href="/Bids.aspx#current">Bids &amp; RFPs</a>'
            '<a href="/procurement?session=private">Procurement</a>'
        )

        def fetch(url, binary=False):
            calls.append(url)
            return html, "text/html", url

        report = staged.build([SOURCE], fetch=fetch)
        row = report["probes"][0]
        self.assertEqual(calls, [SOURCE["candidate_official_url"]])
        self.assertEqual(
            row["official_bid_index_links_unverified"],
            [
                {"label": "Bids & RFPs", "url": "https://town.example/Bids.aspx"},
                {"label": "Procurement", "url": "https://town.example/procurement"},
            ],
        )
        self.assertEqual(report["unverified_bid_index_link_targets"], 1)
        self.assertEqual(report["unverified_bid_index_links_found"], 2)
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertFalse(row["individual_notice_retrieved"])
        self.assertNotIn("opportunities", report)

    def test_external_unsafe_and_archived_links_are_not_candidates(self):
        html = (
            '<h1>Purchasing</h1>'
            '<a href="https://procurement.opengov.com/portal/town">View Bids</a>'
            '<a href="https://town.example.evil.example/Bids.aspx">Bids</a>'
            '<a href="http://town.example/Bids.aspx">Bids</a>'
            '<a href="https://127.0.0.1/Bids.aspx">Bids</a>'
            '<a href="/Bid-Results">Bid Results</a>'
            '<a href="/past-bids">Past Bids</a>'
            '<a href="/procurement-policy">Procurement Policy</a>'
            '<a href="/docs/trees.pdf">Tree removal bids</a>'
            '<a href="/account/login">Bid Login</a>'
            '<a href="/">Bids</a>'
        )
        row = staged.probe(SOURCE, fetch=lambda url: (html, "text/html", url))
        self.assertNotIn("official_bid_index_links_unverified", row)
        self.assertFalse(row["direct_monitoring_activated"])

    def test_individual_rfps_and_bid_sheets_are_not_index_links(self):
        # A singular notice or document-center entry is not a bid index.
        html = (
            '<h1>Town News</h1>'
            '<a href="/2026/10/request-for-proposal">Request for Proposal</a>'
            '<a href="/post.php?id=42">Seeking RFQ for Contractors</a>'
            '<a href="/news/codes-rfp-2026">Codes RFP 2026</a>'
            '<a href="/news/city-hall-bid-sheet">City Hall IFB - Bid Sheet</a>'
            '<a href="/procurement">Procurement</a>'
        )
        row = staged.probe(SOURCE, fetch=lambda url: (html, "text/html", url))
        self.assertEqual(row["official_bid_index_links_unverified"], [
            {"label": "Procurement", "url": "https://town.example/procurement"}
        ])
        self.assertFalse(row["direct_monitoring_activated"])

    def test_individual_notice_urls_with_generic_bid_labels_are_not_indexes(self):
        # The label may say "Bids & RFPs" while the URL points to a
        # single CivicPlus notice, a numbered detail route, or a news post.
        # Stripping bidID would falsely suggest an authoritative index.
        html = (
            '<h1>Town Hall</h1>'
            '<a href="/Bids.aspx?bidID=416&token=private">Bids &amp; RFPs</a>'
            '<a href="/Bids.aspx?BID_ID=417">Current Bids</a>'
            '<a href="/procurement?notice-id=418">Procurement</a>'
            '<a href="/news/2026/11/tree-removal">Bids &amp; RFPs</a>'
            '<a href="/bids/419">Current Bids</a>'
            '<a href="/rfps/420">RFPs</a>'
            '<a href="/Bids.aspx?status=open">Current Bids</a>'
            '<a href="/procurement?category=services">Procurement</a>'
        )
        calls = []

        def fetch(url, binary=False):
            calls.append(url)
            return html, "text/html", url

        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(calls, [SOURCE["candidate_official_url"]])
        self.assertEqual(row["official_bid_index_links_unverified"], [
            {"label": "Current Bids", "url": "https://town.example/Bids.aspx"},
            {"label": "Procurement", "url": "https://town.example/procurement"},
        ])
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertFalse(row["individual_notice_retrieved"])

    def test_unlabeled_internal_links_are_not_inferred_as_bid_indexes(self):
        html = (
            '<h1>Town Hall</h1>'
            '<a href="/Bids.aspx">Learn More</a>'
            '<a href="/news">News</a>'
        )
        report = staged.build([SOURCE], fetch=lambda url: (html, "text/html", url))
        self.assertEqual(report["unverified_bid_index_link_targets"], 0)
        self.assertEqual(report["unverified_bid_index_links_found"], 0)
        self.assertNotIn("official_bid_index_links_unverified", report["probes"][0])


if __name__ == "__main__":
    unittest.main()
