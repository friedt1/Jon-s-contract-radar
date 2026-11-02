"""Synthetic tree/stump wording regressions. Historical Erie is NOT a live bid."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan


class TreeStumpWordingTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(scan, "NOW", dt.datetime(
            2026, 10, 31, 10, 30, tzinfo=dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def test_tree_stump_and_brush_bid_variants_match_tree_removal(self):
        for wording in (
            "Tree & Stump Removal",
            "Trees & Stumps Removal",
            "Tree/Stump Removal",
            "Tree and Stumps Removal",
            "Tree & Brush Removal",
            "Tree/Brush Removal",
            "Tree and Vegetation Removal",
            "Tree & Vegetation Removal",
            "Tree/Vegetation Removal",
            "Removal of Trees and Vegetation",
        ):
            with self.subTest(wording=wording):
                self.assertEqual(scan.category(wording + " Bid"), "Tree removal")
                self.assertTrue(scan.eligible(
                    wording + " Bid due November 19, 2026",
                    today=dt.date(2026, 10, 31)))

    def test_historical_tioga_tree_vegetation_bid_is_not_live(self):
        # Historical Tioga County Emergency Services 2025 bid wording.
        self.assertEqual(scan.category("TREE AND VEGETATION REMOVAL BID"),
                         "Tree removal")
        self.assertFalse(scan.eligible(
            "TREE AND VEGETATION REMOVAL BID due July 17, 2025",
            today=dt.date(2026, 11, 1)))

    def test_historical_erie_is_expired_and_broad_pa_gate_still_applies(self):
        self.assertFalse(scan.eligible(
            "Erie PA Tree & Stump Removal Bid due October 29, 2026",
            today=dt.date(2026, 10, 31)))
        self.assertFalse(scan.eligible(
            "Erie PA Tree & Stump Removal Bid due November 19, 2026",
            source="PennBid platform", today=dt.date(2026, 10, 31)))
        self.assertIsNone(scan.category(
            "Owego building demolition and site restoration bid"))

    def test_public_pdf_variant_is_unverified_and_no_real_notice_seeded(self):
        source = {"name": "Synthetic County", "url": "https://county.example/bids",
                  "mode": "direct_page", "verified_url": True}
        pdf_url = "https://county.example/media/tree-stump.pdf"
        listing = ('<a href="/media/tree-stump.pdf">'
                   'Tree & Stump Removal Bid Proposal</a>')
        requested = []

        def fake_fetch(url, binary=False):
            requested.append(url)
            if url == source["url"]:
                return listing, "text/html", url
            if url == pdf_url:
                return b"FAKE_PDF", "application/pdf", url
            raise AssertionError("Unexpected fetch: " + url)

        with patch.object(scan, "fetch", side_effect=fake_fetch), patch.object(
            scan, "pdf_text",
            return_value="Tree & Stump Removal Bid due November 19, 2026"
        ):
            leads, status = scan.scan_direct(source)
        self.assertEqual(requested, [source["url"], pdf_url])
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["category"], "Tree removal")
        self.assertEqual(leads[0]["deadline"], "2026-11-19")
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertNotEqual(leads[0].get("open_status"), "verified_open")
        self.assertIn("direct fetched", status)


if __name__ == "__main__":
    unittest.main()
