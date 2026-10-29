"""Offline regressions for bounded PDF requests and truthful detail access health.

All notices are synthetic; none is a verified open opportunity.
"""
import datetime as dt
import unittest
from unittest.mock import patch

import scan
import source_health


SOURCE = {"name": "Test County", "url": "https://example.gov/bids",
          "mode": "direct_page", "verified_url": True}


class PdfRequestBudgetTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(scan, "NOW", dt.datetime(2026, 10, 28, 18,
                                                      tzinfo=dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def test_sixth_pdf_is_not_fetched_and_html_bid_still_examined(self):
        pdf_links = "".join(
            '<a href="/documents/tree-removal-bid-%d.pdf">Tree removal bid PDF %d</a>' % (n, n)
            for n in range(scan.MAX_PDF + 1)
        )
        notice = "https://example.gov/bid/55"
        listing = pdf_links + '<a href="/bid/55">Tree removal bid due 11/19/2026</a>'
        fetched = []

        def fake_fetch(url, binary=False):
            fetched.append(url)
            if url == SOURCE["url"]:
                return listing, "text/html", url
            if url.endswith(".pdf"):
                return b"%PDF-1.7 synthetic", "application/pdf", url
            if url == notice:
                return b"<h1>Tree removal bid due 11/19/2026</h1>", "text/html", url
            raise AssertionError("Unexpected request: " + url)

        with patch.object(scan, "fetch", side_effect=fake_fetch), patch.object(
            scan, "pdf_text", return_value=""
        ):
            leads, status = scan.scan_direct(SOURCE)

        self.assertEqual(len([url for url in fetched if url.endswith(".pdf")]),
                         scan.MAX_PDF)
        self.assertEqual(len(fetched), scan.MAX_PDF + 2)
        self.assertEqual([lead["url"] for lead in leads], [notice])
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("1 PDF requests skipped at budget", status)
        self.assertIn("6 details checked", status)


class DetailAccessHealthTests(unittest.TestCase):
    def test_listing_success_does_not_hide_detail_robots_block(self):
        status = ("direct fetched; 1 listing pages; 4 details checked; "
                  "0 individual bid details fetched; 0 PDFs checked; "
                  "2 detail errors: RobotsDenied,ValueError; "
                  "indirect RSS error: RobotsDenied")
        row = source_health.classify(SOURCE, status)
        self.assertEqual(row["direct_state"], "fetched_unverified")
        self.assertEqual(row["detail_access_state"], "robots_blocked")
        self.assertEqual(row["detail_errors"], 2)
        self.assertEqual(row["indirect_state"], "robots_blocked")
        summary = source_health.summarize([SOURCE], {SOURCE["name"]: status})
        self.assertEqual(summary["counts"]["detail_robots_blocked_sources"], 1)
        self.assertEqual(summary["counts"]["detail_errors"], 2)

    def test_indirect_block_does_not_imply_detail_block(self):
        status = ("direct fetched; 1 listing pages; 0 details checked; "
                  "0 individual bid details fetched; 0 PDF requests skipped at budget; "
                  "indirect RSS error: RobotsDenied")
        row = source_health.classify(SOURCE, status)
        self.assertEqual(row["detail_access_state"], "not_attempted")
        self.assertEqual(row["pdf_budget_skips"], 0)

    def test_partial_detail_errors_and_pdf_budget_are_counted(self):
        status = ("direct fetched; 1 listing pages; 7 details checked; "
                  "2 individual bid details fetched; 5 PDFs checked; "
                  "3 PDF requests skipped at budget; 1 detail errors: TimeoutError")
        row = source_health.classify(SOURCE, status)
        self.assertEqual(row["detail_access_state"], "partial_fetch_errors")
        self.assertEqual(row["detail_errors"], 1)
        self.assertEqual(row["pdf_budget_skips"], 3)
        summary = source_health.summarize([SOURCE], {SOURCE["name"]: status})
        self.assertEqual(summary["counts"]["pdf_budget_skips"], 3)


if __name__ == "__main__":
    unittest.main()
