"""Offline historical-PDF row filtering tests; no live bid data."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan


BASE = "https://agency.example/procurement"
SOURCE = {"name": "Synthetic Procurement", "url": BASE, "mode": "direct_page"}


class HistoricalPdfRowTests(unittest.TestCase):
    def test_generic_result_pdf_is_historical_only_with_isolated_row(self):
        url = "https://agency.example/media/123.pdf"
        self.assertTrue(scan.historical_pdf_row(
            "Download PDF", "Bid Results: tree and stump removal 2024", url))
        self.assertFalse(scan.historical_pdf_row(
            "Download PDF", "Tree removal bid packet 2026", url))
        self.assertFalse(scan.historical_pdf_row(
            "Download PDF", "Bid Results and current bid invitation to bid", url))
        self.assertFalse(scan.historical_pdf_row(
            "Tree removal bid specifications", "Bid Results 2024", url))
        self.assertFalse(scan.historical_pdf_row(
            "Download PDF", "Bid Results 2024", "https://agency.example/bid/123"))

    def test_result_rows_do_not_exhaust_five_pdf_slots(self):
        archive = "".join(
            f'<tr><td>Bid Results: tree removal 2024</td>'
            f'<td><a href="/media/result-{i}.pdf">Download PDF</a></td></tr>'
            for i in range(30))
        current = (
            '<tr><td>Tree and stump removal bid 2026</td>'
            '<td><a href="/media/current.pdf">Download PDF</a></td></tr>')
        attempted = []

        def fake_fetch(url, binary=False):
            if url == BASE:
                return "<table>" + archive + current + "</table>", "text/html", url
            attempted.append(url)
            raise TimeoutError("synthetic unavailable document")

        now = dt.datetime(2026, 11, 5, 10, tzinfo=dt.timezone.utc)
        with (patch.object(scan, "NOW", now),
              patch.object(scan, "fetch", side_effect=fake_fetch)):
            leads, status = scan.scan_direct(SOURCE)

        self.assertEqual(leads, [])
        self.assertEqual(attempted, ["https://agency.example/media/current.pdf"])
        self.assertIn("30 result/award links excluded", status)

    def test_expired_erie_and_unrelated_owego_not_live(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            today=dt.date(2026, 11, 5)))
        self.assertFalse(scan.eligible(
            "Owego demolition of vacant building; tree removal by others "
            "due November 20, 2026", today=dt.date(2026, 11, 5)))


if __name__ == "__main__":
    unittest.main()
