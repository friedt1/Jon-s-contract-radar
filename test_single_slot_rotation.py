"""Offline single-slot detail rotation regressions; no live bids are seeded."""
import datetime as dt
import unittest
from unittest.mock import patch

import detail_rotation
import scan


UTC = dt.timezone.utc
START = dt.datetime(2026, 10, 31, 10, tzinfo=UTC)


class SingleSlotRotationTests(unittest.TestCase):
    def test_one_remaining_slot_eventually_checks_every_tied_notice(self):
        ordered = list(range(7))
        seen = set()
        for hour in range(7):
            rotated = detail_rotation.rotate_boundary_ties(
                ordered, 1, START + dt.timedelta(hours=hour), lambda _: 0)
            self.assertEqual(set(rotated), set(ordered))
            seen.add(rotated[0])
        self.assertEqual(seen, set(ordered))

    def test_one_slot_never_promotes_expired_lower_priority_notice(self):
        ordered = [("future", 1), ("future", 2), ("expired", 3)]
        priority = lambda item: 1 if item[0] == "future" else 0
        seen = set()
        for hour in range(6):
            rotated = detail_rotation.rotate_boundary_ties(
                ordered, 1, START + dt.timedelta(hours=hour), priority)
            seen.add(rotated[0])
            self.assertEqual(rotated[-1], ("expired", 3))
        self.assertEqual(seen, set(ordered[:2]))

    def test_multiple_slots_keep_first_notice_stable(self):
        ordered = list(range(9))
        for hour in range(9):
            rotated = detail_rotation.rotate_boundary_ties(
                ordered, 3, START + dt.timedelta(hours=hour), lambda _: 0)
            self.assertEqual(rotated[0], 0)

    def test_generic_scanner_one_slot_does_not_starve_tied_links(self):
        base = "https://county.example/bids"
        listing = "".join(
            f'<a href="/bid/{number}">Tree removal bid</a>'
            for number in range(4))
        seen = set()
        for hour in range(4):
            fetched = []

            def fake_fetch(url, binary=False):
                if url == base:
                    return listing, "text/html", url
                fetched.append(url)
                body = "<h1>Unrelated historical road paving project</h1>"
                return (body.encode() if binary else body, "text/html", url)

            with (patch.object(scan, "NOW", START + dt.timedelta(hours=hour)),
                  patch.object(scan, "MAX_DETAIL", 1),
                  patch.object(scan, "fetch", side_effect=fake_fetch)):
                leads, status = scan.scan_direct({
                    "name": "Synthetic County", "url": base, "mode": "direct_page"
                })
            self.assertEqual(leads, [])
            self.assertEqual(len(fetched), 1)
            self.assertIn("3 detail candidates deferred", status)
            seen.update(fetched)
        self.assertEqual(len(seen), 4)


if __name__ == "__main__":
    unittest.main()
