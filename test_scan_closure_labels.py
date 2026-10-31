"""Synthetic scanner closure regressions; none are actual live solicitations."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan


class ScannerClosureLabelTests(unittest.TestCase):
    TODAY = dt.date(2026, 10, 29)

    def test_question_only_status_does_not_close_bidding(self):
        for label in (
            "Status: Closed for questions",
            "Status: Closed - for questions",
            "Status: Closed: Q&A",
            "Status: Closed (questions)",
            "Status is Closed – to inquiries",
            "Status: Closed for RFIs",
            "Status: Closed for addenda",
        ):
            with self.subTest(label=label):
                self.assertFalse(scan.closed(label))
                self.assertTrue(scan.eligible(
                    "Tree and stump removal bid. " + label,
                    source="Chemung County bids", today=self.TODAY))

    def test_actual_submission_closure_still_excludes(self):
        for label in (
            "Status: Closed",
            "Status: Closed - no longer accepting bids",
            "Bids are closed",
            "Bid is closed",
            "Closed for bids",
            "Status: Closed for questions; bids are closed",
            "Status: Awarded",
        ):
            with self.subTest(label=label):
                self.assertTrue(scan.closed(label))
                self.assertFalse(scan.eligible(
                    "Tree removal bid. " + label,
                    source="Chemung County bids", today=self.TODAY))

    def test_publisher_withdrawal_and_rescission_exclude_tree_bids(self):
        for label in (
            "Status: Withdrawn",
            "Status is Rescinded",
            "Bid status: Withdrawn (reissued later)",
            "Tree removal solicitation has been withdrawn",
            "RFP was rescinded by the issuing agency",
            "Withdrawn solicitation",
            "Bid withdrawn",
            "Status: Rescinded",
        ):
            with self.subTest(label=label):
                self.assertTrue(scan.closed(label))
                self.assertFalse(scan.eligible(
                    "Erie tree and stump removal bid. Due November 13, 2026. " + label,
                    source="Test County", today=self.TODAY))

    def test_bid_intake_ended_without_closed_status_excludes_candidates(self):
        # Synthetic publisher wording only, never real/open bid records.
        for label in (
            "Agency is no longer accepting bids",
            "No longer accepting new sealed bids",
            "No longer accepting proposals",
            "Bids are no longer being accepted",
            "Proposals are no longer accepted",
            "Bid intake has ended",
            "Bid submission window has closed",
            "Proposal submission period has ended",
        ):
            with self.subTest(label=label):
                text = "Tree removal bid due November 13, 2026. " + label
                self.assertTrue(scan.closed(label))
                self.assertFalse(scan.eligible(text, today=self.TODAY))
                found = {}
                scan.add_lead(found, "Synthetic County", text,
                              "https://example.gov/bids/closed-notice")
                self.assertEqual(found, {})

    def test_questions_and_future_acceptance_cutoff_are_not_closed_intake(self):
        for label in (
            "No longer accepting questions",
            "Questions are no longer being accepted",
            "Bid submission window remains open",
            "Bids will no longer be accepted after November 13, 2026",
            "Bids will be accepted until November 13, 2026",
        ):
            with self.subTest(label=label):
                self.assertFalse(scan.closed(label))
                self.assertTrue(scan.eligible(
                    "Tree removal bid due November 13, 2026. " + label,
                    today=self.TODAY))

    def test_future_award_and_cancellation_boilerplate_does_not_close_bid(self):
        # An individual bid packet may describe how a contract *will* be
        # awarded or cancelled. Those conditions are not a final agency
        # decision and must not suppress an otherwise eligible notice.
        for clause in (
            "The contract will be awarded to the lowest responsible bidder.",
            "The agency reserves the right to cancel this procurement.",
            "The bid may be cancelled if funding is unavailable.",
            "Bidders must submit current insurance; expired insurance is unacceptable.",
            "An award notice will be published after bid opening.",
            "Bid results will be available following the submission deadline.",
            "Bids closed for questions; submissions remain open.",
            "Bidding closed for questions only; bids are still accepted.",
        ):
            with self.subTest(clause=clause):
                text = "Tree removal bid due November 13, 2026. " + clause
                self.assertFalse(scan.closed(text))
                self.assertTrue(scan.eligible(text, today=self.TODAY))
                found = {}
                scan.add_lead(found, "Synthetic County", text,
                              "https://example.gov/bids/tree-notice")
                self.assertEqual(len(found), 1)
                self.assertEqual(next(iter(found.values()))["status"], "unverified")

    def test_completed_award_and_cancellation_remain_closed(self):
        for label in (
            "Awarded",
            "Bid results",
            "Award notice",
            "Bid status: Awarded",
            "Solicitation status: Cancelled",
            "Contract has been awarded",
            "Bid was canceled",
            "RFP expired",
            "Bids are closed for submissions",
        ):
            with self.subTest(label=label):
                self.assertTrue(scan.closed(label))
                self.assertFalse(scan.eligible(
                    "Tree removal bid due November 13, 2026. " + label,
                    today=self.TODAY))

    def test_one_vendor_withdrawing_offer_does_not_close_procurement(self):
        self.assertTrue(scan.closed("Rescinded"))
        text = ("Tree removal bid due November 13, 2026. "
                "Contractor A withdrew its bid; agency is still accepting offers.")
        self.assertFalse(scan.closed(text))
        self.assertTrue(scan.eligible(text, today=self.TODAY))
        self.assertFalse(scan.closed("Status: Closed for questions"))

    def test_withdrawn_pdf_and_individual_html_notice_are_not_candidates(self):
        src = {"name": "Test County", "url": "https://example.gov/bids",
               "mode": "direct_page"}
        listing = ('<a href="/media/erie-tree.pdf">Erie tree and stump removal bid</a>'
                   '<a href="/bids/erie-tree">Tree removal bid details</a>'
                   '<a href="/bids/owego-demolition">Owego demolition bid</a>')
        pdf_url = "https://example.gov/media/erie-tree.pdf"
        html_url = "https://example.gov/bids/erie-tree"
        owego_url = "https://example.gov/bids/owego-demolition"

        def fake_fetch(url, binary=False):
            if url == src["url"]:
                return listing, "text/html", url
            if url == pdf_url:
                return b"%PDF-synthetic", "application/pdf", url
            if url == html_url:
                return (b"<h1>Tree removal bid</h1><p>Status: Withdrawn</p>"
                        b"<p>Bid due November 13, 2026</p>"), "text/html", url
            if url == owego_url:
                return (b"<h1>Owego demolition bid</h1>"
                        b"<p>Building demolition and site restoration</p>"), "text/html", url
            raise AssertionError("Unexpected URL: " + url)

        with patch.object(scan, "fetch", side_effect=fake_fetch), patch.object(
            scan, "pdf_text",
            return_value=("Erie tree and stump removal bid due November 13, 2026. "
                          "Status: Rescinded")
        ):
            leads, status = scan.scan_direct(src)
        self.assertEqual(leads, [])
        self.assertIn("direct fetched", status)

    def test_erie_expired_and_owego_demolition_are_not_promoted(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid. Bids due October 28, 2026.",
            today=self.TODAY))
        self.assertFalse(scan.eligible(
            "Owego demolition rebid. Building demolition and site restoration.",
            today=self.TODAY))


if __name__ == "__main__":
    unittest.main()
