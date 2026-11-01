"""Offline CivicPlus closing-field variants; no production bid records are created."""
import datetime as dt
import unittest
from unittest.mock import patch

import civicplus_bids as civic
import probe_staged_sources as staged
import scan


BASE = "https://county.example/Bids.aspx"
DETAIL_URL = BASE + "?bidID=91"
LISTING = (
    '<article><a href="/Bids.aspx?bidID=91">Tree removal bid</a>'
    '<p>Bid No. RFB-91</p><p>Status: Closes: Open 11/20/2026 2:00 PM</p></article>'
)
DETAIL = (
    "<p>Bid Number: RFB-91</p><p>Bid Title: Tree removal bid</p>"
    "<p>Status: Open</p><p>Description: Remove hazardous trees.</p>"
    "<p>Closing Date/Time: Sept. 10th, 2026 at 14:30</p>"
)
NOW = dt.datetime(2026, 11, 1, 16, tzinfo=dt.timezone.utc)


def fake_fetch(url, binary=False):
    if url == BASE:
        return LISTING, "text/html", url
    if url == DETAIL_URL:
        return DETAIL.encode(), "text/html", url
    raise AssertionError("Unexpected fetch: " + url)


class CivicPlusClosingVariantsTests(unittest.TestCase):
    def test_abbreviated_month_and_ordinal_listing_and_detail_fields(self):
        for month in ("Sep", "Sep.", "Sept", "Sept.", "September",
                      "Oct.", "Nov.", "Dec."):
            with self.subTest(month=month):
                expected_month = ("09" if month.startswith("Sep") else
                                  {"Oct.": "10", "Nov.": "11", "Dec.": "12"}[month])
                expected = (f"2026-{expected_month}-10", "2:30 PM")
                self.assertEqual(
                    civic.closing_of(
                        f"Status: Closes: Open {month} 10th, 2026 at 14:30"
                    ), expected
                )
                self.assertEqual(
                    civic.detail_closing_of(
                        f"Closing Date/Time: {month} 10th, 2026 at 14:30"
                    ), expected
                )

    def test_unambiguous_24_hour_clocks_and_no_inferred_clock(self):
        for raw, expected in (
            ("00:05", "12:05 AM"), ("09:05", "9:05 AM"),
            ("14:30", "2:30 PM"), ("23:59 hours", "11:59 PM"),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(
                    civic.detail_closing_of(
                        f"Closing Date/Time: November 3, 2026 at {raw}"
                    ), ("2026-11-03", expected)
                )
        self.assertEqual(
            civic.detail_closing_of("Closing Date/Time: November 3, 2026 at 2:30"),
            ("2026-11-03", ""),
        )
        self.assertEqual(
            civic.detail_closing_of("Publication Date/Time: Sept. 10, 2026 at 14:30"),
            ("", ""),
        )

    def test_24_hour_same_day_cutoff_is_enforced_in_eastern_time(self):
        before = dt.datetime(2026, 11, 3, 19, 29, tzinfo=dt.timezone.utc)
        after = dt.datetime(2026, 11, 3, 19, 30, tzinfo=dt.timezone.utc)
        self.assertFalse(civic.closing_passed("2026-11-03", "2:30 PM", before))
        self.assertTrue(civic.closing_passed("2026-11-03", "2:30 PM", after))

    def test_expired_individual_notice_overrides_future_listing(self):
        source = {"name": "Chemung County bids", "url": BASE, "mode": "direct_page"}
        with patch.object(scan, "NOW", NOW), patch.object(
            scan, "fetch", side_effect=fake_fetch
        ):
            leads, diagnostic = scan.scan_direct(source)
        self.assertEqual(leads, [])
        self.assertIn("1 expired", diagnostic)

    def test_staged_notice_records_expired_conflict_without_activation(self):
        source = {
            "name": "Cortland County",
            "mode": "discovery_pending",
            "candidate_official_url": BASE,
            "activation_gate": "Publisher permission and notice verification",
        }
        row = staged.probe(source, fetch=fake_fetch, now=NOW)
        self.assertTrue(row["individual_notice_retrieved"])
        self.assertEqual(row["sample_notice_deadline"], "2026-09-10")
        self.assertEqual(row["sample_notice_deadline_time"], "2:30 PM")
        self.assertTrue(row["sample_notice_deadline_conflict"])
        self.assertEqual(row["sample_notice_temporal_evidence"],
                         "conflicting_deadlines_unverified")
        self.assertFalse(row["direct_monitoring_activated"])

    def test_historical_erie_and_unrelated_owego_are_not_live(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            "PennBid platform", today=dt.date(2026, 11, 1)))
        self.assertIsNone(scan.category(
            "Owego demolition and site restoration project rebid"))


if __name__ == "__main__":
    unittest.main()
