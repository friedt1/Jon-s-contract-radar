"""Nested public bid indexes must not spend the detail budget on unsafe links.

All pages and notices here are synthetic. No real opportunity is seeded.
"""
import datetime as dt
import unittest
from unittest.mock import patch

import scan


BASE = "https://example.gov/bids"
INDEX = "https://example.gov/procurement"
NOTICE = "https://example.gov/bid/55"
SOURCE = {"name": "Test County", "url": BASE, "mode": "direct_page"}


class NestedDetailBudgetTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(
            scan, "NOW", dt.datetime(2026, 10, 28, 18, tzinfo=dt.timezone.utc)
        )
        clock.start()
        self.addCleanup(clock.stop)

    def scan_pages(self, nested):
        fetched = []
        pages = {
            BASE: '<a href="/procurement">Current bids</a>',
            INDEX: nested,
            NOTICE: "<h1>Tree removal bid due November 19, 2026</h1>",
        }

        def fake_fetch(url, binary=False):
            fetched.append(url)
            if url not in pages:
                raise AssertionError("Unapproved or irrelevant fetch: " + url)
            body = pages[url]
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(SOURCE)
        return leads, status, fetched

    def test_provider_and_archive_links_cannot_starve_real_notice(self):
        # The first 20 links are invalid or explicitly excluded. Previously
        # they filled the 18-item nested budget with empty/archived URLs.
        off_host = "".join(
            '<a href="https://pennbid.bonfirehub.com/bid/%d">Tree removal bid</a>' % n
            for n in range(10)
        )
        archive = "".join(
            '<a href="/archive/tree-removal-bid-%d">Tree removal bid</a>' % n
            for n in range(10)
        )
        nested = (
            "<table><tr><td>Tree removal bid due 11/19/2026</td>"
            + off_host + archive
            + '<td><a href="/bid/55">Details</a></td></tr></table>'
        )
        leads, status, fetched = self.scan_pages(nested)
        self.assertEqual(fetched, [BASE, INDEX, NOTICE])
        self.assertEqual([lead["url"] for lead in leads], [NOTICE])
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("2 details checked", status)
        self.assertIn("10 external provider links skipped (access required)", status)

    def test_same_page_fragment_does_not_consume_nested_budget(self):
        anchors = "".join(
            '<a href="#note-%d">Tree removal bid details</a>' % n
            for n in range(25)
        )
        nested = (
            "<table><tr><td>Tree removal bid due 11/19/2026</td>"
            + anchors
            + '<td><a href="/bid/55">Details</a></td></tr></table>'
        )
        leads, _, fetched = self.scan_pages(nested)
        self.assertEqual(fetched, [BASE, INDEX, NOTICE])
        self.assertEqual([lead["url"] for lead in leads], [NOTICE])


if __name__ == "__main__":
    unittest.main()
