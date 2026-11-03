"""Additional synthetic regression for interleaved PDF request scheduling."""
import datetime as dt
import unittest
from detail_rotation import rotate_selected_boundary_ties

class InterleavedPdfTests(unittest.TestCase):
    def test_interleaved_html_stays_fixed_and_tied_pdfs_rotate(self):
        items = [("html", "listing")] + [
            item for n in range(11)
            for item in (("pdf", n), ("html", "detail-" + str(n)))
        ]
        selected = lambda item: item[0] == "pdf"
        start = dt.datetime(2026, 11, 3, 12, tzinfo=dt.timezone.utc)
        observed = set()
        for hour in range(5):
            result = rotate_selected_boundary_ties(
                items, 5, start + dt.timedelta(hours=hour),
                lambda _: 0, selected)
            self.assertEqual([x for x in result if not selected(x)],
                             [x for x in items if not selected(x)])
            self.assertEqual([i for i, x in enumerate(result) if selected(x)],
                             [i for i, x in enumerate(items) if selected(x)])
            self.assertEqual(set(result), set(items))
            observed.update(x[1] for x in result if selected(x) and
                            sum(selected(y) for y in result[:result.index(x)]) < 5)
        self.assertEqual(observed, set(range(11)))

    def test_priority_boundary_never_rotates_expired_pdf(self):
        items = [("pdf", "current-" + str(n)) for n in range(8)]
        items += [("pdf", "expired")]
        start = dt.datetime(2026, 11, 3, 12, tzinfo=dt.timezone.utc)
        for hour in range(5):
            result = rotate_selected_boundary_ties(
                items, 3, start + dt.timedelta(hours=hour),
                lambda x: 0 if x[1] == "expired" else 1,
                lambda x: x[0] == "pdf")
            self.assertEqual(result[-1], ("pdf", "expired"))
            self.assertEqual(set(result), set(items))

if __name__ == "__main__":
    unittest.main()
