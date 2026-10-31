"""CivicPlus duplicate bidID cards must not borrow neighboring row evidence.

All HTML and notices here are synthetic. Nothing is inserted into live feeds.
"""
import datetime as dt
import unittest
from unittest.mock import patch

import civicplus_bids
import scan

BASE = "https://county.example/Bids.aspx"
DETAIL = BASE + "?bidID=41"


def card(title, status, due):
    return ('<article><p>' + title + '</p>'
            '<p>Status: Closes: ' + status + ' ' + due + '</p>'
            '<a href="/Bids.aspx?bidID=41">Read on</a></article>')


class CivicPlusPerLinkContextTests(unittest.TestCase):
    def test_first_card_keeps_its_own_status_and_deadline(self):
        html = (card("Tree and stump removal bid", "Open", "11/19/2026 2:00 PM")
                + card("Office supplies bid", "Closed", "10/10/2026 9:00 AM"))
        page = scan.parse_html(html)
        self.assertEqual(len(page.links), 2)
        self.assertNotEqual(page.link_contexts[0], page.link_contexts[1])
        records = civicplus_bids.listing_records(page, BASE)
        self.assertEqual(len(records), 1)
        row = records[0]
        self.assertEqual(row["url"], DETAIL)
        self.assertIn("Tree and stump removal", row["title"])
        self.assertNotIn("Office supplies", row["description"])
        self.assertEqual(row["open_status"], "open")
        self.assertEqual(row["deadline"], "2026-11-19")
        self.assertEqual(row["deadline_time"], "2:00 PM")

    def test_later_tree_card_cannot_reopen_first_closed_office_bid(self):
        html = (card("Office supplies bid", "Closed", "10/10/2026 9:00 AM")
                + card("Tree removal bid", "Open", "11/19/2026 2:00 PM"))
        records = civicplus_bids.listing_records(scan.parse_html(html), BASE)
        self.assertEqual(len(records), 1)
        self.assertIn("Office supplies", records[0]["title"])
        self.assertNotIn("Tree removal", records[0]["description"])
        self.assertEqual(records[0]["open_status"], "closed")
        self.assertEqual(records[0]["deadline"], "2026-10-10")

    def test_scanner_fetches_first_individual_notice_despite_later_closed_card(self):
        listing = (card("Tree and stump removal bid", "Open", "11/19/2026 2:00 PM")
                   + card("Office supplies bid", "Closed", "10/10/2026 9:00 AM"))
        requested = []

        def fake_fetch(url, binary=False):
            requested.append(url)
            body = (("<p>Status: Open</p><p>Description: Tree and stump removal "
                     "along county roads.</p><p>Closing Date/Time: "
                     "11/19/2026 2:00 PM</p>") if binary else listing)
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "NOW", dt.datetime(
                2026, 10, 30, 20, tzinfo=dt.timezone.utc)), \
             patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct({
                "name": "Chemung County bids", "url": BASE, "mode": "direct_page"
            })
        self.assertEqual(requested, [BASE, DETAIL])
        self.assertEqual([lead["url"] for lead in leads], [DETAIL])
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("1 individual bid details fetched", status)


if __name__ == "__main__":
    unittest.main()
