"""Synthetic HTML regression cases; no real bids are seeded or verified."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan


SOURCE = {"name": "Test County", "url": "https://example.gov/bids",
          "mode": "direct_page"}
DETAIL = "https://example.gov/bids/tree-removal-2026"
LISTING = '<a href="/bids/tree-removal-2026">View details</a>'


class ListBackedNoticeTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(
            scan, "NOW", dt.datetime(2026, 10, 29, 12,
                                     tzinfo=dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def run_notice(self, body):
        def fake_fetch(url, binary=False):
            if url == SOURCE["url"]:
                html = LISTING
            elif url == DETAIL:
                html = body
            else:
                raise AssertionError("unexpected URL: " + url)
            return (html.encode() if binary else html, "text/html", url)
        with patch.object(scan, "fetch", side_effect=fake_fetch):
            return scan.scan_direct(SOURCE)

    def test_list_backed_individual_bid_is_review_candidate(self):
        html = ('<h1>Tree removal bid</h1><ul>'
                '<li>Bids due November 20, 2026</li>'
                '<li>Remove hazardous trees along county roads</li></ul>')
        leads, diagnostic = self.run_notice(html)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["url"], DETAIL)
        self.assertEqual(leads[0]["deadline"], "2026-11-20")
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("1 individual bid details fetched", diagnostic)

    def test_navigation_tree_words_cannot_make_unrelated_notice_relevant(self):
        html = ('<nav><a href="/trees">Tree removal</a></nav>'
                '<h1>Computer equipment bid</h1><ul>'
                '<li>Bids due November 20, 2026</li></ul>')
        leads, _ = self.run_notice(html)
        self.assertEqual(leads, [])

    def test_undated_list_backed_heading_requires_submission_evidence(self):
        html = ('<h1>Tree removal bid</h1><ul>'
                '<li>Questions due November 20, 2026</li>'
                '<li>Pre-bid site visit November 10, 2026</li></ul>')
        leads, _ = self.run_notice(html)
        self.assertEqual(leads, [])

    def test_expired_list_backed_notice_does_not_publish(self):
        html = ('<h1>Tree removal bid</h1><ul>'
                '<li>Bids due October 27, 2026</li></ul>')
        leads, _ = self.run_notice(html)
        self.assertEqual(leads, [])

    def test_bid_index_with_nested_notice_is_not_promoted(self):
        index = ('<h1>Tree removal bid listings</h1><ul>'
                 '<li>Bids due November 20, 2026 '
                 '<a href="/bids/tree-removal-2026">View details</a></li>'
                 '</ul>')
        leads, diagnostic = self.run_notice(index)
        self.assertEqual(leads, [])
        self.assertIn("nested listing pages excluded as notices", diagnostic)

    def test_historical_regression_cases_do_not_become_live(self):
        erie = "Erie PA tree and stump removal bid due 10/29/2026"
        owego = "Owego NY demolition rebid due 11/13/2026"
        self.assertFalse(scan.eligible(erie, "PennBid platform"))
        self.assertIsNone(scan.category(owego))


if __name__ == "__main__":
    unittest.main()
