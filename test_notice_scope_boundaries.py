"""Offline safety regressions: exclusion text is not positive contract scope.

These are synthetic examples, not live solicitations or seeded opportunities.
"""
import unittest
from scan import category, positive_scope_text


class ScopeBoundaryTests(unittest.TestCase):
    def test_demolition_tree_work_by_others_is_not_tree_contract(self):
        self.assertIsNone(category(
            "Owego demolition solicitation; tree removal by others."
        ))

    def test_excluded_tree_and_stump_group_is_not_tree_contract(self):
        self.assertIsNone(category(
            "Demolition bid: no tree removal or stump grinding."
        ))

    def test_positive_brush_clearing_survives_tree_exclusion(self):
        self.assertEqual(
            category("Tree removal by owner; contractor shall perform brush clearing."),
            "Vegetation management",
        )

    def test_explicit_site_grading_is_separately_classified(self):
        self.assertEqual(
            category("Demolition and site grading procurement; tree removal by others."),
            "Related site prep",
        )

    def test_normalization_does_not_reintroduce_excluded_tree_scope(self):
        self.assertNotIn(
            "tree removal",
            positive_scope_text("Demolition: tree removal by owner."),
        )


if __name__ == "__main__":
    unittest.main()
