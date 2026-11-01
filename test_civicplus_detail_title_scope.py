"""Offline CivicPlus detail-title scope regression cases; never seed live bids."""
import datetime as dt
import unittest
from unittest.mock import patch

import civicplus_bids
import scan

BASE = "https://county.example/Bids.aspx"
DETAIL = BASE + "?bidID=45"
SOURCE = {"name": "Chemung County bids", "url": BASE, "mode": "direct_page"}
NOW = dt.datetime(2026, 11, 1, 5, tzinfo=dt.timezone.utc)
LISTING = (
    '<article><p>County maintenance procurement</p><p>Bid No. RFB-45</p>'
    '<p>Status: Closes: Open 11/19/2026 2:00 PM</p>'
    '<a href="/Bids.aspx?bidID=45">Read on</a></article>'
)


def scan_detail(title, description=None):
    body = (
        "<p>Bid Number: RFB-45</p><p>Bid Title: " + title + "</p>"
        "<p>Status: Open</p><p>Closing Date/Time: 11/19/2026 2:00 PM</p>"
    )
    if description is not None:
        body += "<p>Description: " + description + "</p>"

    def fake_fetch(url, binary=False):
        if url == BASE:
            result = LISTING
        elif url == DETAIL:
            result = body
        else:
            raise AssertionError("Unexpected request: " + url)
        return (result.encode() if binary else result, "text/html", url)

    with patch.object(scan, "NOW", NOW), patch.object(
        scan, "fetch", side_effect=fake_fetch
    ):
        return scan.scan_direct(SOURCE)


class CivicPlusDetailTitleScopeTests(unittest.TestCase):
    def test_title_only_tree_work_remains_unverified_review(self):
        leads, diagnostic = scan_detail("Hazardous tree removal along county roads")
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["title"], "Hazardous tree removal along county roads")
        self.assertEqual(leads[0]["scope"], "Hazardous tree removal along county roads")
        self.assertEqual(leads[0]["deadline"], "2026-11-19")
        self.assertEqual(leads[0]["deadline_source"], "individual notice")
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertFalse(leads[0]["travel_verified"])
        self.assertIn("1 individual bid details fetched", diagnostic)

    def test_detail_title_overrides_generic_listing_title(self):
        leads, diagnostic = scan_detail("Office supplies and paper products")
        self.assertEqual(leads, [])
        self.assertIn("1 individual bid details fetched", diagnostic)

    def test_title_does_not_override_excluded_description(self):
        leads, _ = scan_detail("Tree removal", "Tree removal by others.")
        self.assertEqual(leads, [])

    def test_unrelated_demolition_title_is_not_tree_work(self):
        leads, _ = scan_detail("Owego building demolition and site restoration")
        self.assertEqual(leads, [])

    def test_title_is_isolated_from_metadata(self):
        body = (
            "Bid Number: RFB-45 Bid Title: Roadside tree trimming "
            "Status: Open Closing Date/Time: 11/19/2026 2:00 PM "
            "Description: See attached specifications."
        )
        self.assertEqual(civicplus_bids.detail_title(body), "Roadside tree trimming")

    def test_historical_erie_is_not_live(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bids due October 29, 2026",
            today=dt.date(2026, 11, 1)
        ))


if __name__ == "__main__":
    unittest.main()
