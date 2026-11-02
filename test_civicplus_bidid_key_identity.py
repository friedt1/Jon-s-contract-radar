"""Case-varied CivicPlus bidID URLs are one notice, never extra live bids.

Offline fixtures only: historical Erie/Owego cases are not live contracts.
"""
import datetime as dt
import unittest
from unittest.mock import patch

import civicplus_bids
import notice_identity
import scan

BASE = "https://county.example/Bids.aspx"
DETAIL = BASE + "?bidID=41"


class CivicPlusQueryKeyIdentityTests(unittest.TestCase):
    def test_single_numeric_bidid_key_is_case_insensitive_only_on_civicplus(self):
        variants = [
            DETAIL,
            BASE + "?BIDID=41",
            BASE + "?bidid=41&utm_source=notice",
            BASE + "?BidId=41#details",
        ]
        self.assertEqual({notice_identity.canonical_url(v) for v in variants},
                         {DETAIL})
        self.assertEqual(len({notice_identity.notice_id(v) for v in variants}), 1)
        self.assertEqual(civicplus_bids.individual_url(
            "/Bids.aspx?BIDID=41", BASE), DETAIL)
        # Other publishers may use case-sensitive query keys.
        self.assertNotEqual(
            notice_identity.notice_id("https://county.example/solicitations?bidID=41"),
            notice_identity.notice_id("https://county.example/solicitations?BIDID=41"))

    def test_duplicate_bidids_and_signed_links_are_never_rewritten(self):
        ambiguous = BASE + "?bidID=41&BIDID=42"
        self.assertEqual(notice_identity.canonical_url(ambiguous), ambiguous)
        self.assertEqual(civicplus_bids.individual_url(ambiguous, BASE), "")
        signed = BASE + "?BIDID=41&X-Amz-Signature=abc"
        self.assertEqual(notice_identity.canonical_url(signed), signed)
        # Non-numeric values are not legitimate CivicPlus notice IDs.
        self.assertEqual(notice_identity.canonical_url(BASE + "?BIDID=abc"),
                         BASE + "?BIDID=abc")

    def test_conflicting_case_variant_cards_fetch_once_and_use_detail_scope(self):
        listing = (
            '<article><p>Tree and stump removal bid</p>'
            '<p>Status: Closes: Open 11/19/2026 2:00 PM</p>'
            '<a href="/Bids.aspx?bidID=41">Read on</a></article>'
            '<article><p>Office supplies bid</p>'
            '<p>Status: Closes: Closed 10/10/2026 9:00 AM</p>'
            '<a href="/Bids.aspx?BIDID=41">Read on</a></article>'
        )
        detail = (
            "<p>Bid Title: Office supplies</p><p>Status: Open</p>"
            "<p>Description: Office paper and toner only.</p>"
            "<p>Closing Date/Time: 11/19/2026 2:00 PM</p>"
        )
        requested = []

        def fake_fetch(url, binary=False):
            requested.append(url)
            if url == BASE:
                return listing, "text/html", url
            if url == DETAIL:
                return detail.encode(), "text/html", url
            raise AssertionError("Unexpected URL: " + url)

        with (patch.object(scan, "NOW", dt.datetime(
                2026, 10, 30, 20, tzinfo=dt.timezone.utc)),
              patch.object(scan, "fetch", side_effect=fake_fetch)):
            leads, status = scan.scan_direct(
                {"name": "Chemung County bids", "url": BASE, "mode": "direct_page"})

        self.assertEqual(leads, [])
        self.assertEqual(requested, [BASE, DETAIL])
        self.assertIn("1 individual bid records", status)
        self.assertIn("1 conflicting duplicate bid cards", status)
        self.assertIn("1 individual bid details fetched", status)

    def test_historical_erie_and_owego_are_not_live_leads(self):
        self.assertFalse(scan.eligible(
            "Erie tree & stump removal bids due October 28, 2026",
            today=dt.date(2026, 11, 2)))
        self.assertIsNone(scan.category(
            "Owego building demolition and site restoration rebid"))


if __name__ == "__main__":
    unittest.main()
