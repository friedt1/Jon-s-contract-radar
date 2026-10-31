"""Offline regression: repeated hrefs must retain each row's bid evidence.

Synthetic HTML only. No external source is fetched or notice published as live.
"""
import datetime as dt
import unittest
from unittest.mock import patch

import scan


class DuplicateHrefRowEvidenceTests(unittest.TestCase):
    def test_duplicate_href_keeps_each_distinct_row_context(self):
        html = (
            '<table><tr><td>Tree removal bid due November 19, 2026</td>'
            '<td><a href="/document?id=42">Details</a></td></tr>'
            '<tr><td>Office supplies procurement</td>'
            '<td><a href="/document?id=42">Details</a></td></tr></table>'
        )
        page = scan.parse_html(html)
        self.assertEqual(len(page.links), 2)
        self.assertEqual(page.links[0][1], page.links[1][1])
        self.assertIn("Tree removal bid", page.link_contexts[0])
        self.assertIn("Office supplies", page.link_contexts[1])
        self.assertNotIn("Office supplies", page.link_contexts[0])

    def test_later_unrelated_duplicate_cannot_hide_tree_notice(self):
        base = "https://example.gov/bids"
        notice = "https://example.gov/document?id=42"
        listing = (
            '<table><tr><td>Tree removal bid due November 19, 2026</td>'
            '<td><a href="/document?id=42">Details</a></td></tr>'
            '<tr><td>Office supplies</td>'
            '<td><a href="/document?id=42">Details</a></td></tr></table>'
        )
        fetched = []
        def fake_fetch(url, binary=False):
            fetched.append(url)
            body = listing if url == base else (
                "<h1>Tree removal bid due November 19, 2026</h1>"
            )
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "NOW", dt.datetime(
                2026, 10, 30, 20, tzinfo=dt.timezone.utc)), \
             patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct({
                "name": "Test County", "url": base, "mode": "direct_page"
            })
        self.assertEqual(fetched, [base, notice])
        self.assertEqual([item["url"] for item in leads], [notice])
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("1 details checked", status)


if __name__ == "__main__":
    unittest.main()
