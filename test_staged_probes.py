"""Offline staged-source probes: no real site or opportunity is asserted."""
import unittest
from unittest.mock import Mock

import probe_staged_sources as staged
import robots_policy


ENTRY = "https://county.example/Bids.aspx"
SOURCE = {
    "name": "Cortland County",
    "mode": "discovery_pending",
    "candidate_official_url": ENTRY,
    "activation_gate": "Terms review",
}


def listing():
    return ('<article><a href="/Bids.aspx?bidID=4">Tree removal bid</a>'
            '<p>Status: Closed</p></article>')


def detail():
    return ('<h1>Bid Title: Tree removal</h1><p>Bid Number: 4</p>'
            '<p>Description: Historical removal notice.</p><p>Status: Closed</p>')


class StagedProbeTests(unittest.TestCase):
    def test_historical_notice_proves_shape_not_live_opportunity(self):
        calls = []
        def fetch(url, binary=False):
            calls.append(url)
            if url == ENTRY:
                return listing(), "text/html", url
            return detail().encode(), "text/html", url
        result = staged.build([SOURCE], fetch=fetch, now=staged.dt.datetime(
            2026, 10, 29, tzinfo=staged.dt.timezone.utc))
        row = result["probes"][0]
        self.assertEqual(row["state"], "notice_format_confirmed_terms_review_required")
        self.assertTrue(row["individual_notice_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertEqual(row["sample_notice_status"], "closed")
        self.assertEqual(len(calls), 2)
        self.assertNotIn("opportunities", result)

    def test_robots_blocked_never_fetches_notice(self):
        fetch = Mock(side_effect=robots_policy.RobotsDenied("disallowed"))
        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["state"], "listing_robots_blocked")
        self.assertFalse(row["listing_retrieved"])
        self.assertEqual(fetch.call_count, 1)

    def test_no_bidid_is_not_marked_as_live_adapter(self):
        def fetch(url, binary=False):
            return "<p>Purchasing office</p>", "text/html", url
        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["state"], "listing_reachable_no_bidid_records")
        self.assertFalse(row["direct_monitoring_activated"])

    def test_non_civicplus_requires_separate_adapter(self):
        other = dict(SOURCE, name="Allegany County")
        row = staged.probe(other, fetch=lambda url: ("<h1>County bids</h1>", "text/html", url))
        self.assertEqual(row["state"], "listing_reachable_adapter_required")

    def test_redirect_to_homepage_does_not_prove_individual_notice(self):
        def fetch(url, binary=False):
            if url == ENTRY:
                return listing(), "text/html", url
            return detail().encode(), "text/html", ENTRY
        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["state"], "individual_notice_redirect_or_type_mismatch")
        self.assertFalse(row["individual_notice_retrieved"])

    def test_detail_robots_denial_is_distinct_from_listing_denial(self):
        def fetch(url, binary=False):
            if url == ENTRY:
                return listing(), "text/html", url
            raise robots_policy.RobotsDenied("detail disallowed")
        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["state"], "individual_notice_robots_blocked")
        self.assertTrue(row["listing_retrieved"])
        self.assertFalse(row["individual_notice_retrieved"])

    def test_no_staged_sources_does_not_create_false_coverage(self):
        result = staged.build([{"name":"Other","mode":"discovery_pending"}],fetch=Mock())
        self.assertEqual(result["staged_entrypoints"],0)
        self.assertEqual(result["probes"],[])


if __name__ == "__main__":
    unittest.main()
