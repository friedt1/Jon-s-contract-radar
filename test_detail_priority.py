"""Offline regressions: navigation must not starve real individual bid links.

All URLs and notices here are synthetic fixtures, never live opportunities.
"""
import unittest
from unittest.mock import patch

import scan


SOURCE = {"name": "Test County", "url": "https://example.gov/bids", "mode": "direct_page"}
NOTICE = "https://example.gov/bid/321"
INDEX = "https://example.gov/procurement"
NAV = "".join(
    '<a href="/page/%d">View details</a>' % n for n in range(30)
)
DETAIL = "<h1>Tree removal bid due 11/19/2026</h1>"


class DetailPriorityTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(
            scan, "NOW", scan.dt.datetime(2026, 10, 28, 18,
                                         tzinfo=scan.dt.timezone.utc)
        )
        clock.start()
        self.addCleanup(clock.stop)

    def run_fixture(self, listing, pages):
        fetched = []

        def fake(url, binary=False):
            if url == SOURCE["url"]:
                body = listing
            else:
                fetched.append(url)
                body = pages.get(url, "<html>County navigation</html>")
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "fetch", side_effect=fake):
            leads, status = scan.scan_direct(SOURCE)
        return leads, status, fetched

    def test_generic_details_bid_url_beats_thirty_navigation_links(self):
        listing = NAV + '<a href="/bid/321">Details</a>'
        leads, status, fetched = self.run_fixture(listing, {NOTICE: DETAIL})
        self.assertEqual(fetched[0], NOTICE)
        self.assertEqual([lead["url"] for lead in leads], [NOTICE])
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("18 details checked", status)

    def test_nested_individual_notice_preempts_unrelated_siblings(self):
        listing = '<a href="/procurement">Current bids</a>' + NAV
        nested = ('<table><tr><td>General roadside maintenance</td>'
                  '<td><a href="/bid/321">Details</a></td></tr></table>')
        leads, status, fetched = self.run_fixture(
            listing, {INDEX: nested, NOTICE: DETAIL}
        )
        self.assertEqual(fetched[:2], [INDEX, NOTICE])
        self.assertEqual([lead["url"] for lead in leads], [NOTICE])
        self.assertIn("nested listing pages excluded as notices", status)

    def test_nested_notice_failure_never_promotes_listing(self):
        listing = '<a href="/procurement">Current bids</a>' + NAV
        nested = ('<table><tr><td>Tree removal bid</td>'
                  '<td><a href="/bid/321">Details</a></td></tr></table>')
        leads, _, fetched = self.run_fixture(
            listing, {INDEX: nested, NOTICE: "<html>Purchasing homepage</html>"}
        )
        self.assertEqual(fetched[:2], [INDEX, NOTICE])
        self.assertEqual(leads, [])


if __name__ == "__main__":
    unittest.main()
