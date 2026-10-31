"""Synthetic CivicPlus tracked-card identity regressions; never seed live bids."""
import datetime as dt
import unittest
from unittest.mock import patch

import civicplus_bids
import scan

BASE = "https://county.example/Bids.aspx"
DETAIL = BASE + "?bidID=41"
SOURCE = {"name": "Chemung County bids", "url": BASE, "mode": "direct_page"}


def card(title, status, due, query):
    return ('<article><p>' + title + '</p><p>Status: Closes: '
            + status + ' ' + due + '</p><a href="/Bids.aspx?'
            + query + '">Read on</a></article>')


class TrackedCivicPlusCardsTests(unittest.TestCase):
    def test_marketing_links_share_one_individual_bid_identity(self):
        links = [
            "/Bids.aspx?bidID=41",
            "/Bids.aspx?utm_source=email&bidID=41",
            "/Bids.aspx?bidID=41&fbclid=tracking",
            "/Bids.aspx?bidID=41#details",
        ]
        self.assertEqual({civicplus_bids.individual_url(link, BASE)
                          for link in links}, {DETAIL})
        # Unknown parameters are potentially substantive and must survive.
        self.assertEqual(civicplus_bids.individual_url(
            "/Bids.aspx?bidID=41&ref=vendor&utm_campaign=mail", BASE),
            DETAIL + "&ref=vendor")
        self.assertNotEqual(civicplus_bids.individual_url(
            "/Bids.aspx?bidID=42", BASE), DETAIL)

    def test_conflicting_tracked_cards_require_one_authoritative_detail(self):
        html = (
            card("Office supplies bid", "Closed", "10/10/2026 9:00 AM",
                 "bidID=41&utm_source=mail")
            + card("Tree and stump removal", "Open", "11/19/2026 2:00 PM",
                   "fbclid=tracking&bidID=41")
        )
        requested = []

        def fetch(url, binary=False):
            requested.append(url)
            if url == BASE:
                body = html
            elif url == DETAIL:
                body = ('<p>Bid Number: 41</p><p>Status: Open</p>'
                        '<p>Description: Tree and stump removal along county roads.</p>'
                        '<p>Closing Date/Time: 11/19/2026 2:00 PM</p>')
            else:
                raise AssertionError("unexpected URL " + url)
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "NOW", dt.datetime(
                2026, 10, 30, 20, tzinfo=dt.timezone.utc)), \
             patch.object(scan, "fetch", side_effect=fetch):
            leads, diagnostic = scan.scan_direct(SOURCE)
        self.assertEqual(requested, [BASE, DETAIL])
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["url"], DETAIL)
        self.assertIn("Tree and stump removal", leads[0]["title"])
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("1 conflicting duplicate bid cards", diagnostic)

    def test_expired_erie_and_unrelated_owego_stay_excluded(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bids due 10/29/2026",
            "PennBid platform", today=dt.date(2026, 10, 30)))
        self.assertIsNone(scan.category("Owego demolition rebid due 11/19/2026"))


if __name__ == "__main__":
    unittest.main()
