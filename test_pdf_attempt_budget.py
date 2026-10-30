"""Synthetic PDF network-budget regressions; no real opportunities are seeded."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan
import source_health


SOURCE = {"name": "Test County", "url": "https://example.gov/bids",
          "mode": "direct_page", "verified_url": True}


class PdfNetworkBudgetTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(scan, "NOW", dt.datetime(
            2026, 10, 30, 10, 30, tzinfo=dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def test_failed_pdf_downloads_still_consume_request_budget(self):
        # The old scanner counted only successfully fetched PDFs. Eight
        # timeouts could therefore trigger eight network requests despite
        # MAX_PDF=5. Duplicate skipped links should not inflate diagnostics.
        links = "".join(
            '<a href="/media/tree-%d.pdf">Tree removal bid 2026 packet %d</a>'
            % (i, i) for i in range(scan.MAX_PDF + 3)
        )
        links += ('<a href="/media/tree-7.pdf">'
                  'Tree removal bid 2026 packet 7 duplicate</a>')
        attempted = []

        def fake_fetch(url, binary=False):
            if url == SOURCE["url"]:
                return links, "text/html", url
            attempted.append(url)
            raise TimeoutError("synthetic PDF timeout")

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(SOURCE)

        self.assertEqual(leads, [])
        self.assertEqual(len(attempted), scan.MAX_PDF)
        self.assertIn("5 PDF-shaped requests attempted", status)
        self.assertIn("3 PDF requests skipped at budget", status)
        self.assertIn("5 detail errors: TimeoutError", status)
        health = source_health.classify(SOURCE, status)
        self.assertEqual(health["pdf_fetch_attempts"], scan.MAX_PDF)
        self.assertEqual(health["pdf_budget_skips"], 3)
        self.assertEqual(
            source_health.summarize([SOURCE], {SOURCE["name"]: status})
            ["counts"]["pdf_fetch_attempts"], scan.MAX_PDF)

    def test_opaque_agency_pdf_errors_are_bounded_too(self):
        # Synthetic Tioga media and CivicPlus DocumentCenter URLs, not bids.
        paths = ["/media/opaque-%d" % i for i in range(4)]
        paths += ["/DocumentCenter/View/%d" % i for i in range(5)]
        listing = "".join(
            '<a href="%s">Tree removal bid 2026 proposal</a>' % path
            for path in paths)
        requested = []

        def fake_fetch(url, binary=False):
            if url == SOURCE["url"]:
                return listing, "text/html", url
            requested.append(url)
            raise OSError("synthetic unavailable document")

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(leads, [])
        self.assertEqual(len(requested), scan.MAX_PDF)
        self.assertIn("4 PDF requests skipped at budget", status)

    def test_expired_erie_and_unrelated_owego_are_not_live(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            today=dt.date(2026, 10, 30)))
        self.assertFalse(scan.eligible(
            "Owego building demolition and site restoration bid due "
            "November 13, 2026", today=dt.date(2026, 10, 30)))


if __name__ == "__main__":
    unittest.main()
