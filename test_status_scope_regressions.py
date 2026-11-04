"""Offline regressions: publisher status, scope exclusions, and locality.

These are synthetic examples, never live opportunities or seeded feed data.
"""
import unittest

import scan


class StatusScopeRegressionTests(unittest.TestCase):
    def test_closed_question_period_does_not_close_bid(self):
        self.assertFalse(scan.closed("Tree removal bid; questions closed"))
        self.assertFalse(scan.closed("Tree removal RFP; Q&A closed"))

    def test_explicit_bid_closure_blocks_candidate(self):
        self.assertTrue(scan.closed("Tree removal bid status: awarded"))
        self.assertTrue(scan.closed("Tree removal bids are no longer accepted"))

    def test_demolition_excluded_tree_work_is_not_a_lead(self):
        self.assertIsNone(scan.category(
            "Owego demolition of vacant building; tree removal by owner"))

    def test_positive_scope_survives_separate_exclusion(self):
        self.assertEqual("Vegetation management", scan.category(
            "Brush clearing required; tree removal by others"))

    def test_related_site_prep_has_separate_category(self):
        self.assertEqual("Related site prep", scan.category(
            "Site grading and earthwork invitation to bid"))

    def test_broad_procurement_requires_local_place_evidence(self):
        self.assertFalse(scan.eligible(
            "Tree removal bid for Erie County Pennsylvania",
            source="PA procurement opportunities"))
        self.assertTrue(scan.eligible(
            "Tree removal bid for Chemung County New York",
            source="PA procurement opportunities"))

    def test_historical_erie_scope_is_not_proof_of_open_bid(self):
        self.assertEqual("Tree removal", scan.category(
            "Erie County tree and stump removal bid"))
        self.assertFalse(scan.eligible(
            "Erie County tree and stump removal bid; status: awarded"))


if __name__ == "__main__":
    unittest.main()
