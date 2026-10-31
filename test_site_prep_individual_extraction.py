"""Offline regressions: related site prep is extractable from individual notices.

All examples are synthetic; none are real or verified-open procurement bids.
"""
import datetime as dt
import unittest
from unittest.mock import patch

import scan


SOURCE = {"name": "Test County", "url": "https://example.gov/bids", "mode": "direct_page"}
HTML_NOTICE = "https://example.gov/bid/site-grading"
PDF_NOTICE = "https://example.gov/media/2026/site-prep.pdf"


class SitePrepIndividualExtractionTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(
            scan, "NOW", dt.datetime(2026, 10, 30, 16, tzinfo=dt.timezone.utc)
        )
        clock.start()
        self.addCleanup(clock.stop)

    def scan_html(self, heading):
        listing = '<a href="/bid/site-grading">Site grading bid</a>'
        detail = "<h1>" + heading + "</h1>"

        def fake_fetch(url, binary=False):
            self.assertIn(url, (SOURCE["url"], HTML_NOTICE))
            body = listing if url == SOURCE["url"] else detail
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            return scan.scan_direct(SOURCE)

    def scan_pdf(self, extracted):
        listing = '<a href="/media/2026/site-prep.pdf">Site preparation bid</a>'

        def fake_fetch(url, binary=False):
            self.assertIn(url, (SOURCE["url"], PDF_NOTICE))
            if url == SOURCE["url"]:
                return listing, "text/html", url
            self.assertTrue(binary)
            return b"%PDF-1.4 synthetic", "application/pdf", url

        with (patch.object(scan, "fetch", side_effect=fake_fetch),
              patch.object(scan, "pdf_text", return_value=extracted)):
            return scan.scan_direct(SOURCE)

    def test_html_site_grading_notice_is_unverified_related_work(self):
        leads, status = self.scan_html(
            "Site grading bid due November 19, 2026"
        )
        self.assertEqual(len(leads), 1, status)
        self.assertEqual(leads[0]["url"], HTML_NOTICE)
        self.assertEqual(leads[0]["category"], "Related site prep")
        self.assertEqual(leads[0]["deadline"], "2026-11-19")
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertNotEqual(leads[0].get("open_status"), "verified_open")

    def test_pdf_site_preparation_notice_is_unverified_related_work(self):
        leads, status = self.scan_pdf(
            "Site preparation bid. Submission deadline November 19, 2026."
        )
        self.assertEqual(len(leads), 1, status)
        self.assertEqual(leads[0]["url"], PDF_NOTICE)
        self.assertEqual(leads[0]["category"], "Related site prep")
        self.assertEqual(leads[0]["lead_type"], "PDF bid candidate")
        self.assertEqual(leads[0]["status"], "unverified")

    def test_expired_site_prep_notices_are_not_published(self):
        html, _ = self.scan_html("Site grading bid due October 20, 2026")
        pdf, _ = self.scan_pdf(
            "Site preparation bid. Submission deadline October 20, 2026."
        )
        self.assertEqual(html, [])
        self.assertEqual(pdf, [])

    def test_owego_demolition_is_not_site_prep(self):
        html, _ = self.scan_html(
            "Owego building demolition and site preparation bid due November 19, 2026"
        )
        pdf, _ = self.scan_pdf(
            "Owego building demolition and site preparation bid. "
            "Submission deadline November 19, 2026."
        )
        self.assertEqual(html, [])
        self.assertEqual(pdf, [])


if __name__ == "__main__":
    unittest.main()
