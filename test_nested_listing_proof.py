"""Synthetic regression fixtures; no real bid is asserted or seeded."""
import unittest
from unittest.mock import patch

import scan


SOURCE = {"name": "Test County", "url": "https://example.gov/bids", "mode": "direct_page"}
INDEX = "https://example.gov/procurement"
NOTICE = "https://example.gov/bid/123"
LISTING = '<a href="/procurement">Current bids</a>'
NESTED = ('<div><h1>Tree removal bid due 11/19/2026</h1>'
          '<a href="/bid/123">Tree removal bid details</a></div>')
DETAIL = '<h1>Tree removal bid due 11/19/2026</h1>'


class NestedListingProofTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(
            scan, "NOW", scan.dt.datetime(2026, 10, 28, 18,
                                         tzinfo=scan.dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def scan_fixture(self, detail_available=True):
        def fake(url, binary=False):
            if url == SOURCE["url"]:
                body = LISTING
            elif url == INDEX:
                body = NESTED
            elif url == NOTICE and detail_available:
                body = DETAIL
            else:
                raise OSError("individual notice unavailable")
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "fetch", side_effect=fake):
            return scan.scan_direct(SOURCE)

    def test_div_based_bid_index_is_not_a_solicitation(self):
        leads, diagnostic = self.scan_fixture()
        self.assertEqual([lead["url"] for lead in leads], [NOTICE])
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("1 nested listing pages excluded as notices", diagnostic)

    def test_index_is_not_published_when_individual_notice_fails(self):
        leads, diagnostic = self.scan_fixture(detail_available=False)
        self.assertEqual(leads, [])
        self.assertIn("detail errors", diagnostic)
        self.assertIn("1 nested listing pages excluded as notices", diagnostic)

    def test_notice_link_shape_not_navigation_or_attachment(self):
        self.assertTrue(scan.is_individual_notice_link(NOTICE))
        self.assertTrue(scan.is_individual_notice_link(
            "https://example.gov/Bids.aspx?bidID=123"))
        self.assertFalse(scan.is_individual_notice_link(INDEX))
        self.assertFalse(scan.is_individual_notice_link(
            "https://example.gov/bid/specifications.pdf"))


class ClosedStatusContextTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(
            scan, "NOW", scan.dt.datetime(2026, 10, 28, 18,
                                         tzinfo=scan.dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def test_closed_road_in_scope_does_not_close_bid(self):
        text = ("Tree removal bid due 11/19/2026. "
                "The road will be closed during tree felling.")
        self.assertFalse(scan.closed(text))
        self.assertTrue(scan.eligible(text, "Test County"))

    def test_explicit_closed_bid_and_award_are_rejected(self):
        for text in (
            "Tree removal bid closed",
            "Tree removal bid status: Closed",
            "Tree removal contract awarded",
            "Tree trimming bid closed for submissions",
            "Closed",
        ):
            with self.subTest(text=text):
                self.assertTrue(scan.closed(text))

    def test_erie_historical_and_owego_unrelated_not_live(self):
        erie = ("Erie PA Bid 6565-26 TREE & STUMP REMOVAL "
                "due 10/20/2026")
        owego = ("67 Central Avenue Demolition Rebid, Owego NY. "
                 "Building demolition and site restoration due 11/13/2026")
        self.assertFalse(scan.eligible(erie, "PennBid platform"))
        self.assertIsNone(scan.category(owego))
        self.assertFalse(scan.eligible(owego, "Tioga County NY"))


if __name__ == "__main__":
    unittest.main()
