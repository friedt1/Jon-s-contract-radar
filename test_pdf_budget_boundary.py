"""Offline PDF request-budget regression tests; never represent live opportunities."""
import datetime as dt
import unittest

import detail_rotation


UTC = dt.timezone.utc


class PdfBoundaryRotationTests(unittest.TestCase):
    def test_pdf_budget_rotates_even_when_general_detail_budget_does_not(self):
        # Eight PDF-shaped links fit under the general 18-detail budget,
        # but only five PDFs can be attempted per scan.
        ordered = [f"html-{n}" for n in range(3)] + [f"pdf-{n}" for n in range(8)]
        selected = lambda item: item.startswith("pdf-")
        start = dt.datetime(2026, 11, 7, 3, tzinfo=UTC)
        seen = set()
        for hour in range(8):
            now = start + dt.timedelta(hours=hour)
            result = detail_rotation.rotate_selected_boundary_ties(
                ordered, 5, now, lambda _: 0, selected)
            self.assertEqual(result[:3], ordered[:3])
            self.assertEqual(set(result), set(ordered))
            self.assertEqual(len(result), len(ordered))
            seen.update(item for item in result if selected(item) and
                        sum(selected(other) for other in result[:result.index(item)]) < 5)
        self.assertEqual(seen, {f"pdf-{n}" for n in range(8)})

    def test_pdf_priority_boundary_does_not_promote_expired_notices(self):
        # Priority order is supplied by the caller; expired notices must
        # never displace higher-priority PDFs at the cutoff.
        ordered = [("future", n) for n in range(7)] + [("expired", n) for n in range(3)]
        selected = lambda _: True
        priority = lambda item: 1 if item[0] == "future" else 0
        start = dt.datetime(2026, 11, 7, 3, tzinfo=UTC)
        for hour in range(7):
            result = detail_rotation.rotate_selected_boundary_ties(
                ordered, 5, start + dt.timedelta(hours=hour), priority, selected)
            self.assertTrue(all(item[0] == "future" for item in result[:5]))
            self.assertEqual(set(result), set(ordered))

    def test_no_pdf_budget_exhaustion_preserves_original_order(self):
        ordered = ["html-1", "pdf-1", "html-2", "pdf-2"]
        now = dt.datetime(2026, 11, 7, 3, tzinfo=UTC)
        self.assertEqual(detail_rotation.rotate_selected_boundary_ties(
            ordered, 5, now, lambda _: 0,
            lambda item: item.startswith("pdf-")), ordered)


if __name__ == "__main__":
    unittest.main()
