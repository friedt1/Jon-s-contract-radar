"""Offline row-year PDF priority tests; synthetic URLs are not live bids."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan


BASE = "https://county.example/bids"
SOURCE = {"name": "Synthetic County", "url": BASE, "mode": "direct_page"}
NOW = dt.datetime(2026, 10, 31, 13, tzinfo=dt.timezone.utc)


class PdfRowYearPriorityTests(unittest.TestCase):
    def test_isolated_row_year_only_when_link_lacks_year(self):
        url = "https://county.example/media/document.pdf"
        self.assertEqual(scan.pdf_listing_recency(
            "Download PDF", url, 2026, "Tree removal bid posted 2026"), 3)
        self.assertEqual(scan.pdf_listing_recency(
            "Download PDF", url, 2026, "Tree removal bid posted 2024"), -6)
        self.assertEqual(scan.pdf_listing_recency(
            "Download PDF", url, 2026), 0)
        # An explicit link year outranks surrounding row text, which might
        # mention a newer addendum. The year is only a retrieval hint.
        self.assertEqual(scan.pdf_listing_recency(
            "2024 bid packet", url, 2026, "2026 addendum"), -6)
        self.assertEqual(scan.pdf_listing_recency(
            "Download PDF", "https://county.example/2025/bid.pdf",
            2026, "Tree removal 2026"), -6)

    def test_newer_row_pdf_is_checked_before_archive_under_pdf_cap(self):
        rows = [
            '<tr><td>Tree removal bid packet 2024</td>'
            f'<td><a href="/media/old-{i}.pdf">Download PDF</a></td></tr>'
            for i in range(8)
        ]
        rows.append(
            '<tr><td>Tree removal bid packet 2026</td>'
            '<td><a href="/media/current.pdf">Download PDF</a></td></tr>'
        )
        listing = "<table>" + "".join(rows) + "</table>"
        attempted = []

        def fake_fetch(url, binary=False):
            if url == BASE:
                return listing, "text/html", url
            attempted.append(url)
            raise TimeoutError("synthetic document unavailable")

        with (patch.object(scan, "NOW", NOW),
              patch.object(scan, "fetch", side_effect=fake_fetch)):
            leads, status = scan.scan_direct(SOURCE)

        self.assertEqual(leads, [])
        self.assertEqual(attempted[0], "https://county.example/media/current.pdf")
        self.assertEqual(len(attempted), scan.MAX_PDF)
        self.assertIn("5 PDF-shaped requests attempted", status)
        self.assertIn("4 PDF requests skipped at budget", status)

    def test_erie_and_owego_are_not_promoted(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            today=dt.date(2026, 10, 31)))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            today=dt.date(2026, 10, 31)))


if __name__ == "__main__":
    unittest.main()
