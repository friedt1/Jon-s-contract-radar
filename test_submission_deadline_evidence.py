"""Offline regression tests; these synthetic examples are not live contracts."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan
from submission_deadlines import submission_deadline


class SubmissionDateTests(unittest.TestCase):
    def test_questions_cannot_extend_bid_deadline(self):
        text = ("Tree removal bid due 10/28/2026; "
                "Questions due 11/20/2026; "
                "Site visit due 11/10/2026")
        self.assertEqual(submission_deadline(text), "2026-10-28")

    def test_questions_only_never_become_submission_date(self):
        for text in (
            "Tree removal bid. Questions due 11/20/2026.",
            "Tree removal RFP. Deadline for questions 11/20/2026.",
            "Tree removal bid. Clarifications due November 20, 2026.",
            "Tree removal bid. Pre-bid meeting due 11/20/2026.",
            "Tree removal bid. Addenda due 11/20/2026.",
        ):
            with self.subTest(text=text):
                self.assertEqual(submission_deadline(text), "")

    def test_submission_formats_and_amendment(self):
        for text in (
            "Tree removal bids due 11/02/2026",
            "Tree removal bid Closing Date/Time: 11/02/2026 2:00 PM",
            "Tree removal bids received until Nov 2, 2026",
            "Tree removal submission deadline November 2, 2026",
        ):
            with self.subTest(text=text):
                self.assertEqual(submission_deadline(text), "2026-11-02")
        self.assertEqual(submission_deadline(
            "Tree removal bid due 11/02/2026; amended bid due 11/09/2026"),
            "2026-11-09")

    def test_erie_and_owego_examples_remain_non_live(self):
        erie = "Erie PA tree and stump removal bid due 10/29/2026"
        owego = "Owego NY demolition rebid due 11/13/2026"
        self.assertEqual(submission_deadline(erie), "2026-10-29")
        self.assertFalse(scan.eligible(erie, "PennBid platform"))
        self.assertIsNone(scan.category(owego))


class DetailProofTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(
            scan, "NOW", dt.datetime(2026, 10, 29, 12, tzinfo=dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def run_detail(self, detail):
        base = "https://example.gov/bids"
        notice = "https://example.gov/bid/1"

        def fake_fetch(url, binary=False):
            if url == base:
                body = '<a href="/bid/1">Tree removal bid due 11/20/2026</a>'
            elif url == notice:
                body = detail
            else:
                raise AssertionError("unexpected URL")
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            return scan.scan_direct({"name": "Test County", "url": base,
                                     "mode": "direct_page"})

    def test_non_bid_detail_does_not_inherit_listing_bid_label(self):
        leads, diagnostic = self.run_detail(
            "<h1>Tree removal safety training and information</h1>")
        self.assertEqual(leads, [])
        self.assertIn("1 details checked", diagnostic)

    def test_real_bid_word_on_detail_can_be_unverified_candidate(self):
        leads, _ = self.run_detail(
            "<h1>Tree removal bid due 11/20/2026</h1>")
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["status"], "unverified")

    def test_bid_specific_metadata_proves_bid_context(self):
        leads, _ = self.run_detail(
            "<div>Bid Number: 1001 Description: Tree removal "
            "Closing Date/Time: 11/20/2026</div>")
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["deadline"], "2026-11-20")
        self.assertEqual(leads[0]["status"], "unverified")


if __name__ == "__main__":
    unittest.main()
