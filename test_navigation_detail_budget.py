"""Synthetic bid navigation fixtures: only bid evidence should use detail budget.

No fixture is a live opportunity and no external source is contacted.
"""
import datetime as dt
import unittest
from unittest.mock import patch

import scan

SOURCE = {"name": "Test County", "url": "https://example.gov/bids", "mode": "direct_page"}


class NavigationBudgetTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(scan, "NOW", dt.datetime(2026, 10, 28, 18, tzinfo=dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def run_pages(self, pages):
        requested = []

        def fake(url, binary=False):
            requested.append(url)
            body = pages[url]
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "fetch", side_effect=fake):
            leads, status = scan.scan_direct(SOURCE)
        return leads, status, requested

    def test_navigation_links_do_not_starve_a_generic_bid_link(self):
        nav = "".join('<a href="/page/%d">View details</a>' % n for n in range(60))
        notice = "https://example.gov/bid/42"
        leads, status, requested = self.run_pages({
            SOURCE["url"]: nav + '<a href="/bid/42">Details</a>',
            notice: "<h1>Tree removal bid due November 19, 2026</h1>",
        })
        self.assertEqual(requested, [SOURCE["url"], notice])
        self.assertEqual([lead["url"] for lead in leads], [notice])
        self.assertIn("1 details checked", status)
        self.assertEqual(leads[0]["status"], "unverified")

    def test_generic_label_with_isolated_bid_row_still_follows_notice(self):
        detail = "https://example.gov/document?id=42"
        leads, status, requested = self.run_pages({
            SOURCE["url"]: ('<table><tr><td>Tree trimming bid due 11/19/2026</td>'
                            '<td><a href="/document?id=42">Details</a></td></tr></table>'),
            detail: "<h1>Tree trimming bid due 11/19/2026</h1>",
        })
        self.assertEqual(requested, [SOURCE["url"], detail])
        self.assertEqual([lead["url"] for lead in leads], [detail])
        self.assertIn("1 details checked", status)

    def test_generic_label_on_purchasing_index_preserves_nested_bid(self):
        index = "https://example.gov/purchasing"
        notice = "https://example.gov/bid/55"
        leads, status, requested = self.run_pages({
            SOURCE["url"]: '<a href="/purchasing">View details</a>',
            index: ('<table><tr><td>Tree removal bid due 11/19/2026</td>'
                    '<td><a href="/bid/55">Details</a></td></tr></table>'),
            notice: "<h1>Tree removal bid due 11/19/2026</h1>",
        })
        self.assertEqual(requested, [SOURCE["url"], index, notice])
        self.assertEqual([lead["url"] for lead in leads], [notice])
        self.assertIn("2 details checked", status)


if __name__ == "__main__":
    unittest.main()
