"""Offline regression guards: historical notices are fixtures, never live leads.

These tests only classify scope text. They do not establish current publisher
status, deadline, geography, eligibility, or a verified open solicitation.
"""
import unittest
import scan


class HistoricalScopeRegressions(unittest.TestCase):
    def test_erie_tree_and_stump_removal_is_tree_work(self):
        self.assertEqual(
            scan.category("Erie County invitation to bid: tree and stump removal"),
            "Tree removal",
        )

    def test_owego_demolition_only_is_not_tree_work_or_site_prep(self):
        self.assertIsNone(
            scan.category("Village of Owego request for bids: building demolition"),
        )

    def test_owego_tree_removal_by_others_is_not_a_tree_lead(self):
        self.assertIsNone(
            scan.category(
                "Village of Owego building demolition; tree removal by others"
            ),
        )

    def test_demolition_with_actual_grading_is_related_only(self):
        self.assertEqual(
            scan.category(
                "Village of Owego building demolition and site grading required"
            ),
            "Related site prep",
        )

    def test_demolition_with_positive_tree_scope_is_tree_work(self):
        self.assertEqual(
            scan.category(
                "Village of Owego demolition; contractor shall perform tree removal"
            ),
            "Tree removal",
        )


if __name__ == "__main__":
    unittest.main()
