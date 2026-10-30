"""Offline regression checks for outbound staged procurement links.

Only the official entrypoint is fetched. Neither an external portal nor
an externally hosted PDF is opened, activated, or advertised as a live bid.
"""
import unittest

import probe_staged_sources as staged

SOURCE = {
    "name": "City of Hornell",
    "candidate_official_url": "https://www.cityofhornell.gov/upcoming-bid-projects",
    "mode": "discovery_pending",
    "activation_gate": "Review publisher permissions and per-notice extraction.",
}


def check(html):
    calls = []

    def fetch(url, binary=False):
        calls.append((url, binary))
        return html, "text/html", url

    row = staged.probe(SOURCE, fetch=fetch)
    assert calls == [(SOURCE["candidate_official_url"], False)], calls
    assert not row["individual_notice_retrieved"]
    assert not row["direct_monitoring_activated"]
    return row


class OutboundStagedLinkTests(unittest.TestCase):
    def test_protocol_relative_opengov_link_requires_provider_access(self):
        row = check('<h1>Upcoming Bid Projects</h1>'
                    '<a href="//procurement.opengov.com/portal/city">View Bids</a>')
        self.assertEqual(row["state"],
                         "listing_reachable_external_provider_access_required")

    def test_provider_lookalike_does_not_count_as_provider(self):
        row = check('<h1>Upcoming Bid Projects</h1>'
                    '<a href="https://procurement.opengov.com.attacker.example/bids">'
                    'View Bids</a>')
        self.assertEqual(row["state"], "listing_reachable_adapter_required")

    def test_protocol_relative_cdn_pdf_with_query_is_diagnostic_only(self):
        row = check('<h1>Upcoming Bid Projects</h1>'
                    '<a href="//files.example.org/packets/trees.pdf?version=2">'
                    'Bid packet</a>')
        self.assertEqual(row["state"],
                         "listing_reachable_off_host_documents_review_required")
        self.assertEqual(row["off_host_pdf_hosts_unverified"],
                         ["files.example.org"])

    def test_same_host_pdf_not_reported_as_external(self):
        row = check('<h1>Upcoming Bid Projects</h1>'
                    '<a href="/packets/trees.pdf">Bid packet</a>')
        self.assertEqual(row["state"], "listing_reachable_adapter_required")
        self.assertNotIn("off_host_pdf_hosts_unverified", row)

    def test_insecure_pdf_is_not_treated_as_permitted_external_document(self):
        row = check('<h1>Upcoming Bid Projects</h1>'
                    '<a href="http://files.example.org/bid.pdf">Bid packet</a>')
        self.assertEqual(row["state"], "listing_reachable_adapter_required")
        self.assertNotIn("off_host_pdf_hosts_unverified", row)

    def test_malformed_link_does_not_break_empty_listing_diagnostic(self):
        row = check('<h1>Bid Postings</h1>'
                    '<p>There are no open bids at this time.</p>'
                    '<a href="https://[invalid">Broken link</a>')
        self.assertEqual(row["state"], "listing_reachable_no_open_bids_reported")
        self.assertNotIn("error_type", row)


if __name__ == "__main__":
    unittest.main()
