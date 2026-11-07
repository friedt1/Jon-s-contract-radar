"""Offline PDF budget rotation invariants; synthetic links are never live bids."""
import datetime as dt
import unittest

from detail_rotation import rotate_selected_boundary_ties

UTC = dt.timezone.utc


class PdfSelectionBoundaryTests(unittest.TestCase):
    def test_pdf_rotation_preserves_html_slots_and_priority_groups(self):
        items = [("html", "index"), ("pdf", "priority"),
                 ("html", "notice"), *[("pdf", str(i)) for i in range(9)],
                 ("html", "footer")]
        selected = lambda item: item[0] == "pdf"
        priority = lambda item: 10 if item[1] == "priority" else 0
        now = dt.datetime(2026, 11, 7, 12, tzinfo=UTC)
        seen = set()
        for hour in range(12):
            result = rotate_selected_boundary_ties(
                items, 3, now + dt.timedelta(hours=hour), priority, selected)
            self.assertEqual(len(result), len(items))
            self.assertEqual(set(result), set(items))
            self.assertEqual(
                [result[i] for i, item in enumerate(items) if not selected(item)],
                [item for item in items if not selected(item)])
            pdfs = [item for item in result if selected(item)]
            self.assertEqual(pdfs[0], ("pdf", "priority"))
            seen.update(pdfs[:3])
        self.assertEqual(seen, set(item for item in items if selected(item)))

    def test_no_pdf_rotation_when_budget_covers_all_selected(self):
        items = [("html", "a"), ("pdf", "one"),
                 ("html", "b"), ("pdf", "two")]
        now = dt.datetime(2026, 11, 7, 12, tzinfo=UTC)
        for budget in (2, 3, 10):
            self.assertEqual(rotate_selected_boundary_ties(
                items, budget, now, lambda _: 0,
                lambda item: item[0] == "pdf"), items)

    def test_naive_clock_and_invalid_budget_do_not_reorder(self):
        items = [("pdf", str(i)) for i in range(8)]
        selected = lambda _: True
        for budget, clock in (
            (0, dt.datetime(2026, 11, 7, tzinfo=UTC)),
            (-1, dt.datetime(2026, 11, 7, tzinfo=UTC)),
            (3, dt.datetime(2026, 11, 7)),
        ):
            self.assertEqual(rotate_selected_boundary_ties(
                items, budget, clock, lambda _: 0, selected), items)


if __name__ == "__main__":
    unittest.main()
