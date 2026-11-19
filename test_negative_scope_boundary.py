"""Regression boundaries: excluded tree work is not an actionable tree bid.

These are synthetic notices, not current procurement listings. In particular,
the Owego demolition example must never be manually published as a tree bid.
"""
import unittest

from scan import category, eligible, positive_scope_text


class ExcludedScopeRegressionTests(unittest.TestCase):
    def test_demolition_with_tree_work_by_others_is_not_tree_bid(self):
        notice = ("Bid: Owego building demolition. Tree removal by others. "
                  "Site grading by owner. No tree trimming.")
        self.assertIsNone(category(notice))
        self.assertFalse(eligible(notice))

    def test_negated_tree_and_stump_scope_is_not_positive_work(self):
        notice = "RFP: demolition; no tree removal or stump grinding."
        self.assertIsNone(category(notice))
        self.assertFalse(eligible(notice))

    def test_positive_brush_clearing_survives_separate_exclusion(self):
        notice = ("RFP: brush clearing is required; tree removal by owner.")
        self.assertEqual(category(notice), "Vegetation management")

    def test_site_prep_is_separately_labeled_not_tree_service(self):
        notice = "Bid: site grading and grubbing required."
        self.assertEqual(category(notice), "Related site prep")

    def test_tree_protection_is_not_tree_removal(self):
        notice = "Bid: demolition with tree protection and landscape buffers."
        self.assertIsNone(category(notice))

    def test_explicit_exclusion_is_stripped_before_matching(self):
        text = positive_scope_text("No tree removal. Brush clearing required.")
        self.assertNotIn("tree removal", text)
        self.assertIn("brush clearing", text)


if __name__ == "__main__":
    unittest.main()
