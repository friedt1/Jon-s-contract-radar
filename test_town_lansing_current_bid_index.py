"""Current official Town of Lansing bid-index staging (synthetic notices only).

A newly discovered official link does not authorize crawling or prove an open
contract. These tests never modify the published opportunity feed.
"""
import datetime as dt
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import audit_source_coverage
import civicplus_bids
import probe_staged_sources as staged
import scan
import source_health


URL = "https://www.lansingtownny.gov/Bids.aspx"
NOW = dt.datetime(2026, 11, 2, 13, tzinfo=dt.timezone.utc)


class TownLansingCurrentBidIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads(
            (Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
        cls.source = next(row for row in cls.sources
                          if row["name"] == "Town of Lansing")

    def test_new_official_civicplus_url_remains_staged(self):
        row = self.source
        self.assertEqual(len(self.sources), 102)
        self.assertEqual(len({item["name"] for item in self.sources}), 102)
        self.assertEqual(row["candidate_official_url"], URL)
        self.assertNotEqual(row["candidate_official_url"],
                            "https://www.lansingtownny.gov/rfps")
        self.assertEqual(row["mode"], "discovery_pending")
        self.assertEqual(row["url"], "")
        self.assertIs(row["verified_url"], False)
        self.assertIn("Town of Lansing", civicplus_bids.SOURCES)
        self.assertIn("publisher terms", row["activation_gate"])
        self.assertIn("robots", row["activation_gate"])
        self.assertFalse(row.get("provider_access_required", False))
        self.assertEqual(source_health.classify(row, "")["direct_state"],
                         "staged_official_url")
        audit = audit_source_coverage.audit(self.sources)
        self.assertEqual(audit["total"], 102)
        self.assertEqual(audit["direct_configured"], 18)
        self.assertEqual(audit["not_directly_monitored"], 84)
        self.assertEqual(audit["official_urls_staged"], 84)
        self.assertFalse(next(x for x in audit["sources"]
                              if x["source"] == row["name"])["direct_fetch_target"])

    def test_staged_source_is_never_sent_to_direct_scanner(self):
        with (patch.object(scan, "scan_direct",
                           side_effect=AssertionError("staged source activated")) as direct,
              patch.object(scan, "scan_news", return_value=[])):
            _, status, leads = scan.run(self.source)
        direct.assert_not_called()
        self.assertEqual(leads, [])
        self.assertNotIn("direct fetched", status)

    def test_empty_listing_is_not_a_live_opportunity(self):
        html = ("<h1>Bids & RFPs</h1>"
                "<p>There are no open bid postings at this time.</p>")
        result = staged.probe(
            self.source, fetch=lambda url, binary=False: (html, "text/html", url),
            now=NOW)
        self.assertEqual(result["state"], "listing_reachable_no_open_bids")
        self.assertFalse(result["individual_notice_retrieved"])
        self.assertFalse(result["direct_monitoring_activated"])
        self.assertNotIn("opportunities", result)

    def test_synthetic_notice_shape_is_not_permission_or_verified_open(self):
        listing = ('<article><a href="/Bids.aspx?bidID=81">'
                   'Tree removal bid</a><p>Status: Open</p>'
                   '<p>Closes: 11/30/2026 2:00 PM</p></article>')
        detail = ('<h1>Bid Title: Tree removal</h1>'
                  '<p>Bid Number: 81</p><p>Description: Tree removal.</p>'
                  '<p>Closing Date/Time: 11/30/2026 2:00 PM</p>'
                  '<p>Status: Open</p>')
        def fake_fetch(url, binary=False):
            if url == URL:
                return listing, "text/html", url
            self.assertEqual(url, URL + "?bidID=81")
            return detail.encode(), "text/html", url
        result = staged.probe(self.source, fetch=fake_fetch, now=NOW)
        self.assertEqual(result["state"],
                         "notice_format_confirmed_terms_review_required")
        self.assertTrue(result["individual_notice_retrieved"])
        self.assertEqual(result["sample_notice_deadline"], "2026-11-30")
        self.assertFalse(result["direct_monitoring_activated"])
        self.assertNotIn("opportunities", result)

    def test_historical_erie_and_unrelated_owego_are_excluded(self):
        today = dt.date(2026, 11, 2)
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            "PennBid platform", today=today))
        self.assertFalse(scan.eligible(
            "Owego building demolition and site restoration bid due "
            "November 13, 2026", "Tioga County NY", today=today))


if __name__ == "__main__":
    unittest.main()
