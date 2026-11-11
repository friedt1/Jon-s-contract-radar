"""Offline regression: detail-budget rotation across the Eastern DST fallback.

Synthetic identifiers only; no live opportunities or source status changes.
"""
import datetime as dt
import unittest
from zoneinfo import ZoneInfo

from detail_rotation import rotate_boundary_ties, rotate_selected_boundary_ties


class DstFallbackRotationTests(unittest.TestCase):
    def test_repeated_eastern_one_am_uses_distinct_utc_hours(self):
        eastern = ZoneInfo("America/New_York")
        first = dt.datetime(2026, 11, 1, 1, 15, tzinfo=eastern, fold=0)
        second = dt.datetime(2026, 11, 1, 1, 15, tzinfo=eastern, fold=1)
        self.assertEqual(second.timestamp() - first.timestamp(), 3600)
        ordered = list(range(12))
        priority = lambda _: 0
        first_batch = rotate_boundary_ties(ordered, 3, first, priority)[:3]
        second_batch = rotate_boundary_ties(ordered, 3, second, priority)[:3]
        self.assertTrue(set(first_batch).isdisjoint(second_batch))
        self.assertEqual(
            rotate_boundary_ties(ordered, 3, first, priority),
            rotate_boundary_ties(ordered, 3, first.astimezone(dt.timezone.utc), priority),
        )
        self.assertEqual(
            rotate_boundary_ties(ordered, 3, second, priority),
            rotate_boundary_ties(ordered, 3, second.astimezone(dt.timezone.utc), priority),
        )

    def test_pdf_subset_uses_both_fallback_hours_without_moving_html(self):
        eastern = ZoneInfo("America/New_York")
        ordered = [("html", "index")] + [("pdf", str(i)) for i in range(8)]
        selected = lambda item: item[0] == "pdf"
        priority = lambda _: 0
        batches = []
        for fold in (0, 1):
            clock = dt.datetime(2026, 11, 1, 1, 15, tzinfo=eastern, fold=fold)
            result = rotate_selected_boundary_ties(
                ordered, 2, clock, priority, selected
            )
            self.assertEqual(result[0], ordered[0])
            self.assertEqual(set(result), set(ordered))
            batches.append(set(result[1:3]))
        self.assertTrue(batches[0].isdisjoint(batches[1]))


if __name__ == "__main__":
    unittest.main()
