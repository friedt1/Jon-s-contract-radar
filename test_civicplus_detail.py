"""Synthetic CivicPlus detail-page fixtures modeled on the public bid detail labels."""
import unittest
from unittest.mock import patch

import civicplus_bids as civic
import scan

BASE = "https://example.gov/Bids.aspx"
SOURCE = {"name": "Chemung County bids", "url": BASE, "mode": "direct_page"}


def listing(due="10/20/2026", status="Open"):
    return ('<article><a href="/Bids.aspx?bidID=31">Tree and stump removal bid</a>'
            '<p>Bid No. RFB-2816</p><p>Status:</p><p>Closes:</p>'
            '<p>' + status + '</p><p>' + due + ' 1:45 PM</p></article>')


def detail(status="Open", due="11/19/2026", location=""):
    return ('<table><tr><th>Bid Number:</th><td>RFB-2816</td></tr>'
            '<tr><th>Bid Title:</th><td>Tree and stump removal bid</td></tr>'
            '<tr><th>Status:</th><td>' + status + '</td></tr></table>'
            '<p>Publication Date/Time: 10/01/2026 12:00 AM</p>'
            '<p>Closing Date/Time: ' + due + ' 1:30 PM</p>'
            '<p>Description: Tree removal and stump grinding along a county roadway.</p>'
            + ('<p>Project Location: ' + location + '</p>' if location else '')
            + '<p>Related Documents:</p>')


class CivicPlusDetailTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(scan, "NOW", scan.dt.datetime(2026, 10, 28, 19, tzinfo=scan.dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def run_scan(self, list_html, detail_html):
        def fake(url, binary=False):
            body = detail_html if binary else list_html
            return (body.encode() if binary else body, "text/html", url)
        with patch.object(scan, "fetch", side_effect=fake):
            return scan.scan_direct(SOURCE)

    def test_detail_closing_overrides_expired_listing_and_extracts_scope(self):
        leads, status = self.run_scan(listing(), detail(location="Horseheads, NY"))
        self.assertEqual(len(leads), 1)
        lead = leads[0]
        self.assertEqual(lead["deadline"], "2026-11-19")
        self.assertEqual(lead["deadline_time"], "1:30 PM")
        self.assertEqual(lead["deadline_source"], "individual notice")
        self.assertIn("along a county roadway", lead["scope"])
        self.assertEqual(lead["location"], "Horseheads, NY")
        self.assertFalse(lead["location_verified"])
        self.assertFalse(lead["travel_verified"])
        self.assertEqual(lead["status"], "unverified")
        self.assertIn("1 relevant details checked", status)
        self.assertIn("1 individual bid details fetched", status)

    def test_detail_expired_overrides_future_listing(self):
        leads, status = self.run_scan(listing("11/19/2026"), detail(due="10/20/2026"))
        self.assertEqual(leads, [])
        self.assertIn("1 expired", status)
        self.assertIn("1 individual bid details fetched", status)

    def test_detail_awarded_overrides_open_listing(self):
        leads, status = self.run_scan(listing("11/19/2026"), detail(status="Awarded"))
        self.assertEqual(leads, [])
        self.assertIn("1 closed", status)
        self.assertIn("1 individual bid details fetched", status)

    def test_publication_date_is_not_a_deadline(self):
        self.assertEqual(civic.detail_closing_of("Publication Date/Time: 11/19/2026"), ("", ""))
        self.assertEqual(civic.detail_closing_of("Closing Date/Time: 11/19/2026 1:30 PM"),
                         ("2026-11-19", "1:30 PM"))

    def test_detail_description_stops_before_later_status_and_bid_metadata(self):
        # Synthetic notice with publisher fields after the scope. They must
        # not leak into the description used for relevance or closing checks.
        body = ("Bid Number: RFB-81 Description: Remove hazardous trees "
                "and grind stumps. Status: Open Closing Date/Time: "
                "11/19/2026 1:30 PM Project Location: Elmira, NY "
                "Bid Title: Roadside tree removal Related Documents: packet")
        self.assertEqual(civic.detail_description(body),
                         "Remove hazardous trees and grind stumps.")
        self.assertEqual(civic.detail_worksite(body), "Elmira, NY")

    def test_scan_does_not_mix_status_or_other_fields_into_scope(self):
        body = ("<p>Bid Number: RFB-81</p><p>Bid Title: Tree removal</p>"
                "<p>Description: Remove hazardous trees and grind stumps.</p>"
                "<p>Status: Open</p><p>Closing Date/Time: 11/19/2026 1:30 PM</p>"
                "<p>Project Location: Elmira, NY</p>"
                "<p>Bid Title: Roadside tree removal</p>")
        leads, _ = self.run_scan(listing("11/19/2026"), body)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["scope"], "Remove hazardous trees and grind stumps.")
        self.assertEqual(leads[0]["location"], "Elmira, NY")
        self.assertNotIn("Status:", leads[0]["summary"])
        self.assertEqual(leads[0]["status"], "unverified")

    def test_purchasing_office_not_assumed_to_be_worksite(self):
        self.assertEqual(civic.detail_worksite("Description: Contact Purchasing at 150 Lake Street Elmira NY"), "")
        leads, _ = self.run_scan(listing("11/19/2026"), detail())
        self.assertEqual(len(leads), 1)
        self.assertIn("Worksite unverified", leads[0]["location"])

    def test_bidid_homepage_without_individual_fields_is_not_proof(self):
        leads, status = self.run_scan(listing("11/19/2026"),
                                      '<html><h1>County purchasing homepage</h1></html>')
        self.assertEqual(leads, [])
        self.assertIn('0 individual bid details fetched', status)
        self.assertIn('missing individual bid fields', status)

    def test_detail_failure_is_reported_without_publishing_listing_only_lead(self):
        def fake(url, binary=False):
            if binary:
                raise OSError("network failure")
            return listing(due=""), "text/html", url
        with patch.object(scan, "fetch", side_effect=fake):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(leads, [])
        self.assertIn("detail errors: OSError", status)
        self.assertIn("0 individual bid details fetched", status)


if __name__ == "__main__":
    unittest.main()
