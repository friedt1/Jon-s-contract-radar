"""Offline synthetic fixtures for individual NYSCR and CivicPlus bid boundaries."""
import datetime as dt
import unittest
from unittest.mock import patch

import civicplus_bids
import nyscr_extract
import scan

BASE = "https://example.gov/Bids.aspx"
SOURCE = {"name": "Chemung County bids", "url": BASE, "mode": "direct_page"}


def card(bid, title, state, due):
    return (
        '<article><h3>' + title + '</h3>'
        '<a href="/Bids.aspx?bidID=' + str(bid) + '">Read on</a>'
        '<p>Bid No. RFB-' + str(bid) + '</p>'
        '<p>Status:</p><p>Closes:</p><p>' + state + '</p>'
        '<p>' + due + '</p></article>'
    )


class CivicPlusGenericAnchorFixtures(unittest.TestCase):
    def test_title_before_read_on_is_not_lost(self):
        html = card(501, "Tree removal along county road", "Open", "11/19/2026 1:45 PM")
        rows = civicplus_bids.listing_records(scan.parse_html(html), BASE)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Tree removal along county road")
        self.assertEqual(rows[0]["bid_number"], "RFB-501")
        self.assertEqual(rows[0]["deadline"], "2026-11-19")
        self.assertEqual(rows[0]["open_status"], "open")

    def test_closed_neighbor_does_not_hide_generic_anchor_bid(self):
        html = (card(500, "Tree removal awarded", "Closed", "10/20/2026")
                + card(501, "Tree removal along county road", "Open", "11/19/2026"))
        def fake_fetch(url, binary=False):
            if not binary:
                return html, "text/html", BASE
            body = ("<p>Status: Open</p><p>Description: Tree removal and stump grinding.</p>"
                    "<p>Closing Date/Time: 11/19/2026 1:45 PM</p>")
            return body.encode(), "text/html", url
        clock = dt.datetime(2026, 10, 28, 19, tzinfo=dt.timezone.utc)
        with patch.object(scan, "NOW", clock), patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual([x["url"] for x in leads], [BASE + "?bidID=501"])
        self.assertEqual(leads[0]["title"], "Tree removal along county road")
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertEqual(leads[0]["deadline_source"], "individual notice")
        self.assertIn("1 closed", status)


class NYSCRPreCRNoteFixtures(unittest.TestCase):
    def test_note_after_generic_title_is_part_of_same_notice(self):
        text = """Office supplies contract
CR#:
2140001
Agency:
Example Office
Due date:
11/18/2026
Ad type:
General
Regional highway maintenance
Note:
Includes removal of hazardous trees and storm debris.
CR#:
2140002
Agency:
Example Highway Agency
Due date:
11/20/2026
Location:
Elmira NY
Ad type:
General
Computer services
CR#:
2140003
Agency:
Example Office
Due date:
11/22/2026
"""
        rows = nyscr_extract.extract(text)
        self.assertEqual([r["cr_number"] for r in rows], ["2140002"])
        self.assertEqual(rows[0]["title"], "Regional highway maintenance")
        self.assertIn("hazardous trees", rows[0]["scope"])
        self.assertIn("storm debris", rows[0]["note"])
        self.assertEqual(rows[0]["agency"], "Example Highway Agency")
        self.assertEqual(rows[0]["deadline"], "2026-11-20")
        self.assertEqual(rows[0]["open_status"], "unknown")
        self.assertFalse(nyscr_extract.promotable(rows[0], today=dt.date(2026, 10, 28)))

    def test_first_notice_note_and_subcontracting_banner(self):
        text = """General grounds contract
Note: Scope includes tree pruning and brush removal.
This is a subcontracting opportunity
CR#:
2140004
Agency: Example Agency
Due date: 11/30/2026
"""
        rows = nyscr_extract.extract(text)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "General grounds contract")
        self.assertIn("tree pruning", rows[0]["scope"])
        self.assertNotIn("subcontracting opportunity", rows[0]["note"])

    def test_previous_notice_description_does_not_absorb_next_title_or_note(self):
        text = """Tree trimming contract
CR#:
2140005
Agency: Example Agency
Description:
Tree trimming along state roads.
Due date: 11/20/2026
Ad type:
General
Office procurement
Note:
Printer supplies only.
CR#:
2140006
Agency: Example Office
Due date: 11/21/2026
"""
        rows = nyscr_extract.extract(text)
        self.assertEqual([r["cr_number"] for r in rows], ["2140005"])
        self.assertNotIn("Office procurement", rows[0]["scope"])
        self.assertNotIn("Printer supplies", rows[0]["scope"])


if __name__ == "__main__":
    unittest.main()
