"""Offline CivicPlus receipt-deadline regressions; no live opportunities seeded."""
import datetime as dt
import unittest
from unittest.mock import patch

import civicplus_bids as civic
import scan


BASE = "https://example.gov/Bids.aspx"
DETAIL_URL = BASE + "?bidID=91"
SOURCE = {"name": "Chemung County bids", "url": BASE, "mode": "direct_page"}
LISTING = (
    '<article><a href="/Bids.aspx?bidID=91">Roadside tree removal</a>'
    '<p>Bid No. RFB-91</p><p>Status: Closes: Open 11/20/2026 3:00 PM</p>'
    '</article>'
)
DETAIL = (
    "<p>Bid Number: RFB-91</p><p>Bid Title: Roadside tree removal</p>"
    "<p>Status: Open</p><p>Description: Remove hazardous roadside trees.</p>"
    "<p>Closing Date/Time: 11-02-2026 no later than 2:30 PM</p>"
)


class CivicPlusDashReceiptDeadlineTests(unittest.TestCase):
    def test_listing_and_individual_closing_fields(self):
        for suffix, expected in (
            ("at 2:30 PM", "2:30 PM"),
            ("by 2:30 PM", "2:30 PM"),
            ("until 14:30", "2:30 PM"),
            ("no later than 14:30", "2:30 PM"),
            ("", ""),
        ):
            with self.subTest(suffix=suffix):
                raw = "11-02-2026" + (" " + suffix if suffix else "")
                self.assertEqual(
                    civic.closing_of("Status: Closes: Open " + raw),
                    ("2026-11-02", expected),
                )
                self.assertEqual(
                    civic.detail_closing_of("Closing Date/Time: " + raw),
                    ("2026-11-02", expected),
                )

    def test_invalid_dash_date_and_unlabeled_clock_are_not_guessed(self):
        self.assertEqual(
            civic.detail_closing_of("Closing Date/Time: 02-30-2026 at 2:30 PM"),
            ("", ""),
        )
        self.assertEqual(
            civic.detail_closing_of("Closing Date/Time: 11-02-2026 by 2:30"),
            ("2026-11-02", ""),
        )
        self.assertEqual(
            civic.detail_closing_of(
                "Publication Date/Time: 11-02-2026 2:30 PM"
            ),
            ("", ""),
        )

    def test_expired_individual_notice_overrides_future_listing(self):
        def fetch(url, binary=False):
            self.assertIn(url, (BASE, DETAIL_URL))
            body = DETAIL if binary else LISTING
            return (body.encode() if binary else body, "text/html", url)

        after = dt.datetime(2026, 11, 2, 19, 30, tzinfo=dt.timezone.utc)
        before = dt.datetime(2026, 11, 2, 19, 29, tzinfo=dt.timezone.utc)
        with patch.object(scan, "fetch", side_effect=fetch):
            with patch.object(scan, "NOW", after):
                leads, diagnostic = scan.scan_direct(SOURCE)
                self.assertEqual(leads, [])
                self.assertIn("1 expired", diagnostic)
            with patch.object(scan, "NOW", before):
                leads, _ = scan.scan_direct(SOURCE)
                self.assertEqual(len(leads), 1)
                self.assertEqual(leads[0]["deadline"], "2026-11-02")
                self.assertEqual(leads[0]["deadline_time"], "2:30 PM")
                self.assertEqual(leads[0]["status"], "unverified")

    def test_original_formats_and_regression_exclusions(self):
        self.assertEqual(
            civic.detail_closing_of(
                "Closing Date/Time: 11/02/2026 at 2:30 PM"
            ),
            ("2026-11-02", "2:30 PM"),
        )
        self.assertEqual(
            civic.detail_closing_of(
                "Closing Date/Time: 2026-11-02 at 14:30"
            ),
            ("2026-11-02", "2:30 PM"),
        )
        self.assertFalse(scan.eligible(
            "Erie PA tree and stump removal bids due October 29, 2026",
            "PennBid platform", today=dt.date(2026, 11, 1),
        ))
        self.assertIsNone(scan.category(
            "Owego NY building demolition and site restoration rebid"
        ))


if __name__ == "__main__":
    unittest.main()
