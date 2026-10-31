"""Synthetic RSS amendment ordering tests; no real opportunities are seeded."""
import datetime as dt
import unittest
from unittest.mock import patch
from xml.sax.saxutils import escape

import local_bid_rss
import scan

NOW = dt.datetime(2026, 10, 31, 16, tzinfo=dt.timezone.utc)
OLD_PUB = "Thu, 29 Oct 2026 12:00:00 GMT"
NEW_PUB = "Sat, 31 Oct 2026 15:00:00 GMT"


def feed(*entries):
    return "<rss version='2.0'><channel>" + "".join(
        "<item><title>" + escape(title) + "</title>"
        "<link>" + escape(url) + "</link>"
        "<description>" + escape(description) + "</description>"
        "<pubDate>" + published + "</pubDate></item>"
        for title, url, description, published in entries
    ) + "</channel></rss>"


ORIGINAL = (
    "Tree removal bid", "https://county.example/Bids.aspx?bidID=47&utm_source=mail",
    "Sealed bids due October 30, 2026 at 1 PM", OLD_PUB,
)
AMENDMENT = (
    "Amended tree removal bid", "https://county.example/Bids.aspx?bidID=47",
    "Amended: sealed bids due November 4, 2026 at 1 PM", NEW_PUB,
)


class LatestRSSAmendmentTests(unittest.TestCase):
    def test_newer_amendment_replaces_expired_original_in_either_feed_order(self):
        for entries in ((ORIGINAL, AMENDMENT), (AMENDMENT, ORIGINAL)):
            with self.subTest(order=entries[0][0]):
                rows = local_bid_rss.parse(feed(*entries), now=NOW)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["title"], AMENDMENT[0])
                self.assertEqual(rows[0]["description"], AMENDMENT[2])
                self.assertEqual(rows[0]["published"], "2026-10-31")
                self.assertEqual(rows[0]["url"],
                                 "https://county.example/Bids.aspx?bidID=47")
                self.assertEqual(rows[0]["status"], "unverified")
                self.assertFalse(rows[0]["original_notice_confirmed"])

    def test_equal_timestamp_keeps_first_copy(self):
        first = (ORIGINAL[0], ORIGINAL[1], "First source copy", NEW_PUB)
        second = (AMENDMENT[0], AMENDMENT[1], "Conflicting copy", NEW_PUB)
        rows = local_bid_rss.parse(feed(first, second), now=NOW)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["description"], "First source copy")

    def test_distinct_bid_ids_not_collapsed(self):
        another = (
            "Tree trimming bid", "https://county.example/Bids.aspx?bidID=48",
            "Sealed bids due November 6, 2026", NEW_PUB,
        )
        rows = local_bid_rss.parse(feed(ORIGINAL, AMENDMENT, another), now=NOW)
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["url"].split("bidID=")[1] for row in rows},
                         {"47", "48"})

    def test_scanner_uses_amended_deadline_without_claiming_verified_open(self):
        xml = feed(ORIGINAL, AMENDMENT)
        def fake_fetch(url, binary=False):
            if url == local_bid_rss.FEED_URL:
                return xml, "application/rss+xml", url
            return "<html></html>", "text/html", url
        source = {"name": "Elmira Next local bids",
                  "mode": "discovery_pending", "url": ""}
        with patch.object(scan, "fetch", side_effect=fake_fetch), \
             patch.object(scan, "NOW", NOW), \
             patch.object(scan, "scan_news", return_value=[]):
            _, status, leads = scan.run(source)
        self.assertIn("local bid RSS fetched", status)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["deadline"], "2026-11-04")
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertEqual(leads[0]["published"], "2026-10-31")


if __name__ == "__main__":
    unittest.main()
