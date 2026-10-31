"""Offline PDF-budget fairness tests; synthetic URLs are never live bids."""
import datetime as dt
import unittest
from unittest.mock import patch

import detail_rotation
import scan


UTC = dt.timezone.utc
SOURCE = {"name": "Synthetic County", "url": "https://county.example/bids",
          "mode": "direct_page", "verified_url": True}


class PdfBudgetRotationTests(unittest.TestCase):
    def test_selected_rotation_preserves_html_slots_and_priority(self):
        items = [
            (10, "current-a.pdf"), (10, "html-a"),
            (10, "current-b.pdf"), (10, "html-b"),
            (10, "current-c.pdf"), (10, "current-d.pdf"),
            (10, "current-e.pdf"), (-10, "expired.pdf"),
        ]
        start = dt.datetime(2026, 10, 31, 10, tzinfo=UTC)
        seen = set()
        for hour in range(5):
            result = detail_rotation.rotate_selected_boundary_ties(
                items, 2, start + dt.timedelta(hours=hour),
                lambda row: row[0], lambda row: row[1].endswith(".pdf"))
            self.assertEqual(result[1], items[1])
            self.assertEqual(result[3], items[3])
            self.assertEqual(result[-1], items[-1])
            self.assertEqual(set(result), set(items))
            seen.update(row[1] for row in result if row[1].endswith(".pdf")
                        and row in [result[0], result[2]])
        self.assertEqual(seen, {"current-a.pdf", "current-b.pdf",
                                "current-c.pdf", "current-d.pdf",
                                "current-e.pdf"})

    def test_direct_archive_rotates_five_pdf_attempts_without_increasing_cap(self):
        listing = "".join(
            f'<a href="/docs/tree-{i}.pdf">Tree removal bid packet</a>'
            for i in range(12))
        start = dt.datetime(2026, 10, 31, 10, tzinfo=UTC)
        seen = set()
        for hour in range(4):
            attempted = []

            def fake_fetch(url, binary=False):
                if url == SOURCE["url"]:
                    return listing, "text/html", url
                attempted.append(url)
                raise TimeoutError("synthetic document timeout")

            with (patch.object(scan, "NOW", start + dt.timedelta(hours=hour)),
                  patch.object(scan, "fetch", side_effect=fake_fetch)):
                leads, status = scan.scan_direct(SOURCE)
            self.assertEqual(leads, [])
            self.assertEqual(len(attempted), scan.MAX_PDF)
            self.assertIn("5 PDF-shaped requests attempted", status)
            self.assertIn("7 PDF requests skipped at budget", status)
            seen.update(attempted)
        self.assertEqual(len(seen), 12)

    def test_nested_archive_rotates_tied_pdf_links(self):
        index = "https://county.example/procurement"
        listing = '<a href="/procurement">Current bids</a>'
        nested = "".join(
            f'<a href="/docs/tree-{i}.pdf">Tree removal bid packet</a>'
            for i in range(11))
        start = dt.datetime(2026, 10, 31, 10, tzinfo=UTC)
        seen = set()
        for hour in range(4):
            attempted = []

            def fake_fetch(url, binary=False):
                if url == SOURCE["url"]:
                    return listing, "text/html", url
                if url == index:
                    return nested.encode(), "text/html", url
                attempted.append(url)
                raise TimeoutError("synthetic document timeout")

            with (patch.object(scan, "NOW", start + dt.timedelta(hours=hour)),
                  patch.object(scan, "fetch", side_effect=fake_fetch)):
                leads, status = scan.scan_direct(SOURCE)
            self.assertEqual(leads, [])
            self.assertEqual(len(attempted), scan.MAX_PDF)
            self.assertIn("5 PDF-shaped requests attempted", status)
            self.assertIn("6 PDF requests skipped at budget", status)
            seen.update(attempted)
        self.assertEqual(len(seen), 11)

    def test_erie_expired_and_owego_demolition_remain_excluded(self):
        today = dt.date(2026, 10, 31)
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 29, 2026",
            today=today))
        self.assertFalse(scan.eligible(
            "Owego building demolition and site restoration bid due "
            "November 13, 2026", today=today))


if __name__ == "__main__":
    unittest.main()
