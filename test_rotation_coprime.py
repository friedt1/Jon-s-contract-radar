"""Ensure tied detail and PDF candidates cannot starve under bounded scans."""
import datetime as dt
import unittest

from detail_rotation import rotate_boundary_ties, rotate_selected_boundary_ties


class CoprimeRotationTests(unittest.TestCase):
    def test_all_candidates_eventually_reach_budget_when_gcd_is_not_one(self):
        # The old hour * window offset with 6 candidates and budget 2
        # visited only 4 of 6 candidates, regardless of scan duration.
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
