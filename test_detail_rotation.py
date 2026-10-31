"""Synthetic offline coverage tests: no fixture represents a live contract."""
import datetime as dt
import unittest
from unittest.mock import patch

import civicplus_bids
import detail_rotation
import scan


UTC = dt.timezone.utc
BASE = "https://county.example/bids"


class RotationUnitTests(unittest.TestCase):
    def test_top_priority_is_stable_but_lower_ranked_candidates_advance(self):
        ordered = list(range(20))
        morning = dt.datetime(2026, 10, 31, 10, tzinfo=UTC)
        first = detail_rotation.rotate_exploration_window(ordered, 8, morning)
        second = detail_rotation.rotate_exploration_window(
            ordered, 8, morning + dt.timedelta(hours=1))
        self.assertEqual(first[:6], ordered[:6])
        self.assertEqual(second[:6], ordered[:6])
        self.assertEqual(set(first), set(ordered))
        self.assertEqual(set(second), set(ordered))
        self.assertNotEqual(first[6:8], second[6:8])

    def test_same_hour_is_deterministic_and_naive_clock_does_not_rotate(self):
        ordered = list(range(30))
        now = dt.datetime(2026, 10, 31, 10, 20, tzinfo=UTC)
        self.assertEqual(
            detail_rotation.rotate_exploration_window(ordered, 8, now),
            detail_rotation.rotate_exploration_window(
                ordered, 8, now + dt.timedelta(minutes=15)))
        self.assertEqual(detail_rotation.rotate_exploration_window(
            ordered, 8, now.replace(tzinfo=None)), ordered)
        self.assertEqual(detail_rotation.rotate_exploration_window(
            ordered, 30, now), ordered)

    def test_rotating_slice_eventually_reaches_all_deferred_candidates(self):
        ordered = list(range(11))
        start = dt.datetime(2026, 10, 31, 10, tzinfo=UTC)
        seen = set()
        for hour in range(5):
            scheduled = detail_rotation.rotate_exploration_window(
                ordered, 6, start + dt.timedelta(hours=hour))
            seen.update(scheduled[:6])
        self.assertEqual(seen, set(ordered))


class ScannerRotationTests(unittest.TestCase):
    def test_generic_individual_detail_budget_explores_unfetched_links(self):
        listing = "".join(
            f'<a href="/bid/{number}">Tree removal bid</a>'
            for number in range(11))
        start = dt.datetime(2026, 10, 31, 10, tzinfo=UTC)
        all_fetched = set()
        first_four = None
        for hour in range(5):
            fetched = []

            def fake_fetch(url, binary=False):
                if url == BASE:
                    return listing, "text/html", url
                fetched.append(url)
                body = "<h1>Unrelated road paving project</h1>"
                return (body.encode() if binary else body, "text/html", url)

            with patch.object(scan, "NOW", start + dt.timedelta(hours=hour)), \
                 patch.object(scan, "MAX_DETAIL", 6), \
                 patch.object(scan, "fetch", side_effect=fake_fetch):
                leads, status = scan.scan_direct({
                    "name": "Synthetic County", "url": BASE, "mode": "direct_page"
                })
            self.assertEqual(leads, [])
            self.assertEqual(len(fetched), 6)
            self.assertIn("5 detail candidates deferred at request budget", status)
            if first_four is None:
                first_four = fetched[:4]
            self.assertEqual(fetched[:4], first_four)
            all_fetched.update(fetched)
        self.assertEqual(len(all_fetched), 11)

    def test_civicplus_budget_explores_tied_future_notice_cards(self):
        entry = "https://county.example/Bids.aspx"
        rows = [{
            "url": entry + "?bidID=" + str(n),
            "title": "Tree removal bid",
            "description": "Tree removal",
            "open_status": "open",
            "deadline": "2026-11-19",
            "deadline_time": "2:00 PM",
            "bid_number": str(n),
        } for n in range(11)]
        start = dt.datetime(2026, 10, 31, 10, tzinfo=UTC)
        all_fetched = set()
        first_four = None
        for hour in range(5):
            fetched = []

            def fake_fetch(url, binary=False):
                fetched.append(url)
                detail = ("<h1>Bid Title: Tree removal</h1>"
                          "<p>Status: Open</p>"
                          "<p>Description: Tree removal on county property.</p>"
                          "<p>Closing Date/Time: 11/19/2026 2:00 PM</p>")
                return detail.encode(), "text/html", url

            with patch.object(scan, "NOW", start + dt.timedelta(hours=hour)), \
                 patch.object(civicplus_bids, "MAX_DETAILS", 6), \
                 patch.object(civicplus_bids, "listing_records", return_value=rows), \
                 patch.object(scan, "fetch", side_effect=fake_fetch):
                leads, status = scan.scan_civicplus(
                    {"name": "Synthetic County", "url": entry},
                    [(scan.parse_html("<p>Public bids</p>"), entry)], [])
            self.assertEqual(len(fetched), 6)
            self.assertIn("5 individual bid records deferred at detail budget", status)
            self.assertTrue(all(lead["status"] == "unverified" for lead in leads))
            if first_four is None:
                first_four = fetched[:4]
            self.assertEqual(fetched[:4], first_four)
            all_fetched.update(fetched)
        self.assertEqual(len(all_fetched), 11)


    def test_nested_bid_index_rotates_deferred_individual_notices(self):
        index = "https://county.example/procurement"
        listing = '<a href="/procurement">Current bids</a>'
        nested = "".join(
            f'<a href="/bid/{number}">Tree removal bid</a>'
            for number in range(11))
        start = dt.datetime(2026, 10, 31, 10, tzinfo=UTC)
        all_fetched = set()
        stable = None
        for hour in range(5):
            fetched = []

            def fake_fetch(url, binary=False):
                if url == BASE:
                    body = listing
                elif url == index:
                    body = nested
                else:
                    fetched.append(url)
                    body = "<h1>Unrelated historical road paving project</h1>"
                return (body.encode() if binary else body, "text/html", url)

            with patch.object(scan, "NOW", start + dt.timedelta(hours=hour)), \\
                 patch.object(scan, "MAX_DETAIL", 6), \\
                 patch.object(scan, "fetch", side_effect=fake_fetch):
                leads, status = scan.scan_direct({
                    "name": "Synthetic County", "url": BASE, "mode": "direct_page"
                })
            self.assertEqual(leads, [])
            self.assertEqual(len(fetched), 5)
            self.assertIn("6 details checked", status)
            if stable is None:
                stable = fetched[:3]
            self.assertEqual(fetched[:3], stable)
            all_fetched.update(fetched)
        self.assertEqual(len(all_fetched), 11)


if __name__ == "__main__":
    unittest.main()
