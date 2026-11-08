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


    def test_boundary_rotation_never_displaces_higher_priority(self):
        # Two higher-ranked notices are fixed; one of four tied notices
        # receives the remaining request slot. A lower-ranked notice must
        # never consume that slot merely to improve exploration coverage.
        items = [('high', 0), ('high', 1)] + [
            ('tie', i) for i in range(4)] + [('low', 0)]
        ranks = {'high': 0, 'tie': 1, 'low': 2}
        observed = set()
        for hour in range(8):
            now = dt.datetime(2026, 11, 7, hour, tzinfo=dt.timezone.utc)
            result = rotate_boundary_ties(items, 3, now, lambda x: ranks[x[0]])
            self.assertEqual(result[:2], items[:2])
            self.assertEqual(result[-1], ('low', 0))
            self.assertEqual(result[2][0], 'tie')
            observed.add(result[2])
        self.assertEqual(observed, set(items[2:6]))

    def test_pdf_budget_rotates_only_tied_pdfs_below_fixed_priority(self):
        # HTML positions and the highest-ranked PDF must remain stable;
        # the second PDF slot must eventually reach every tied PDF.
        items = [('html', 'first'), ('pdf', 'urgent')] + [
            ('pdf', i) for i in range(4)] + [('html', 'last')]
        def rank(item):
            return 0 if item == ('pdf', 'urgent') else 1
        seen = set()
        for hour in range(8):
            now = dt.datetime(2026, 11, 7, hour, tzinfo=dt.timezone.utc)
            result = rotate_selected_boundary_ties(
                items, 2, now, rank, lambda x: x[0] == 'pdf')
            self.assertEqual(result[0], ('html', 'first'))
            self.assertEqual(result[-1], ('html', 'last'))
            pdfs = [item for item in result if item[0] == 'pdf']
            self.assertEqual(pdfs[0], ('pdf', 'urgent'))
            seen.add(pdfs[1])
        self.assertEqual(seen, set(items[2:6]))


if __name__ == '__main__':
    unittest.main()
