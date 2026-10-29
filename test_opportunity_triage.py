"""Synthetic triage fixtures; no real or open contract is asserted."""
import datetime as dt
import unittest

from opportunity_triage import review_assessment


class OpportunityTriageTests(unittest.TestCase):
    TODAY = dt.date(2026, 10, 29)

    def test_direct_notice_ranks_above_news_without_verifying_either(self):
        direct = {
            "category": "Tree removal", "lead_type": "individual county bid candidate",
            "deadline": "2026-11-12", "deadline_time": "2:00 PM",
            "scope": "Removal of hazardous trees", "open_status": "detail_listed_open",
            "location": "Town road in Chemung County", "status": "unverified",
            "travel_verified": False,
        }
        news = {
            "category": "Tree removal", "lead_type": "indirect news candidate",
            "deadline": "", "location": "NY/PA target area — driving time unverified",
            "status": "unverified",
        }
        a = review_assessment(direct, self.TODAY)
        b = review_assessment(news, self.TODAY)
        self.assertGreater(a["review_score"], b["review_score"])
        self.assertEqual(a["review_priority"], "high")
        self.assertEqual(b["review_priority"], "low")
        self.assertIn("not an open-contract", a["review_disclaimer"])
        self.assertEqual(direct["status"], "unverified")
        self.assertFalse(direct["travel_verified"])

    def test_deadline_unknown_never_infers_date_or_open_status(self):
        lead = {"category": "Storm cleanup", "lead_type": "direct detail candidate",
                "deadline": "", "status": "unverified"}
        result = review_assessment(lead, self.TODAY)
        self.assertIn("submission deadline unknown", result["review_factors"])
        self.assertEqual(lead["deadline"], "")
        self.assertEqual(lead["status"], "unverified")

    def test_expired_candidate_is_not_prioritized(self):
        lead = {"category": "Tree removal", "lead_type": "individual county bid candidate",
                "deadline": "2026-10-28", "open_status": "detail_listed_open"}
        result = review_assessment(lead, self.TODAY)
        self.assertEqual(result["review_priority"], "expired_check")
        self.assertEqual(result["review_score"], 0)

    def test_erie_and_owego_regression_examples_not_promoted(self):
        erie = {"category": "Tree removal", "lead_type": "indirect news candidate",
                "deadline": "2026-10-29", "location": "Erie, PA"}
        owego = {"category": None, "lead_type": "indirect news candidate",
                 "deadline": "2026-11-13", "location": "Owego, NY"}
        self.assertNotEqual(review_assessment(erie, self.TODAY)["review_priority"], "high")
        self.assertNotEqual(review_assessment(owego, self.TODAY)["review_priority"], "high")

    def test_invalid_dates_and_unknown_categories_are_safe(self):
        lead = {"category": "Unrelated", "lead_type": "unknown", "deadline": "not-a-date"}
        self.assertEqual(review_assessment(lead, self.TODAY)["review_score"], 0)


if __name__ == "__main__":
    unittest.main()
