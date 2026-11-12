"""Offline regression coverage for independent PDF request-budget rotation.

Synthetic links only: these are not published solicitations.
"""
import datetime as dt
import unittest

from detail_rotation import rotate_selected_boundary_ties


UTC = dt.timezone.utc


class PdfBudgetSelectionTests(unittest.TestCase):
    def test_pdf_budget_explores_all_tied_links_without_moving_html(self):
        ordered = [
            ("html", "listing"),
            ("pdf", "notice-a"),
            ("html", "detail"),
            ("pdf", "notice-b"),
            ("pdf", "notice-c"),
            ("pdf", "notice-d"),
            ("pdf", "notice-e"),
        ]
        start = dt.datetime(2026, 11, 12, 10, tzinfo=UTC)
        observed = set()
        for hour in range(5):
            result = rotate_selected_boundary_ties(
                ordered, 2, start + dt.timedelta(hours=hour),
                lambda item: 0, lambda item: item[0] == "pdf")
            self.assertEqual(result[0], ordered[0])
            self.assertEqual(result[2], ordered[2])
            self.assertEqual(set(result), set(ordered))
            pdfs = [item[1] for item in result if item[0] == "pdf"]
            observed.update(pdfs[:2])
        self.assertEqual(observed, {
            "notice-a", "notice-b", "notice-c", "notice-d", "notice-e"
        })

    def test_higher_priority_pdf_stays_before_lower_priority_group(self):
        ordered = [
            ("pdf", "future-a", 2),
            ("html", "detail", 0),
            ("pdf", "future-b", 2),
            ("pdf", "future-c", 2),
            ("pdf", "expired", 0),
        ]
        for hour in range(5):
            result = rotate_selected_boundary_ties(
                ordered, 2, dt.datetime(2026, 11, 12, 10 + hour, tzinfo=UTC),
                lambda item: item[2], lambda item: item[0] == "pdf")
            pdfs = [item[1] for item in result if item[0] == "pdf"]
            self.assertEqual(pdfs[-1], "expired")
            self.assertEqual(result[1], ordered[1])

    def test_no_rotation_when_pdf_count_fits_budget(self):
        ordered = [("pdf", "a"), ("html", "b"), ("pdf", "c")]
        result = rotate_selected_boundary_ties(
            ordered, 2, dt.datetime(2026, 11, 12, 10, tzinfo=UTC),
            lambda item: 0, lambda item: item[0] == "pdf")
        self.assertEqual(result, ordered)


if __name__ == "__main__":
    unittest.main()
