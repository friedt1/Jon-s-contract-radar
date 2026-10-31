"""Offline nested-index regressions; all notices are synthetic, never live bids."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan


BASE = "https://example.gov/bids"
INDEX = "https://example.gov/procurement"
LOCAL = "https://example.gov/bid/elmira-tree"


class NestedPriorityBudgetTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(scan, "NOW", dt.datetime(
            2026, 10, 28, 18, tzinfo=dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def scan_fixture(self, source_name, nested):
        requested = []
        pages = {
            BASE: '<a href="/procurement">Current bids</a>',
            INDEX: nested,
            LOCAL: "<h1>Elmira tree removal bid due 11/19/2026</h1>",
        }

        def fake_fetch(url, binary=False):
            requested.append(url)
            if url not in pages:
                if url.startswith("https://example.gov/bid/outside-"):
                    body = "<h1>Albany road paving bid due 11/19/2026</h1>"
                else:
                    raise AssertionError("Unexpected network request: " + url)
            else:
                body = pages[url]
            return (body.encode() if binary else body, "text/html", url)

        source = {"name": source_name, "url": BASE, "mode": "direct_page"}
        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(source)
        return leads, status, requested

    def test_local_notice_after_thirty_unrelated_nested_bids_gets_first_request(self):
        # Previously only the first MAX_DETAIL nested links were considered,
        # making the last local notice invisible even with unused ranking data.
        unrelated = "".join(
            '<a href="/bid/outside-%d">Albany road paving bid</a>' % i
            for i in range(30)
        )
        nested = unrelated + '<a href="/bid/elmira-tree">Elmira tree removal bid</a>'
        leads, status, requested = self.scan_fixture("PA procurement opportunities", nested)
        self.assertEqual(requested[:3], [BASE, INDEX, LOCAL])
        self.assertEqual([lead["url"] for lead in leads], [LOCAL])
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertLessEqual(len(requested) - 1, scan.MAX_DETAIL)
        self.assertIn("detail candidates deferred at request budget", status)

    def test_undated_local_tree_notice_beats_future_dated_distant_nested_bids(self):
        # Nested statewide indexes can contain hundreds of distant, dated
        # bids. The local undated tree row must not be starved at the cap.
        distant = "".join(
            '<a href="/bid/outside-%d">Albany tree removal bid due November 19, 2026</a>' % i
            for i in range(30)
        )
        nested = distant + '<a href="/bid/elmira-tree">Elmira tree removal bid</a>'
        leads, status, requested = self.scan_fixture("PA procurement opportunities", nested)
        self.assertEqual(requested[:3], [BASE, INDEX, LOCAL])
        self.assertEqual([lead["url"] for lead in leads], [LOCAL])
        self.assertIn("detail candidates deferred at request budget", status)

    def test_relevant_tree_notice_beats_unrelated_nested_bid_ids_on_county_index(self):
        unrelated = "".join(
            '<a href="/bid/outside-%d">Road paving bid</a>' % i
            for i in range(30)
        )
        nested = unrelated + '<a href="/bid/elmira-tree">Elmira tree removal bid</a>'
        leads, _, requested = self.scan_fixture("Test County", nested)
        self.assertEqual(requested[:3], [BASE, INDEX, LOCAL])
        self.assertEqual([lead["url"] for lead in leads], [LOCAL])

    def test_current_notice_beats_expired_nested_tree_notices(self):
        expired = "".join(
            '<a href="/bid/outside-%d">Tree removal bid due 10/01/2024</a>' % i
            for i in range(30)
        )
        nested = expired + '<a href="/bid/elmira-tree">Elmira tree removal bid due 11/19/2026</a>'
        leads, _, requested = self.scan_fixture("Test County", nested)
        self.assertEqual(requested[:3], [BASE, INDEX, LOCAL])
        self.assertEqual([lead["url"] for lead in leads], [LOCAL])


if __name__ == "__main__":
    unittest.main()
