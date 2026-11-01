"""Synthetic offline rotation tests; never seed or claim a live contract."""
import datetime as dt
import unittest
from unittest.mock import patch

import civicplus_bids
import detail_rotation
import scan


UTC = dt.timezone.utc
BASE = "https://county.example/bids"


class RotationUnitTests(unittest.TestCase):
    def test_higher_ranked_candidates_stay_ahead_of_rotating_ties(self):
        ordered = list(range(15))
        priority = lambda number: 10 if number < 4 else 0
        start = dt.datetime(2026, 10, 31, 10, tzinfo=UTC)
        seen = set()
        for hour in range(7):
            result = detail_rotation.rotate_boundary_ties(
                ordered, 6, start + dt.timedelta(hours=hour), priority)
            self.assertEqual(result[:4], ordered[:4])
            self.assertEqual(set(result), set(ordered))
            seen.update(result[:6])
        self.assertEqual(seen, set(ordered))

    def test_all_equal_priority_slots_rotate_without_pinning_first(self):
        ordered = list(range(12))
        now = dt.datetime(2026, 11, 1, 10, tzinfo=UTC)
        batches = [
            detail_rotation.rotate_boundary_ties(
                ordered, 3, now + dt.timedelta(hours=hour), lambda _: 0)[:3]
            for hour in range(4)
        ]
        self.assertEqual(set().union(*(set(batch) for batch in batches)),
                         set(ordered))
        self.assertEqual(len({batch[0] for batch in batches}), 4)

    def test_expired_lower_priority_never_preempts_future_notices(self):
        ordered = [("future", n) for n in range(6)] + [("expired", 99)]
        priority = lambda item: item[0]
        for hour in range(4):
            self.assertEqual(detail_rotation.rotate_boundary_ties(
                ordered, 6, dt.datetime(2026, 10, 31, 10 + hour,
                                        tzinfo=UTC), priority), ordered)

    def test_same_hour_is_deterministic_and_naive_clock_keeps_order(self):
        ordered = list(range(20))
        priority = lambda _: 0
        now = dt.datetime(2026, 10, 31, 10, 20, tzinfo=UTC)
        self.assertEqual(
            detail_rotation.rotate_boundary_ties(ordered, 8, now, priority),
            detail_rotation.rotate_boundary_ties(
                ordered, 8, now + dt.timedelta(minutes=15), priority))
        self.assertEqual(detail_rotation.rotate_boundary_ties(
            ordered, 8, now.replace(tzinfo=None), priority), ordered)
        self.assertEqual(detail_rotation.rotate_boundary_ties(
            ordered, 20, now, priority), ordered)

    def test_all_tied_deferred_candidates_eventually_examined(self):
        ordered = list(range(11))
        start = dt.datetime(2026, 10, 31, 10, tzinfo=UTC)
        seen = set()
        for hour in range(5):
            scheduled = detail_rotation.rotate_boundary_ties(
                ordered, 6, start + dt.timedelta(hours=hour), lambda _: 0)
            seen.update(scheduled[:6])
        self.assertEqual(seen, set(ordered))


class ScannerRotationTests(unittest.TestCase):
    def test_generic_individual_detail_budget_explores_tied_links(self):
        listing = "".join(
            f'<a href="/bid/{number}">Tree removal bid</a>'
            for number in range(11))
        start = dt.datetime(2026, 10, 31, 10, tzinfo=UTC)
        all_fetched = set()
        first_batch = None
        for hour in range(5):
            fetched = []

            def fake_fetch(url, binary=False):
                if url == BASE:
                    return listing, "text/html", url
                fetched.append(url)
                body = "<h1>Unrelated road paving project</h1>"
                return (body.encode() if binary else body, "text/html", url)

            with (patch.object(scan, "NOW", start + dt.timedelta(hours=hour)),
                  patch.object(scan, "MAX_DETAIL", 6),
                  patch.object(scan, "fetch", side_effect=fake_fetch)):
                leads, status = scan.scan_direct({
                    "name": "Synthetic County", "url": BASE, "mode": "direct_page"
                })
            self.assertEqual(leads, [])
            self.assertEqual(len(fetched), 6)
            self.assertIn("5 detail candidates deferred at request budget", status)
            if first_batch is None:
                first_batch = fetched
            elif hour == 1:
                self.assertNotEqual(fetched, first_batch)
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
        first_batch = None
        for hour in range(5):
            fetched = []

            def fake_fetch(url, binary=False):
                fetched.append(url)
                detail = ("<h1>Bid Title: Tree removal</h1>"
                          "<p>Status: Open</p>"
                          "<p>Description: Tree removal on county property.</p>"
                          "<p>Closing Date/Time: 11/19/2026 2:00 PM</p>")
                return detail.encode(), "text/html", url

            with (patch.object(scan, "NOW", start + dt.timedelta(hours=hour)),
                  patch.object(civicplus_bids, "MAX_DETAILS", 6),
                  patch.object(civicplus_bids, "listing_records", return_value=rows),
                  patch.object(scan, "fetch", side_effect=fake_fetch)):
                leads, status = scan.scan_civicplus(
                    {"name": "Synthetic County", "url": entry},
                    [(scan.parse_html("<p>Public bids</p>"), entry)], [])
            self.assertEqual(len(fetched), 6)
            self.assertIn("5 individual bid records deferred at detail budget", status)
            self.assertTrue(all(lead["status"] == "unverified" for lead in leads))
            if first_batch is None:
                first_batch = fetched
            elif hour == 1:
                self.assertNotEqual(fetched, first_batch)
            all_fetched.update(fetched)
        self.assertEqual(len(all_fetched), 11)

    def test_nested_bid_index_rotates_tied_individual_notices(self):
        index = "https://county.example/procurement"
        listing = '<a href="/procurement">Current bids</a>'
        nested = "".join(
            f'<a href="/bid/{number}">Tree removal bid</a>'
            for number in range(11))
        start = dt.datetime(2026, 10, 31, 10, tzinfo=UTC)
        all_fetched = set()
        first_batch = None
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

            with (patch.object(scan, "NOW", start + dt.timedelta(hours=hour)),
                  patch.object(scan, "MAX_DETAIL", 6),
                  patch.object(scan, "fetch", side_effect=fake_fetch)):
                leads, status = scan.scan_direct({
                    "name": "Synthetic County", "url": BASE, "mode": "direct_page"
                })
            self.assertEqual(leads, [])
            self.assertEqual(len(fetched), 5)
            self.assertIn("6 details checked", status)
            if first_batch is None:
                first_batch = fetched
            elif hour == 1:
                self.assertNotEqual(fetched, first_batch)
            all_fetched.update(fetched)
        self.assertEqual(len(all_fetched), 11)


if __name__ == "__main__":
    unittest.main()
