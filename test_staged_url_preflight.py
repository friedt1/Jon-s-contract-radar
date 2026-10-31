"""Staged source URL hygiene tests. All hosts and listings are synthetic."""
import unittest
from unittest.mock import Mock

import probe_staged_sources as staged


ENTRY = "https://county.example/Bids.aspx"
SOURCE = {
    "name": "Cortland County",
    "mode": "discovery_pending",
    "candidate_official_url": ENTRY,
    "activation_gate": "Publisher terms and individual notice review required",
}


class StagedUrlPreflightTests(unittest.TestCase):
    def test_unsafe_staged_urls_never_trigger_network_requests(self):
        for url in (
            "http://county.example/Bids.aspx",
            "https://user:password@county.example/Bids.aspx",
            "https://127.0.0.1/Bids.aspx",
            "https://county.internal/Bids.aspx",
            "https://county.example:8443/Bids.aspx",
            "https://county.example/Bids.aspx?x=%0aInjected",
            "https://county.example/Bids.aspx#fragment",
            "https://county.example/Bids.aspx\\bad",
            {"url": ENTRY},
        ):
            with self.subTest(url=url):
                fetch = Mock(side_effect=AssertionError("network must not be used"))
                row = staged.probe(dict(SOURCE, candidate_official_url=url),
                                   fetch=fetch)
                self.assertEqual(row["state"], "listing_invalid_official_url")
                self.assertFalse(row["listing_retrieved"])
                self.assertFalse(row["individual_notice_retrieved"])
                self.assertFalse(row["direct_monitoring_activated"])
                fetch.assert_not_called()

    def test_unsafe_final_landing_is_not_counted_as_retrieved_listing(self):
        for final, expected in (
            ("http://county.example/Bids.aspx", "listing_insecure_redirect"),
            ("https://county.example:8443/Bids.aspx", "listing_unsafe_redirect"),
            ("https://user:pass@county.example/Bids.aspx", "listing_unsafe_redirect"),
            ("https://county.example/Bids.aspx?x=%0d", "listing_unsafe_redirect"),
            ("https://127.0.0.1/Bids.aspx", "listing_unsafe_redirect"),
            ("not a url", "listing_unsafe_redirect"),
        ):
            with self.subTest(final=final):
                fetch = Mock(return_value=("<h1>Bid listings</h1>", "text/html", final))
                row = staged.probe(SOURCE, fetch=fetch)
                self.assertEqual(row["state"], expected)
                self.assertFalse(row["listing_retrieved"])
                self.assertFalse(row["individual_notice_retrieved"])
                self.assertFalse(row["direct_monitoring_activated"])
                fetch.assert_called_once_with(ENTRY)

    def test_valid_staged_url_keeps_diagnostic_only_behavior(self):
        fetch = Mock(return_value=("<p>Bid listings</p>", "text/html", ENTRY))
        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["state"], "listing_reachable_no_bidid_records")
        self.assertTrue(row["listing_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])
        fetch.assert_called_once_with(ENTRY)

    def test_build_reports_invalid_staged_urls_separately(self):
        fetch = Mock(return_value=("<p>Bid listings</p>", "text/html", ENTRY))
        report = staged.build([
            SOURCE,
            dict(SOURCE, name="Unsafe", candidate_official_url="http://county.example/bids"),
            dict(SOURCE, name="Unknown", candidate_official_url=""),
        ], fetch=fetch)
        self.assertEqual(report["configured_targets"], 3)
        self.assertEqual(report["staged_entrypoints"], 2)
        self.assertEqual(report["safe_staged_entrypoints"], 1)
        self.assertEqual(report["invalid_staged_entrypoints"], 1)
        self.assertEqual(report["probes"][1]["state"], "listing_invalid_official_url")
        self.assertNotIn("opportunities", report)
        fetch.assert_called_once_with(ENTRY)


if __name__ == "__main__":
    unittest.main()
