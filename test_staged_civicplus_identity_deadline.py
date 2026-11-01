"""Offline staged CivicPlus integrity tests; never seed production opportunities."""
import datetime as dt
import unittest

import probe_staged_sources as staged
import scan


ENTRY = "https://county.example/Bids.aspx"
NOTICE = ENTRY + "?bidID=55"
SOURCE = {
    "name": "Cortland County",
    "mode": "discovery_pending",
    "candidate_official_url": ENTRY,
    "activation_gate": "Publisher terms and notice extraction review",
}
NOW = dt.datetime(2026, 11, 1, 14, tzinfo=dt.timezone.utc)
LISTING = (
    '<article><p>Tree and stump removal</p><p>Bid No. RFB-101</p>'
    '<p>Status: Closes: Open 11/20/2026 2:00 PM</p>'
    '<a href="/Bids.aspx?bidID=55">Read on</a></article>'
)


def notice(number="RFB-101", closing="11/20/2026 2:00 PM"):
    return (
        f"<p>Bid Number: {number}</p><p>Bid Title: Roadside tree removal</p>"
        "<p>Status: Open</p><p>Description: Remove hazardous trees.</p>"
        f"<p>Closing Date/Time: {closing}</p>"
    )


def probe(detail):
    calls = []

    def fetch(url, binary=False):
        calls.append(url)
        if url == ENTRY:
            return LISTING, "text/html", url
        if url == NOTICE:
            return detail.encode(), "text/html", url
        raise AssertionError("unexpected request: " + url)

    row = staged.probe(SOURCE, fetch=fetch, now=NOW)
    return row, calls


class StagedCivicPlusIdentityAndDeadlineTests(unittest.TestCase):
    def test_wrong_bid_number_under_same_bidid_is_not_valid_sample(self):
        for number in ("RFB-202", "rfb-202"):
            with self.subTest(number=number):
                row, calls = probe(notice(number))
                self.assertEqual(calls, [ENTRY, NOTICE])
                self.assertEqual(row["state"], "individual_notice_bid_number_mismatch")
                self.assertFalse(row["individual_notice_retrieved"])
                self.assertEqual(row["individual_samples_attempted"], 1)
                self.assertEqual(
                    row["individual_sample_failures"][0]["state"],
                    "individual_notice_bid_number_mismatch",
                )
                self.assertFalse(row["direct_monitoring_activated"])
                self.assertNotIn("sample_notice_deadline", row)

    def test_matching_bid_number_is_diagnostic_not_activation(self):
        row, calls = probe(notice("rfb-101"))
        self.assertEqual(calls, [ENTRY, NOTICE])
        self.assertEqual(row["state"], "notice_format_confirmed_terms_review_required")
        self.assertTrue(row["individual_notice_retrieved"])
        self.assertEqual(row["sample_notice_deadline"], "2026-11-20")
        self.assertEqual(row["sample_notice_deadline_source"], "individual_notice")
        self.assertFalse(row["sample_notice_unparseable_detail_closing"])
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertNotIn("opportunities", row)

    def test_malformed_detail_cutoff_does_not_reuse_listing_date(self):
        row, _ = probe(notice(closing="Pending amendment"))
        self.assertTrue(row["individual_notice_retrieved"])
        self.assertEqual(row["sample_notice_deadline"], "")
        self.assertEqual(row["sample_notice_deadline_time"], "")
        self.assertEqual(row["sample_notice_deadline_source"], "unknown")
        self.assertTrue(row["sample_notice_unparseable_detail_closing"])
        self.assertEqual(row["sample_notice_temporal_evidence"], "deadline_unknown")
        self.assertFalse(row["direct_monitoring_activated"])

    def test_absent_detail_cutoff_can_use_listing_with_unverified_source(self):
        row, _ = probe(notice().replace(
            "<p>Closing Date/Time: 11/20/2026 2:00 PM</p>", ""
        ))
        self.assertEqual(row["sample_notice_deadline"], "2026-11-20")
        self.assertEqual(row["sample_notice_deadline_source"], "listing")
        self.assertFalse(row["sample_notice_unparseable_detail_closing"])
        self.assertEqual(row["sample_notice_temporal_evidence"],
                         "deadline_not_passed_unverified")

    def test_expired_individual_cutoff_overrides_future_listing(self):
        row, _ = probe(notice(closing="10/22/2026 2:00 PM"))
        self.assertEqual(row["sample_notice_deadline"], "2026-10-22")
        self.assertEqual(row["sample_notice_deadline_source"], "individual_notice")
        self.assertTrue(row["sample_notice_deadline_conflict"])
        self.assertEqual(row["sample_notice_temporal_evidence"],
                         "conflicting_deadlines_unverified")
        self.assertFalse(row["direct_monitoring_activated"])

    def test_historical_erie_and_unrelated_owego_are_not_live(self):
        self.assertFalse(scan.eligible(
            "Erie PA tree and stump removal due October 29, 2026",
            "PennBid platform", today=dt.date(2026, 11, 1),
        ))
        self.assertIsNone(scan.category(
            "Owego building demolition and site restoration rebid"
        ))


if __name__ == "__main__":
    unittest.main()
