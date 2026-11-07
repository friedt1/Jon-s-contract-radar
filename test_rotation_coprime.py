"""Ensure tied detail and PDF candidates cannot starve under bounded scans."""
import datetime as dt
import unittest

from detail_rotation import rotate_boundary_ties, rotate_selected_boundary_ties


class BoundaryWindowCoverageTests(unittest.TestCase):
    def test_all_candidates_reach_budget_with_non_coprime_window(self):
        # Six tied candidates with two slots must all be visited, even
        # though gcd(window, group_size) is two.
        items = list(range(6))
        observed = set()
        for hour in range(6):
            now = dt.datetime(2026, 11, 7, hour, tzinfo=dt.timezone.utc)
            observed.update(rotate_boundary_ties(items, 2, now, lambda _: 0)[:2])
        self.assertEqual(observed, set(items))

    def test_pdf_rotation_covers_every_pdf_and_preserves_html_positions(self):
        items = [('html', 'a')] + [('pdf', i) for i in range(6)] + [('html', 'b')]
        seen = set()
        for hour in range(6):
            now = dt.datetime(2026, 11, 7, hour, tzinfo=dt.timezone.utc)
            result = rotate_selected_boundary_ties(
                items, 2, now, lambda _: 0, lambda x: x[0] == 'pdf')
            self.assertEqual(result[0], ('html', 'a'))
            self.assertEqual(result[-1], ('html', 'b'))
            seen.update(x[1] for x in result if x[0] == 'pdf' and result.index(x) <= 2)
        self.assertEqual(seen, set(range(6)))


if __name__ == '__main__':
    unittest.main()
