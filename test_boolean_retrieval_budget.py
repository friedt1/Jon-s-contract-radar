"""Boolean configuration flags must never silently become request budgets."""
import datetime as dt
import unittest

from detail_rotation import rotate_boundary_ties, rotate_selected_boundary_ties


class BooleanBudgetTests(unittest.TestCase):
    def test_boolean_is_not_a_request_budget(self):
        items = list(range(10))
        now = dt.datetime(2026, 11, 7, 12, tzinfo=dt.timezone.utc)
        for budget in (True, False):
            with self.subTest(budget=budget):
                self.assertEqual(
                    rotate_boundary_ties(items, budget, now, lambda _: 0), items)
                self.assertEqual(
                    rotate_selected_boundary_ties(
                        items, budget, now, lambda _: 0, lambda _: True), items)


if __name__ == "__main__":
    unittest.main()
