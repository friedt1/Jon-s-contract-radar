"""Offline regressions for timezone-invariant detail scheduling.

Synthetic candidate identifiers only; never publish them as live bids.
"""
import datetime as dt
import unittest

from detail_rotation import rotate_boundary_ties, rotate_selected_boundary_ties


class UtcRotationEquivalenceTests(unittest.TestCase):
    def test_equivalent_timezone_clocks_select_identical_candidates(self):
        ordered = list(range(13))
        utc = dt.datetime(2026, 11, 7, 18, 30, tzinfo=dt.timezone.utc)
        eastern = utc.astimezone(dt.timezone(dt.timedelta(hours=-5)))
        priority = lambda _: 0
        self.assertEqual(
            rotate_boundary_ties(ordered, 4, utc, priority),
            rotate_boundary_ties(ordered, 4, eastern, priority),
        )

    def test_pdf_rotation_preserves_html_slots_and_priority_groups(self):
        ordered = [
            ("html", "important"), ("pdf", "high-1"),
            ("pdf", "high-2"), ("html", "other"),
            ("pdf", "low-1"), ("pdf", "low-2"), ("pdf", "low-3"),
        ]
        priority = lambda item: 1 if item[1].startswith("high") else 0
        selected = lambda item: item[0] == "pdf"
        start = dt.datetime(2026, 11, 7, 18, tzinfo=dt.timezone.utc)
        seen_low = set()
        for hour in range(6):
            result = rotate_selected_boundary_ties(
                ordered, 3, start + dt.timedelta(hours=hour),
                priority, selected,
            )
            self.assertEqual(result[0], ordered[0])
            self.assertEqual(result[3], ordered[3])
            self.assertEqual(result[1:3], ordered[1:3])
            self.assertEqual(set(result), set(ordered))
            seen_low.update(item[1] for item in result[:5]
                            if item[1].startswith("low"))
        self.assertEqual(seen_low, {"low-1"})


if __name__ == "__main__":
    unittest.main()
