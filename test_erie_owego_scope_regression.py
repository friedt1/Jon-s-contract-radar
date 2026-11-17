"""Historical Erie/Owego classification regressions, not live bid records.

These are synthetic scope strings only: no invented IDs, URLs, deadlines,
availability, or source promotions. Run with python -m unittest discover.
"""
import unittest
from scan import category


class ErieOwegoScopeRegression(unittest.TestCase):
    def test_erie_tree_and_stump_removal_is_tree_work(self):
        self.assertEqual(
            category("Erie tree and stump removal bid specifications"),
            "Tree removal",
        )

    def test_owego_demolition_only_is_not_tree_work(self):
        self.assertIsNone(
            category("Owego demolition of an existing building; remove debris"),
        )

    def test_owego_demolition_with_tree_work_by_others_is_not_tree_work(self):
        self.assertIsNone(
            category("Owego building demolition; tree removal by others"),
        )

    def test_owego_demolition_with_real_site_grading_is_separate_category(self):
        self.assertEqual(
            category("Owego demolition and site grading contract"),
            "Related site prep",
        )

    def test_positive_brush_clearing_survives_tree_exclusion(self):
        self.assertEqual(
            category("Owego site project: tree removal by owner; brush clearing required"),
            "Vegetation management",
        )


if __name__ == "__main__":
    unittest.main()
