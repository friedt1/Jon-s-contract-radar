"""Offline Granicus staging regressions: no real bid is asserted or published."""
import datetime as dt
import unittest

import granicus_rfps as granicus
import probe_staged_sources as staged
import scan

ENTRY = "https://www.binghamton-ny.gov/government/departments/purchasing/bids-rfps"
NOTICE = "https://www.binghamton-ny.gov/Home/Components/RFP/RFP/420/90"
SOURCE = {
    "name": "City of Binghamton", "mode": "discovery_pending",
    "candidate_official_url": ENTRY, "activation_gate": "Review publisher terms",
}
NOW = dt.datetime(2026, 10, 29, 18, 0, tzinfo=dt.timezone.utc)


def listing(due="10/01/2026 10:30 AM", title="BID: Emergency tree removal"):
    return ('<table><tr><td><a href="/Home/Components/RFP/RFP/420/90">'
            + title + '</a></td><td>09/01/2026</td><td>'
            + due + '</td><td>Open</td></tr></table>')


def detail(due="10/01/2026 10:30 AM"):
    return ('<h1>BID: Emergency tree removal</h1>'
            '<p>Department: Purchasing</p><p>Start Date: 09/01/2026</p>'
            '<p>Close Date: ' + due + '</p>'
            '<p>Description: Emergency tree removal in city parks.</p>')


class GranicusStagingTests(unittest.TestCase):
    def test_only_same_host_individual_notice_paths(self):
        self.assertEqual(granicus.individual_url("/Home/Components/RFP/RFP/420/90", ENTRY), NOTICE)
        for link in (
            "https://evil.example/Home/Components/RFP/RFP/420/90",
            "/Home/Components/RFP/RFP/not-a-number/90",
            "/Home/Components/RFP/RFP/420/90?redirect=1",
            "/Home/Components/RFP/RFP/420/90%0a",
            "http://www.binghamton-ny.gov/Home/Components/RFP/RFP/420/90",
            "/government/departments/purchasing/bids-rfps",
        ):
            with self.subTest(link=link):
                self.assertEqual(granicus.individual_url(link, ENTRY), "")

    def test_listing_second_date_is_closing_not_start(self):
        rows = granicus.listing_records(scan.parse_html(listing()), ENTRY)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["deadline"], "2026-10-01")
        self.assertEqual(rows[0]["deadline_time"], "10:30 AM")
        self.assertEqual(rows[0]["open_status"], "open")
        one_date = '<tr><td><a href="/Home/Components/RFP/RFP/420/90">BID: Tree</a></td><td>09/01/2026</td></tr>'
        self.assertEqual(granicus.listing_records(scan.parse_html(one_date), ENTRY)[0]["deadline"], "")

    def test_stale_open_label_does_not_imply_open_contract(self):
        def fetch(url, binary=False):
            if url == ENTRY:
                return listing(), "text/html", url
            return detail().encode(), "text/html", url
        result = staged.build([SOURCE], fetch=fetch, now=NOW)
        row = result["probes"][0]
        self.assertEqual(row["state"], "notice_format_confirmed_terms_review_required")
        self.assertTrue(row["individual_notice_retrieved"])
        self.assertEqual(row["sample_notice_status_source"], "listing_unverified")
        self.assertEqual(row["sample_notice_listing_status"], "open")
        self.assertEqual(row["sample_notice_detail_status"], "unknown")
        self.assertEqual(row["sample_notice_status"], "unknown")
        self.assertEqual(row["sample_notice_temporal_evidence"], "deadline_passed")
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertNotIn("opportunities", result)

    def test_future_listing_open_cannot_become_detail_open_without_status(self):
        # A future closing date is not evidence that the individual notice
        # explicitly remains open; Granicus details often omit Status.
        def fetch(url, binary=False):
            if url == ENTRY:
                return listing("11/20/2026 10:30 AM"), "text/html", url
            return detail("11/20/2026 10:30 AM").encode(), "text/html", url

        row = staged.probe(SOURCE, fetch=fetch, now=NOW)
        self.assertEqual(row["sample_notice_listing_status"], "open")
        self.assertEqual(row["sample_notice_detail_status"], "unknown")
        self.assertEqual(row["sample_notice_status"], "unknown")
        self.assertEqual(row["sample_notice_status_source"], "listing_unverified")
        self.assertEqual(row["sample_notice_temporal_evidence"],
                         "deadline_not_passed_unverified")
        self.assertFalse(row["direct_monitoring_activated"])

    def test_listing_closed_is_conservative_when_detail_omits_status(self):
        def fetch(url, binary=False):
            if url == ENTRY:
                return listing("11/20/2026 10:30 AM").replace(
                    "<td>Open</td>", "<td>Closed</td>"), "text/html", url
            return detail("11/20/2026 10:30 AM").encode(), "text/html", url

        row = staged.probe(SOURCE, fetch=fetch, now=NOW)
        self.assertEqual(row["sample_notice_detail_status"], "unknown")
        self.assertEqual(row["sample_notice_status"], "closed")
        self.assertEqual(row["sample_notice_temporal_evidence"],
                         "closed_or_awarded")
        self.assertFalse(row["direct_monitoring_activated"])

    def test_conflicting_closing_dates_are_explicitly_unverified(self):
        def fetch(url, binary=False):
            return (listing("10/31/2026 10:30 AM"), "text/html", url) if url == ENTRY else (
                detail("11/02/2026 10:30 AM").encode(), "text/html", url)
        row = staged.probe(SOURCE, fetch=fetch, now=NOW)
        self.assertTrue(row["sample_notice_deadline_conflict"])
        self.assertEqual(row["sample_notice_temporal_evidence"], "conflicting_deadlines_unverified")
        self.assertFalse(row["direct_monitoring_activated"])

    def test_homepage_substitution_is_not_notice_evidence(self):
        def fetch(url, binary=False):
            return (listing(), "text/html", url) if url == ENTRY else (
                b'<h1>Bids and RFPs</h1><p>Open bids are listed here.</p>', "text/html", url)
        row = staged.probe(SOURCE, fetch=fetch, now=NOW)
        self.assertEqual(row["state"], "individual_notice_fields_missing")
        self.assertFalse(row["individual_notice_retrieved"])

    def test_redirect_to_different_notice_is_rejected(self):
        def fetch(url, binary=False):
            return (listing(), "text/html", url) if url == ENTRY else (
                detail().encode(), "text/html",
                "https://www.binghamton-ny.gov/Home/Components/RFP/RFP/421/90")
        row = staged.probe(SOURCE, fetch=fetch, now=NOW)
        self.assertEqual(row["state"], "individual_notice_redirect_or_type_mismatch")
        self.assertFalse(row["direct_monitoring_activated"])

    def test_unrelated_bid_stays_diagnostic_only(self):
        def fetch(url, binary=False):
            return (listing(title="RFP: ATM service"), "text/html", url) if url == ENTRY else (
                detail().replace("Emergency tree removal", "ATM service").encode(), "text/html", url)
        row = staged.probe(SOURCE, fetch=fetch, now=NOW)
        self.assertTrue(row["individual_notice_retrieved"])
        self.assertNotIn("opportunities", row)
        self.assertFalse(row["direct_monitoring_activated"])


if __name__ == "__main__":
    unittest.main()
