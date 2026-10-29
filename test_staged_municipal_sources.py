"""Offline regression tests for newly staged official sources and stale CivicPlus notices."""
import datetime as dt
import json
import pathlib
import unittest

import probe_staged_sources as staged
import civicplus_bids


NOW = dt.datetime(2026, 10, 29, 6, 45, tzinfo=dt.timezone.utc)


def source(name, url):
    return {"name": name, "mode": "discovery_pending",
            "candidate_official_url": url, "activation_gate": "Review terms"}


class MunicipalStagingTests(unittest.TestCase):
    def test_official_sources_are_staged_not_activated(self):
        records = json.loads((pathlib.Path(__file__).parent / "sources.json").read_text())
        expected = {
            "Village of Horseheads": "https://www.villageofhorseheads.gov/Bids.aspx",
            "City of Cortland": "https://www.cortlandny.gov/Bids.aspx",
            "City of Corning": "https://cityofcorningny.gov/index.asp?SEC=07CB95A9-0A8E-4D9D-B22C-7B8C866B36E5",
            "Town of Corning": "https://townofcorningny.gov/",
        }
        self.assertEqual(len(records), 102)
        for name, url in expected.items():
            with self.subTest(name=name):
                entry = next(row for row in records if row["name"] == name)
                self.assertEqual(entry["mode"], "discovery_pending")
                self.assertEqual(entry["candidate_official_url"], url)
                self.assertFalse(entry.get("verified_url"))
                self.assertFalse(entry.get("url"))
        self.assertTrue({"Village of Horseheads", "City of Cortland"} <= civicplus_bids.SOURCES)

    def test_binghamton_official_granicus_index_is_staged_only(self):
        # Official city purchasing index has individual /Home/Components/RFP/RFP/
        # records, but this project has not established permission or a parser.
        records = json.loads((pathlib.Path(__file__).parent / "sources.json").read_text())
        row = next(x for x in records if x["name"] == "City of Binghamton")
        self.assertEqual(row["mode"], "discovery_pending")
        self.assertFalse(row["verified_url"])
        self.assertEqual(row["url"], "")
        self.assertEqual(row["candidate_official_url"],
                         "https://www.binghamton-ny.gov/government/departments/purchasing/bids-rfps")
        self.assertIn("Granicus adapter", row["activation_gate"])
        self.assertIn("status", row["activation_gate"])
        # The new Granicus probe may read individual notices, but never
        # promotes a staged source or treats a stale Open label as live.
        def fetch(url, binary=False):
            if not binary:
                return ('<tr><td><a href="/Home/Components/RFP/RFP/416/90">'
                        'Sale for 312 Main Street</a></td><td>07/23/2026</td>'
                        '<td>08/12/2026 10:30 AM</td><td>Open</td></tr>'), "text/html", url
            return (b'<h1>Sale for 312 Main Street</h1><p>Start Date: 07/23/2026</p>'
                    b'<p>Close Date: 08/12/2026 10:30 AM</p>'), "text/html", url
        probe = staged.probe(row, fetch=fetch, now=NOW)
        self.assertEqual(probe["state"], "notice_format_confirmed_terms_review_required")
        self.assertEqual(probe["individual_records_discovered"], 1)
        self.assertEqual(probe["sample_notice_temporal_evidence"], "deadline_passed")
        self.assertFalse(probe["direct_monitoring_activated"])

    def test_explicit_no_open_bids_not_confused_with_broken_parser(self):
        entry = "https://www.cortlandny.gov/Bids.aspx"
        def fetch(url, binary=False):
            return "<h1>Bids & RFPs</h1><p>There are no open bid postings at this time.</p>", "text/html", url
        row = staged.probe(source("City of Cortland", entry), fetch=fetch, now=NOW)
        self.assertEqual(row["state"], "listing_reachable_no_open_bids")
        self.assertEqual(row["individual_records_discovered"], 0)
        self.assertFalse(row["direct_monitoring_activated"])

    def test_stale_open_label_is_explicitly_flagged(self):
        entry = "https://www.villageofhorseheads.gov/Bids.aspx"
        def fetch(url, binary=False):
            if url == entry:
                return ('<article><a href="/Bids.aspx?bidID=8">Emergency tree removal</a>'
                        '<p>Status: Open Closes: 10/13/2026 11:59 PM</p></article>'), "text/html", url
            return (b'<h1>Bid Title: Emergency tree removal</h1><p>Bid Number: H-8</p>'
                    b'<p>Description: Tree removal.</p>'
                    b'<p>Closing Date/Time: 10/13/2026 11:59 PM</p><p>Status: Open</p>'), "text/html", url
        row = staged.probe(source("Village of Horseheads", entry), fetch=fetch, now=NOW)
        self.assertEqual(row["state"], "notice_format_confirmed_terms_review_required")
        self.assertEqual(row["sample_notice_status"], "open")
        self.assertEqual(row["sample_notice_deadline"], "2026-10-13")
        self.assertEqual(row["sample_notice_temporal_evidence"], "deadline_passed")
        self.assertFalse(row["direct_monitoring_activated"])

    def test_future_deadline_is_still_unverified_not_open_contract(self):
        entry = "https://www.villageofhorseheads.gov/Bids.aspx"
        def fetch(url, binary=False):
            if url == entry:
                return '<article><a href="/Bids.aspx?bidID=8">Tree work</a></article>', "text/html", url
            return (b'<h1>Bid Title: Tree work</h1><p>Bid Number: H-8</p>'
                    b'<p>Description: Tree removal.</p>'
                    b'<p>Closing Date/Time: 11/30/2026 10:00 AM</p><p>Status: Open</p>'), "text/html", url
        row = staged.probe(source("Village of Horseheads", entry), fetch=fetch, now=NOW)
        self.assertEqual(row["sample_notice_temporal_evidence"], "deadline_not_passed_unverified")
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertNotIn("opportunities", row)

    def test_generic_listing_does_not_become_no_open_bids(self):
        entry = "https://www.cortlandny.gov/Bids.aspx"
        row = staged.probe(source("City of Cortland", entry),
                           fetch=lambda url, binary=False: ("<h1>Bid Postings</h1>", "text/html", url),
                           now=NOW)
        self.assertEqual(row["state"], "listing_reachable_no_bidid_records")


if __name__ == "__main__":
    unittest.main()
