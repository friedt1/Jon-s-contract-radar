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


    def test_broken_first_notice_retries_next_without_publishing(self):
        listing = ('<article><a href="/Bids.aspx?bidID=4">Old tree removal</a></article>'
                   '<article><a href="/Bids.aspx?bidID=5">Tree removal</a></article>')
        calls = []
        def fetch(url, binary=False):
            calls.append(url)
            if url == ENTRY:
                return listing, "text/html", url
            if "bidID=4" in url:
                raise OSError("historical notice missing")
            return detail().encode(), "text/html", url

        result = staged.build([SOURCE], fetch=fetch)
        row = result["probes"][0]
        self.assertEqual(row["state"], "notice_format_confirmed_terms_review_required")
        self.assertEqual(row["individual_records_discovered"], 2)
        self.assertEqual(row["individual_samples_attempted"], 2)
        self.assertEqual(row["individual_sample_failures"][0]["state"],
                         "individual_notice_fetch_error")
        self.assertEqual(row["individual_sample_failures"][0]["error_type"], "OSError")
        self.assertTrue(row["sample_notice_url"].endswith("bidID=5"))
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertNotIn("opportunities", result)
        self.assertEqual(len(calls), 3)

    def test_missing_fields_and_robots_denial_can_fall_back(self):
        listing = ('<article><a href="/Bids.aspx?bidID=4">Tree bid</a></article>'
                   '<article><a href="/Bids.aspx?bidID=5">Tree bid</a></article>'
                   '<article><a href="/Bids.aspx?bidID=6">Tree bid</a></article>')
        def fetch(url, binary=False):
            if url == ENTRY:
                return listing, "text/html", url
            if "bidID=4" in url:
                raise robots_policy.RobotsDenied("notice path denied")
            if "bidID=5" in url:
                return b"<h1>County purchasing homepage</h1>", "text/html", url
            return detail().encode(), "text/html", url

        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["state"], "notice_format_confirmed_terms_review_required")
        self.assertEqual(row["individual_samples_attempted"], 3)
        self.assertEqual([x["state"] for x in row["individual_sample_failures"]],
                         ["individual_notice_robots_blocked",
                          "individual_notice_fields_missing"])
        self.assertTrue(row["sample_notice_url"].endswith("bidID=6"))
        self.assertFalse(row["direct_monitoring_activated"])

    def test_bounded_failures_do_not_fetch_fourth_notice(self):
        listing = "".join(
            f'<article><a href="/Bids.aspx?bidID={n}">Tree removal</a></article>'
            for n in range(4, 8)
        )
        calls = []
        def fetch(url, binary=False):
            calls.append(url)
            if url == ENTRY:
                return listing, "text/html", url
            raise OSError("notice unavailable")

        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["state"], "individual_notice_fetch_error")
        self.assertEqual(row["individual_records_discovered"], 4)
        self.assertEqual(row["individual_samples_attempted"], staged.MAX_SAMPLE_DETAILS)
        self.assertEqual(len(row["individual_sample_failures"]), staged.MAX_SAMPLE_DETAILS)
        self.assertEqual(len(calls), staged.MAX_SAMPLE_DETAILS + 1)
        self.assertFalse(row["individual_notice_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])

    def test_mixed_sample_failures_are_reported_distinctly(self):
        listing = ('<article><a href="/Bids.aspx?bidID=4">Tree bid</a></article>'
                   '<article><a href="/Bids.aspx?bidID=5">Tree bid</a></article>')
        def fetch(url, binary=False):
            if url == ENTRY:
                return listing, "text/html", url
            if "bidID=4" in url:
                raise robots_policy.RobotsDenied("denied")
            raise OSError("gone")

        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["state"], "individual_notice_samples_failed")
        self.assertEqual(row["individual_samples_attempted"], 2)
        self.assertEqual(len(row["individual_sample_failures"]), 2)
        self.assertFalse(row["individual_notice_retrieved"])


if __name__ == "__main__":
    unittest.main()
