"""Offline CivicPlus bid-number integrity checks; no real opportunities seeded."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan
import civicplus_bids

BASE = "https://county.example/Bids.aspx"
DETAIL = BASE + "?bidID=55"
SOURCE = {"name": "Chemung County bids", "url": BASE, "mode": "direct_page"}
NOW = dt.datetime(2026, 10, 31, 18, tzinfo=dt.timezone.utc)
LISTING = (
    '<article><p>Tree and stump removal bid</p>'
    '<p>Bid No. RFB-101</p>'
    '<p>Status: Closes: Open 11/20/2026 2:00 PM</p>'
    '<a href="/Bids.aspx?bidID=55">Read on</a></article>'
)


def run_notice(detail, listing=LISTING):
    requests = []

    def fake_fetch(url, binary=False):
        requests.append(url)
        if url == BASE:
            body = listing
        elif url == DETAIL:
            body = detail
        else:
            raise AssertionError("unexpected URL " + url)
        return (body.encode() if binary else body, "text/html", url)

    with patch.object(scan, "NOW", NOW), patch.object(
        scan, "fetch", side_effect=fake_fetch
    ):
        leads, diagnostic = scan.scan_direct(SOURCE)
    return leads, diagnostic, requests


def detail(number="Bid Number: RFB-101"):
    return (
        "<p>" + number + "</p><p>Status: Open</p>"
        "<p>Description: Remove hazardous trees along county roads.</p>"
        "<p>Closing Date/Time: 11/20/2026 2:00 PM</p>"
    )


class CivicPlusBidNumberIntegrityTests(unittest.TestCase):
    def test_mismatched_bid_number_rejects_individual_detail(self):
        for number in ("Bid Number: RFB-202", "Bid No. RFB-202"):
            with self.subTest(number=number):
                leads, diagnostic, requests = run_notice(detail(number))
                self.assertEqual(leads, [])
                self.assertEqual(requests, [BASE, DETAIL])
                self.assertIn("1 detail errors: detail bid number mismatch", diagnostic)
                self.assertIn("0 individual bid details fetched", diagnostic)

    def test_matching_number_accepts_only_unverified_candidate(self):
        for number in ("Bid Number: RFB-101", "Bid No. rfb-101"):
            with self.subTest(number=number):
                leads, diagnostic, requests = run_notice(detail(number))
                self.assertEqual(requests, [BASE, DETAIL])
                self.assertEqual(len(leads), 1)
                self.assertEqual(leads[0]["status"], "unverified")
                self.assertEqual(leads[0]["deadline"], "2026-11-20")
                self.assertEqual(leads[0]["bid_number"], "RFB-101")
                self.assertFalse(leads[0]["travel_verified"])
                self.assertIn("1 individual bid details fetched", diagnostic)

    def test_missing_detail_number_does_not_invent_conflict(self):
        leads, diagnostic, _ = run_notice(detail("Bid Title: Roadside tree work"))
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("1 individual bid details fetched", diagnostic)

    def test_multi_token_bid_number_mismatch_rejected(self):
        # Both IDs share the prefix "RFP". Comparing only the first token
        # would accept the WRONG individual solicitation as this listing.
        listing = LISTING.replace("RFB-101", "RFP 26-ADM-014")
        leads, diagnostic, requests = run_notice(
            detail("Bid Number: RFP 26-ADM-015"), listing=listing)
        self.assertEqual(leads, [])
        self.assertEqual(requests, [BASE, DETAIL])
        self.assertIn("detail bid number mismatch", diagnostic)
        self.assertIn("0 individual bid details fetched", diagnostic)

    def test_matching_multi_token_bid_number_keeps_unverified_status(self):
        listing = LISTING.replace("RFB-101", "RFP 26-ADM-014")
        leads, diagnostic, _ = run_notice(
            detail("Bid Number: rfp 26-ADM-014"), listing=listing)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["bid_number"], "RFP 26-ADM-014")
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("1 individual bid details fetched", diagnostic)

    def test_bid_number_parser_does_not_absorb_adjacent_fields(self):
        for text, expected in (
            ("Bid No. RFP 26-ADM-014 Status: Open", "RFP 26-ADM-014"),
            ("Bid Number: IFB FY26-12 Description: Remove trees", "IFB FY26-12"),
            ("Bid Number: RFB-101 Closing Date/Time: 11/20/2026", "RFB-101"),
            ("Bid Number: 2026-33 Status: Open", "2026-33"),
            ("Bid Number: RFP Status: Open", "RFP"),
        ):
            with self.subTest(text=text):
                self.assertEqual(civicplus_bids.bid_number_of(text), expected)

    def test_historical_erie_and_unrelated_owego_stay_excluded(self):
        self.assertFalse(scan.eligible(
            "Erie PA tree and stump removal bids due October 29, 2026",
            today=dt.date(2026, 10, 31)
        ))
        self.assertIsNone(scan.category(
            "Owego building demolition and site restoration rebid"
        ))


if __name__ == "__main__":
    unittest.main()
