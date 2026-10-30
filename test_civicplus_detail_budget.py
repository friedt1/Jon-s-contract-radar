"""Offline CivicPlus retrieval-budget regressions; no live bid is asserted."""
import datetime as dt
import unittest
from unittest.mock import patch

import civicplus_bids
import scan


ENTRY = "https://county.example/Bids.aspx"
SOURCE = {"name": "Chemung County bids", "url": ENTRY, "mode": "direct_page"}


def record(number, due, title="Tree removal bid"):
    return {
        "url": ENTRY + "?bidID=" + str(number),
        "title": title,
        "description": "",
        "open_status": "open",  # Publisher labels can be stale.
        "deadline": due,
        "deadline_time": "2:00 PM" if due else "",
        "bid_number": str(number),
    }


class CivicPlusBudgetTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(scan, "NOW", dt.datetime(
            2026, 10, 30, 17, 0, tzinfo=dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def run_fixture(self, final_due):
        # The archive contains more than MAX_DETAILS stale "Open" bids.
        # A current, generically titled notice is last in publisher order.
        old = [record(i, "2026-09-01") for i in range(
            1, civicplus_bids.MAX_DETAILS + 1)]
        current = record(999, final_due, "General roadway maintenance")
        rows = old + [current]
        requests = []

        def fetch(url, binary=False):
            requests.append(url)
            if "bidID=999" in url:
                detail = ("<h1>Bid Title: General roadway maintenance</h1>"
                          "<p>Status: Open</p>"
                          "<p>Description: Tree removal and stump grinding "
                          "on a county roadway.</p>"
                          + ("<p>Closing Date/Time: 11/19/2026 2:00 PM</p>"
                             if final_due else ""))
            else:
                detail = ("<p>Bid Title: Historical tree removal</p>"
                          "<p>Status: Open</p>"
                          "<p>Description: Historical tree removal.</p>"
                          "<p>Closing Date/Time: 09/01/2026 2:00 PM</p>")
            return detail.encode(), "text/html", url

        with patch.object(civicplus_bids, "listing_records", return_value=rows):
            with patch.object(scan, "fetch", side_effect=fetch):
                leads, status = scan.scan_civicplus(
                    SOURCE, [(scan.parse_html("<p>Bids</p>"), ENTRY)], [])
        return leads, status, requests

    def test_future_generic_notice_not_starved_by_expired_tree_archive(self):
        leads, status, requests = self.run_fixture("2026-11-19")
        self.assertEqual(len(requests), civicplus_bids.MAX_DETAILS)
        self.assertEqual(requests[0], ENTRY + "?bidID=999")
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["url"], ENTRY + "?bidID=999")
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertFalse(leads[0]["travel_verified"])
        self.assertIn("1 individual bid records deferred at detail budget", status)

    def test_undated_notice_checked_before_stale_open_archive(self):
        leads, status, requests = self.run_fixture("")
        self.assertEqual(requests[0], ENTRY + "?bidID=999")
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("1 individual bid records deferred at detail budget", status)

    def test_budget_is_not_claimed_as_full_individual_notice_coverage(self):
        leads, status, requests = self.run_fixture("2026-11-19")
        self.assertIn("37 individual bid records", status)
        self.assertIn("36 relevant details checked", status)
        self.assertEqual(len(requests), 36)
        self.assertNotIn("verified open", status)


if __name__ == "__main__":
    unittest.main()
