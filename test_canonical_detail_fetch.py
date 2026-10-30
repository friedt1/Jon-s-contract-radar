"""Synthetic duplicate-link regressions; never live contract fixtures."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan
import source_health


SOURCE = {"name": "Test County", "url": "https://example.gov/bids",
          "mode": "direct_page", "verified_url": True}


class CanonicalDetailFetchTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(
            scan, "NOW", dt.datetime(2026, 10, 30, 11,
                                     tzinfo=dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def test_tracking_variants_do_not_repeat_pdf_fetch_or_merge_bid_ids(self):
        listing = (
            '<a href="/media/tree.pdf?bidID=102&utm_source=email">'
            'Tree removal bid 2026 packet</a>'
            '<a href="/media/tree.pdf?utm_medium=mail&bidID=102">'
            'Tree removal bid 2026 packet duplicate</a>'
            '<a href="/media/tree.pdf?bidID=102#details">'
            'Tree removal bid 2026 packet fragment</a>'
            '<a href="/media/tree.pdf?bidID=103">'
            'Tree removal bid 2026 different solicitation</a>'
        )
        requested = []

        def fake_fetch(url, binary=False):
            if url == SOURCE["url"]:
                return listing, "text/html", url
            requested.append(url)
            return b"%PDF synthetic", "application/pdf", url

        with patch.object(scan, "fetch", side_effect=fake_fetch), patch.object(
            scan, "pdf_text", return_value=(
                "Tree removal bid due November 19, 2026")
        ):
            leads, status = scan.scan_direct(SOURCE)

        self.assertEqual(len(requested), 2)
        self.assertEqual(len(leads), 2)
        self.assertEqual(len({x["id"] for x in leads}), 2)
        self.assertTrue(all(x["status"] == "unverified" for x in leads))
        self.assertIn("2 details checked", status)
        self.assertIn("2 PDF-shaped requests attempted", status)

    def test_duplicate_skipped_links_count_once_after_pdf_budget(self):
        listing = "".join(
            '<a href="/media/tree-%d.pdf?utm_source=mail">'
            'Tree removal bid 2026 packet %d</a>' % (n, n)
            for n in range(scan.MAX_PDF + 1)
        )
        listing += (
            '<a href="/media/tree-5.pdf?utm_campaign=duplicate">'
            'Tree removal bid 2026 packet 5 duplicate</a>'
        )
        requested = []

        def fake_fetch(url, binary=False):
            if url == SOURCE["url"]:
                return listing, "text/html", url
            requested.append(url)
            raise TimeoutError("synthetic inaccessible PDF")

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(SOURCE)

        self.assertEqual(leads, [])
        self.assertEqual(len(requested), scan.MAX_PDF)
        self.assertIn("5 PDF-shaped requests attempted", status)
        self.assertIn("1 PDF requests skipped at budget", status)
        health = source_health.classify(SOURCE, status)
        self.assertEqual(health["pdf_budget_skips"], 1)

    def test_expired_erie_and_unrelated_owego_stay_excluded(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            today=dt.date(2026, 10, 30)))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            today=dt.date(2026, 10, 30)))


if __name__ == "__main__":
    unittest.main()
