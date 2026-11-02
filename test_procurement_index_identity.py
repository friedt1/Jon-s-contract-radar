"""Offline regression: a procurement collection is not an individual bid.

Synthetic pages only; no source permissions or live opportunities asserted.
"""
import datetime as dt
import unittest
from unittest.mock import patch

import scan


SOURCE = {"name": "Test County", "url": "https://example.gov/bids",
          "mode": "direct_page", "verified_url": True}
INDEX = "https://example.gov/bids/current"
NOTICE = "https://example.gov/bids/42"


class ProcurementIndexIdentityTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(
            scan, "NOW", dt.datetime(2026, 11, 2, 17,
                                     tzinfo=dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def scan_pages(self, pages):
        requests = []

        def fake_fetch(url, binary=False):
            requests.append(url)
            body = pages[url]
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(SOURCE)
        return leads, status, requests

    def test_collection_routes_not_individual_notice_links(self):
        for path in ("/bids", "/bids/current", "/bids/open",
                     "/bids/2026", "/rfp/archive", "/solicitations/results",
                     "/bids/current.html", "/bids/open.aspx",
                     "/rfp/archive.php", "/solicitations/2026.htm",
                     "/bids/closed", "/bids/bid-results.html",
                     "/purchasing", "/procurement", "/Bids.aspx"):
            with self.subTest(path=path):
                url = "https://example.gov" + path
                self.assertTrue(scan.is_procurement_index_link(url))
                self.assertFalse(scan.is_individual_notice_link(url))
        for path in ("/bids/42", "/bid/42", "/rfp/bridge-42"):
            with self.subTest(path=path):
                self.assertFalse(scan.is_procurement_index_link(
                    "https://example.gov" + path))
                self.assertTrue(scan.is_individual_notice_link(
                    "https://example.gov" + path))
        self.assertFalse(scan.is_procurement_index_link(
            "https://example.gov/Bids.aspx?bidID=42"))
        self.assertTrue(scan.is_individual_notice_link(
            "https://example.gov/Bids.aspx?bidID=42"))

    def test_headline_on_collection_without_details_does_not_publish(self):
        leads, status, requests = self.scan_pages({
            SOURCE["url"]: '<a href="/bids/current">Current bids</a>',
            INDEX: ('<h1>Tree removal bid due November 19, 2026</h1>'
                    '<p>Browse current solicitations for details.</p>'),
        })
        self.assertEqual(leads, [])
        self.assertEqual(requests, [SOURCE["url"], INDEX])
        self.assertIn("1 details checked", status)

    def test_collection_can_still_lead_to_fetched_individual_notice(self):
        leads, status, requests = self.scan_pages({
            SOURCE["url"]: '<a href="/bids/current">Current bids</a>',
            INDEX: '<a href="/bids/42">Tree removal bid due November 19, 2026</a>',
            NOTICE: '<h1>Tree removal bid due November 19, 2026</h1>',
        })
        self.assertEqual([lead["url"] for lead in leads], [NOTICE])
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertEqual(requests, [SOURCE["url"], INDEX, NOTICE])
        self.assertIn("2 details checked", status)

    def test_file_suffixed_collection_is_not_a_bid(self):
        index = "https://example.gov/bids/current.html"
        leads, status, requests = self.scan_pages({
            SOURCE["url"]: '<a href="/bids/current.html">Current bids</a>',
            index: ('<h1>Tree removal bid due November 19, 2026</h1>'
                    '<p>Browse the current procurement listings.</p>'),
        })
        self.assertEqual(leads, [])
        self.assertEqual(requests, [SOURCE["url"], index])
        self.assertIn("1 details checked", status)

    def test_file_suffixed_collection_can_link_real_notice_detail(self):
        index = "https://example.gov/bids/current.html"
        notice = "https://example.gov/bids/42.html"
        leads, _, requests = self.scan_pages({
            SOURCE["url"]: '<a href="/bids/current.html">Current bids</a>',
            index: '<a href="/bids/42.html">Tree removal bid due November 19, 2026</a>',
            notice: '<h1>Tree removal bid due November 19, 2026</h1>',
        })
        self.assertEqual([lead["url"] for lead in leads], [notice])
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertEqual(requests, [SOURCE["url"], index, notice])

    def test_historical_erie_and_unrelated_owego_stay_excluded(self):
        self.assertFalse(scan.eligible(
            "Erie PA tree and stump removal bid due October 29, 2026",
            today=dt.date(2026, 11, 2)))
        self.assertFalse(scan.eligible(
            "Owego demolition RFP; tree removal by owner; "
            "bids due November 13, 2026",
            today=dt.date(2026, 11, 2)))


if __name__ == "__main__":
    unittest.main()
