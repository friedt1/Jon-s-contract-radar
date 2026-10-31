"""Synthetic CivicPlus duplicate-card regressions; no live bids are seeded."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan

BASE = "https://county.example/Bids.aspx"
DETAIL = BASE + "?bidID=41"
SOURCE = {"name": "Chemung County bids", "url": BASE, "mode": "direct_page"}
NOW = dt.datetime(2026, 10, 30, 20, tzinfo=dt.timezone.utc)


def card(title, status, due):
    return ('<article><p>' + title + '</p><p>Status: Closes: '
            + status + ' ' + due
            + '</p><a href="/Bids.aspx?bidID=41">Read on</a></article>')


def detail(status, description=None, closing="11/19/2026 2:00 PM"):
    body = ('<p>Bid Number: 41</p><p>Status: ' + status + '</p>')
    if description is not None:
        body += '<p>Description: ' + description + '</p>'
    return body + '<p>Closing Date/Time: ' + closing + '</p>'


class ConflictingCivicPlusCardTests(unittest.TestCase):
    def scan(self, listing, individual):
        requested = []

        def fake_fetch(url, binary=False):
            requested.append(url)
            if url == BASE:
                body = listing
            elif url == DETAIL:
                body = individual
            else:
                raise AssertionError("unexpected fetch " + url)
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "NOW", NOW), \
             patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, diagnostic = scan.scan_direct(SOURCE)
        return leads, diagnostic, requested

    def test_first_closed_card_cannot_hide_reopened_individual_bid(self):
        listing = (card("Office supplies bid", "Closed", "10/10/2026 9:00 AM")
                   + card("Tree and stump removal bid", "Open", "11/19/2026 2:00 PM"))
        leads, diagnostic, requested = self.scan(
            listing, detail("Open", "Tree and stump removal along county roads"))
        self.assertEqual(requested, [BASE, DETAIL])
        self.assertEqual(len(leads), 1)
        self.assertIn("Tree and stump removal", leads[0]["title"])
        self.assertEqual(leads[0]["deadline"], "2026-11-19")
        self.assertEqual(leads[0]["deadline_source"], "individual notice")
        self.assertEqual(leads[0]["open_status"], "detail_listed_open")
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("1 conflicting duplicate bid cards", diagnostic)

    def test_first_open_card_cannot_reopen_closed_individual_bid(self):
        listing = (card("Tree removal bid", "Open", "11/19/2026 2:00 PM")
                   + card("Office supplies bid", "Closed", "10/10/2026 9:00 AM"))
        leads, diagnostic, requested = self.scan(
            listing, detail("Closed", "Office supplies"))
        self.assertEqual(leads, [])
        self.assertEqual(requested, [BASE, DETAIL])
        self.assertIn("1 closed", diagnostic)

    def test_conflicting_cards_without_individual_scope_are_not_promoted(self):
        listing = (card("Tree removal bid", "Closed", "10/10/2026 9:00 AM")
                   + card("Tree trimming bid", "Open", "11/19/2026 2:00 PM"))
        leads, diagnostic, requested = self.scan(listing, detail("Open"))
        self.assertEqual(leads, [])
        self.assertEqual(requested, [BASE, DETAIL])
        self.assertIn("1 individual bid details fetched", diagnostic)

    def test_repeated_links_inside_one_card_are_not_conflicting(self):
        listing = ('<article><p>Tree removal bid</p><p>Status: Open</p>'
                   '<p>Closes: 11/19/2026 2:00 PM</p>'
                   '<a href="/Bids.aspx?bidID=41">Read on</a>'
                   '<a href="/Bids.aspx?bidID=41">View details</a></article>')
        leads, diagnostic, requested = self.scan(
            listing, detail("Open", "Tree removal"))
        self.assertEqual(requested, [BASE, DETAIL])
        self.assertEqual(len(leads), 1)
        self.assertIn("0 conflicting duplicate bid cards", diagnostic)

    def test_expired_erie_and_unrelated_owego_still_excluded(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bids due 10/29/2026",
            "PennBid platform", today=dt.date(2026, 10, 30)))
        self.assertIsNone(scan.category("Owego demolition rebid due 11/19/2026"))


if __name__ == "__main__":
    unittest.main()
