"""Offline CivicPlus bidID ambiguity regressions; no production bids seeded.

A duplicated bidID (including differently cased keys) is not a stable
solicitation identity: HTTP servers may select different values. Fail closed
before individual-detail retrieval, including the generic scanner fallback.
"""
import datetime as dt
import unittest
from unittest.mock import patch

import civicplus_bids
import probe_staged_sources
import scan

BASE = "https://county.example/Bids.aspx"
VALID = BASE + "?bidID=42"
NOW = dt.datetime(2026, 11, 1, 15, tzinfo=dt.timezone.utc)
BAD_QUERIES = (
    "bidID=41&bidID=42",
    "bidID=41&BIDID=42",
    "BIDID=41&bidid=41",
    "bidID=41&bidID=",
    "bidID=41&bidID=oops",
    "bidID=%D9%A4",  # Arabic-Indic digit is not an ASCII bid identifier.
    "bidID=41&bidid=41&utm_source=mail",
)


class CivicPlusAmbiguousBidIdTests(unittest.TestCase):
    def test_duplicate_or_non_ascii_bidids_are_not_individual_links(self):
        for query in BAD_QUERIES:
            with self.subTest(query=query):
                href = "/Bids.aspx?" + query
                self.assertEqual(civicplus_bids.individual_url(href, BASE), "")
                self.assertEqual(scan.safe_detail_url(BASE, href), "")
        self.assertEqual(civicplus_bids.individual_url(
            "/Bids.aspx?utm_source=email&bidID=42", BASE), VALID)
        self.assertEqual(scan.safe_detail_url(BASE, "/Bids.aspx?bidID=42"),
                         VALID)

    def test_ambiguous_card_does_not_consume_detail_budget(self):
        html = (
            '<article><p>Tree removal fake duplicate</p>'
            '<a href="/Bids.aspx?bidID=41&amp;bidID=42">Read on</a></article>'
            '<article><p>Tree and stump removal bid</p><p>Bid No. 42</p>'
            '<p>Status: Closes: Open 11/20/2026 2:00 PM</p>'
            '<a href="/Bids.aspx?bidID=42">Read on</a></article>'
        )
        records = civicplus_bids.listing_records(scan.parse_html(html), BASE)
        self.assertEqual([row["url"] for row in records], [VALID])
        calls = []

        def fake_fetch(url, binary=False):
            calls.append(url)
            if url == BASE:
                body = html
            elif url == VALID:
                body = (
                    "<p>Bid Number: 42</p><p>Bid Title: Tree removal</p>"
                    "<p>Status: Open</p>"
                    "<p>Description: Tree removal of hazardous roadside trees.</p>"
                    "<p>Closing Date/Time: 11/20/2026 2:00 PM</p>"
                )
            else:
                raise AssertionError("Ambiguous detail URL fetched: " + url)
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "NOW", NOW), patch.object(
                scan, "fetch", side_effect=fake_fetch):
            leads, diagnostics = scan.scan_direct(
                {"name": "Chemung County bids", "url": BASE, "mode": "direct_page"}
            )
        self.assertEqual(calls, [BASE, VALID])
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("1 individual bid details fetched", diagnostics)

    def test_staged_probe_does_not_sample_ambiguous_bidid(self):
        html = (
            '<article><p>Tree and stump removal</p>'
            '<a href="/Bids.aspx?bidID=41&amp;BIDID=42">Read on</a></article>'
        )
        calls = []

        def fake_fetch(url, binary=False):
            calls.append(url)
            if url != BASE:
                raise AssertionError("Ambiguous staged detail fetched: " + url)
            return html, "text/html", url

        result = probe_staged_sources.probe({
            "name": "Cortland County",
            "mode": "discovery_pending",
            "candidate_official_url": BASE,
            "activation_gate": "Terms and individual notice extraction review",
        }, fetch=fake_fetch, now=NOW)
        self.assertEqual(calls, [BASE])
        self.assertEqual(result["state"], "listing_reachable_no_bidid_records")
        self.assertFalse(result["individual_notice_retrieved"])
        self.assertFalse(result["direct_monitoring_activated"])

    def test_erie_expired_and_owego_demolition_still_excluded(self):
        self.assertFalse(scan.eligible(
            "Erie PA tree and stump removal due October 29, 2026",
            "PennBid platform", today=dt.date(2026, 11, 1)))
        self.assertIsNone(scan.category(
            "Owego building demolition and site restoration rebid"))


if __name__ == "__main__":
    unittest.main()
