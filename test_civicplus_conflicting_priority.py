"""Synthetic CivicPlus request-budget regressions; never seed live opportunities."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan

BASE = "https://county.example/Bids.aspx"
TARGET = BASE + "?bidID=41"
SOURCE = {"name": "Chemung County bids", "url": BASE, "mode": "direct_page"}
NOW = dt.datetime(2026, 10, 30, 20, tzinfo=dt.timezone.utc)


def card(number, title, status, closing):
    return ('<article><p>' + title + '</p><p>Status: Closes: ' + status
            + ' ' + closing + '</p><a href="/Bids.aspx?bidID='
            + str(number) + '">Read on</a></article>')


def crowded_listing(conflicting_date="11/19/2026 2:00 PM"):
    return (card(41, "Office equipment", "Closed", "10/10/2026 9:00 AM")
            + "".join(card(i, "General office supplies", "Open",
                           "11/20/2026 2:00 PM") for i in range(100, 160))
            + card(41, "Tree and stump removal bid", "Open", conflicting_date))


class ConflictingCardPriorityTests(unittest.TestCase):
    def scan_fixture(self, listing, target_detail):
        requested = []

        def fake_fetch(url, binary=False):
            requested.append(url)
            if url == BASE:
                body = listing
            elif url == TARGET:
                body = target_detail
            elif url.startswith(BASE + "?bidID="):
                body = ("<p>Status: Open</p><p>Description: Office supplies</p>"
                        "<p>Closing Date/Time: 11/20/2026 2:00 PM</p>")
            else:
                raise AssertionError("unexpected URL " + url)
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "NOW", NOW), patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, diagnostic = scan.scan_direct(SOURCE)
        return leads, diagnostic, requested

    def test_reopened_tree_card_gets_detail_budget_despite_closed_first_card(self):
        listing = crowded_listing()
        detail = ("<p>Status: Open</p><p>Description: Tree and stump removal"
                  " along local roads</p><p>Closing Date/Time: 11/19/2026 2:00 PM</p>")
        leads, diagnostic, requests = self.scan_fixture(listing, detail)
        self.assertEqual(requests[0:2], [BASE, TARGET])
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["url"], TARGET)
        self.assertEqual(leads[0]["deadline_source"], "individual notice")
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertFalse(leads[0]["travel_verified"])
        self.assertIn("1 conflicting duplicate bid cards", diagnostic)

    def test_expired_duplicate_card_not_promoted_ahead_of_future_generic_bids(self):
        listing = crowded_listing("10/15/2026 2:00 PM")
        detail = ("<p>Status: Open</p><p>Description: Tree removal</p>"
                  "<p>Closing Date/Time: 10/15/2026 2:00 PM</p>")
        leads, diagnostic, requests = self.scan_fixture(listing, detail)
        self.assertNotIn(TARGET, requests)
        self.assertEqual(leads, [])
        self.assertIn("conflicting duplicate bid cards", diagnostic)

    def test_individual_notice_closure_overrides_reopened_listing_card(self):
        listing = crowded_listing()
        detail = ("<p>Status: Closed</p><p>Description: Tree removal</p>"
                  "<p>Closing Date/Time: 11/19/2026 2:00 PM</p>")
        leads, diagnostic, requests = self.scan_fixture(listing, detail)
        self.assertEqual(requests[1], TARGET)
        self.assertEqual(leads, [])
        self.assertIn("closed", diagnostic)

    def test_erie_expired_and_owego_demolition_still_excluded(self):
        self.assertFalse(scan.eligible(
            "Erie PA tree and stump removal bid due October 29, 2026",
            "PennBid platform", today=dt.date(2026, 10, 30)))
        self.assertFalse(scan.eligible(
            "Owego NY demolition and site restoration bid due November 19, 2026",
            "Tioga County NY", today=dt.date(2026, 10, 30)))


if __name__ == "__main__":
    unittest.main()
