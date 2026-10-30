"""Synthetic statewide detail-budget ordering regressions.

These example URLs and bids are test fixtures only, never live contracts.
"""
import datetime as dt
import unittest
from unittest.mock import patch

import scan


BASE = "https://example.gov/bids"
LOCAL = "https://example.gov/bid/elmira-tree"
OUTSIDE = "https://example.gov/bid/outside-0"
OWEGO = "https://example.gov/bid/owego-demolition"


class BroadPortalLocalPriorityTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(scan, "NOW", dt.datetime(
            2026, 10, 28, 18, tzinfo=dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def fixture(self, source, listing):
        requested = []

        def fake_fetch(url, binary=False):
            requested.append(url)
            if url == BASE:
                body = listing
            elif url == LOCAL:
                body = "<h1>Elmira tree removal bid due 11/19/2026</h1>"
            elif url == OWEGO:
                body = "<h1>Owego demolition bid due 11/19/2026</h1>"
            else:
                body = "<h1>Albany tree removal bid due 11/19/2026</h1>"
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(source)
        return leads, status, requested

    def test_local_tree_notice_beats_statewide_links_at_request_cap(self):
        # A local bid appears after 18 out-of-area tree bid links.
        listing = "".join(
            '<a href="/bid/outside-%d">Tree removal bid in Albany</a>' % n
            for n in range(scan.MAX_DETAIL)
        ) + '<a href="/bid/elmira-tree">Elmira tree removal bid</a>'
        source = {"name": "PA procurement opportunities", "url": BASE}
        leads, status, requested = self.fixture(source, listing)

        self.assertEqual(requested[1], LOCAL)
        self.assertIn(LOCAL, requested)
        self.assertEqual([item["url"] for item in leads], [LOCAL])
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("driving time from Elmira unverified", leads[0]["location"])
        self.assertIn("1 detail candidates deferred at request budget", status)

    def test_local_demolition_never_becomes_tree_lead(self):
        listing = ('<a href="/bid/owego-demolition">Owego demolition bid</a>'
                   '<a href="/bid/elmira-tree">Elmira tree removal bid</a>')
        source = {"name": "PA DGS construction bids", "url": BASE}
        leads, _, requested = self.fixture(source, listing)
        self.assertIn(OWEGO, requested)
        self.assertEqual([item["url"] for item in leads], [LOCAL])

    def test_non_statewide_source_keeps_existing_ordering(self):
        listing = "".join(
            '<a href="/bid/outside-%d">Tree removal bid in Albany</a>' % n
            for n in range(scan.MAX_DETAIL)
        ) + '<a href="/bid/elmira-tree">Elmira tree removal bid</a>'
        source = {"name": "Test County", "url": BASE}
        leads, status, requested = self.fixture(source, listing)
        self.assertEqual(requested[1], OUTSIDE)
        self.assertNotIn(LOCAL, requested)
        self.assertEqual(leads, [])
        self.assertIn("1 detail candidates deferred at request budget", status)


if __name__ == "__main__":
    unittest.main()
