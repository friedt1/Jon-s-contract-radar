"""Offline Tioga-style PDF archive regressions. No fixture is a live bid."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan
import source_health


SOURCE = {"name": "Test County", "url": "https://example.gov/public-works",
          "mode": "direct_page", "verified_url": True}


class PdfArchivePriorityTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(scan, "NOW", dt.datetime(
            2026, 10, 30, 8, 40, tzinfo=dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def test_tioga_style_result_tabs_are_not_live_bid_candidates(self):
        for label in (
            "Tree Removal 2026 Bid Results",
            "Guiderail Vegetation Control 2026 Bid Tab",
            "Notice of Award",
            "Tree Removal Bid Tabulation",
        ):
            with self.subTest(label=label):
                self.assertTrue(scan.published_result_link(label))
        self.assertFalse(scan.published_result_link("Tree Removal 2026 Bid Proposal"))
        self.assertFalse(scan.published_result_link("Tree removal bid addendum"))

    def test_current_year_pdf_is_checked_before_old_archive_and_results_ignored(self):
        older = "".join(
            '<a href="/media/old-%d.pdf">Tree removal bid 2024 proposal %d</a>' % (n, n)
            for n in range(12)
        )
        current = "https://example.gov/media/tree-2026.pdf"
        result = "https://example.gov/media/opaque-result.pdf"
        demolition = "https://example.gov/media/demolition-2026.pdf"
        listing = (
            older
            + '<a href="/media/opaque-result.pdf">Tree Removal 2026 Bid Results</a>'
            + '<a href="/media/demolition-2026.pdf">Owego demolition bid 2026</a>'
            + '<a href="/media/tree-2026.pdf">Tree removal bid 2026 proposal</a>'
        )
        requested = []

        def fake_fetch(url, binary=False):
            requested.append(url)
            if url == SOURCE["url"]:
                return listing, "text/html", url
            if url == current:
                return b"CURRENT", "application/pdf", url
            if url == demolition:
                return b"DEMOLITION", "application/pdf", url
            if "/media/old-" in url:
                return b"OLD", "application/pdf", url
            raise AssertionError("Unexpected URL: " + url)

        def fake_pdf_text(blob):
            if blob == b"CURRENT":
                return "Tree removal bid due November 19, 2026"
            if blob == b"OLD":
                return "Tree removal bid due April 17, 2024"
            if blob == b"DEMOLITION":
                return "Owego demolition and site restoration bid due November 13, 2026"
            raise AssertionError("Unexpected PDF")

        with patch.object(scan, "fetch", side_effect=fake_fetch), patch.object(
            scan, "pdf_text", side_effect=fake_pdf_text
        ):
            leads, status = scan.scan_direct(SOURCE)

        self.assertEqual(requested[1], current)
        self.assertNotIn(result, requested)
        self.assertEqual([lead["url"] for lead in leads], [current])
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("1 result/award links excluded", status)
        self.assertIn("PDF requests skipped at budget", status)
        self.assertLessEqual(len([url for url in requested if url.endswith(".pdf")]),
                             scan.MAX_PDF)
        row = source_health.classify(SOURCE, status)
        self.assertEqual(row["result_award_links_excluded"], 1)
        self.assertEqual(source_health.summarize(
            [SOURCE], {SOURCE["name"]: status}
        )["counts"]["result_award_links_excluded"], 1)

    def test_expired_tree_bid_and_opaque_results_pdf_never_promoted(self):
        result = "https://example.gov/media/opaque.pdf"
        old_bid = "https://example.gov/media/tree-2026.pdf"
        listing = (
            '<a href="/media/opaque.pdf">Tree Removal 2026 Bid Results</a>'
            '<a href="/media/tree-2026.pdf">Tree Removal 2026 Bid Proposal</a>'
        )
        requested = []

        def fake_fetch(url, binary=False):
            requested.append(url)
            if url == SOURCE["url"]:
                return listing, "text/html", url
            if url == old_bid:
                return b"OLD_BID", "application/pdf", url
            raise AssertionError("Results PDF must not be fetched: " + url)

        with patch.object(scan, "fetch", side_effect=fake_fetch), patch.object(
            scan, "pdf_text", return_value="Tree removal bid due April 17, 2026"
        ):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(leads, [])
        self.assertEqual(requested, [SOURCE["url"], old_bid])
        self.assertIn("1 result/award links excluded", status)


    def test_opaque_media_pdfs_respect_budget_and_current_year_priority(self):
        # Synthetic Tioga-style opaque URLs; not real solicitations.
        current = "https://example.gov/media/current-document"
        old = ["https://example.gov/media/opaque-" + str(n) for n in range(7)]
        listing = "".join(
            '<a href="/media/opaque-%d">Tree removal bid 2024 proposal %d</a>' % (n, n)
            for n in range(7)
        ) + '<a href="/media/current-document">Tree removal bid 2026 proposal</a>'
        requested = []

        def fake_fetch(url, binary=False):
            requested.append(url)
            if url == SOURCE["url"]:
                return listing, "text/html", url
            if url == current:
                return b"CURRENT", "application/pdf", url
            if url in old:
                return b"OLD", "application/pdf", url
            raise AssertionError("Unexpected URL: " + url)

        def fake_pdf_text(blob):
            if blob == b"CURRENT":
                return "Tree removal bid due November 19, 2026"
            return "Tree removal bid due April 17, 2024"

        with patch.object(scan, "fetch", side_effect=fake_fetch), patch.object(
            scan, "pdf_text", side_effect=fake_pdf_text
        ):
            leads, status = scan.scan_direct(SOURCE)

        self.assertEqual(requested[1], current)
        self.assertEqual(len(requested), 1 + scan.MAX_PDF)
        self.assertEqual([lead["url"] for lead in leads], [current])
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("3 PDF requests skipped at budget", status)

    def test_documentcenter_opaque_pdfs_do_not_bypass_request_cap(self):
        # Common municipal DocumentCenter/View/123 URLs lack a .pdf suffix.
        links = "".join(
            '<a href="/DocumentCenter/View/%d">Tree removal bid 2024 packet</a>' % n
            for n in range(7)
        )
        requested = []

        def fake_fetch(url, binary=False):
            requested.append(url)
            if url == SOURCE["url"]:
                return links, "text/html", url
            return b"OLD", "application/pdf", url

        with patch.object(scan, "fetch", side_effect=fake_fetch), patch.object(
            scan, "pdf_text", return_value="Tree removal bid due April 17, 2024"
        ):
            leads, status = scan.scan_direct(SOURCE)

        self.assertEqual(leads, [])
        self.assertEqual(len(requested), 1 + scan.MAX_PDF)
        self.assertIn("2 PDF requests skipped at budget", status)
        self.assertTrue(scan.likely_pdf_link(
            "https://example.gov/DocumentCenter/View/123", "Tree removal bid packet"))
        self.assertFalse(scan.likely_pdf_link(
            "https://example.gov/purchasing", "Current bids"))


    def test_undated_archive_labels_use_document_path_year_not_opaque_id(self):
        # Synthetic archive: labels do not contain dates, but directory paths do.
        # Current-year proposals must be checked before expired archived packets.
        older = "".join(
            '<a href="/bids/2024/tree-%d.pdf">Tree removal bid proposal</a>' % n
            for n in range(7)
        )
        current = "https://example.gov/bids/2026/tree-packet.pdf"
        listing = older + '<a href="/bids/2026/tree-packet.pdf">Tree removal bid proposal</a>'
        requested = []

        def fake_fetch(url, binary=False):
            requested.append(url)
            if url == SOURCE["url"]:
                return listing, "text/html", url
            if url == current:
                return b"CURRENT", "application/pdf", url
            if "/bids/2024/" in url:
                return b"OLD", "application/pdf", url
            raise AssertionError("Unexpected URL: " + url)

        def fake_pdf_text(blob):
            return ("Tree removal bid due November 19, 2026" if blob == b"CURRENT"
                    else "Tree removal bid due April 17, 2024")

        with patch.object(scan, "fetch", side_effect=fake_fetch), patch.object(
            scan, "pdf_text", side_effect=fake_pdf_text
        ):
            leads, status = scan.scan_direct(SOURCE)

        self.assertEqual(requested[1], current)
        self.assertEqual([lead["url"] for lead in leads], [current])
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("3 PDF requests skipped at budget", status)
        self.assertEqual(len(requested), 1 + scan.MAX_PDF)
        # A numeric document ID or bidID query parameter is not a year.
        self.assertEqual(scan.pdf_listing_recency(
            "Tree removal bid packet",
            "https://example.gov/DocumentCenter/View/2026", 2026), 0)
        self.assertEqual(scan.pdf_listing_recency(
            "Tree removal bid packet",
            "https://example.gov/media/opaque?bidID=2026", 2026), 0)
        # An explicit publisher label takes precedence over a path year.
        self.assertEqual(scan.pdf_listing_recency(
            "Tree removal bid 2024 proposal",
            "https://example.gov/bids/2026/tree-packet.pdf", 2026), -6)


if __name__ == "__main__":
    unittest.main()
