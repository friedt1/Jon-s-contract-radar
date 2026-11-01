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

    def test_same_day_cutoff_is_excluded_after_eastern_deadline(self):
        # Erie tree/stump is a historical regression, NOT a verified lead.
        erie = {"category": "Tree removal", "lead_type": "individual county bid candidate",
                "deadline": "2026-10-29", "deadline_time": "9:00 AM",
                "open_status": "listing_open", "status": "unverified"}
        after = dt.datetime(2026, 10, 29, 14, 37, tzinfo=dt.timezone.utc)
        before = dt.datetime(2026, 10, 29, 12, 37, tzinfo=dt.timezone.utc)
        self.assertEqual(review_assessment(erie, self.TODAY, now=after)["review_priority"],
                         "expired_check")
        self.assertNotEqual(review_assessment(erie, self.TODAY, now=before)["review_priority"],
                            "expired_check")
        self.assertEqual(erie["status"], "unverified")

    def test_unknown_or_malformed_same_day_time_is_not_invented(self):
        after = dt.datetime(2026, 10, 29, 14, 37, tzinfo=dt.timezone.utc)
        lead = {"category": "Tree removal", "lead_type": "direct detail candidate",
                "deadline": "2026-10-29", "status": "unverified"}
        self.assertNotEqual(review_assessment(lead, self.TODAY, now=after)["review_priority"],
                            "expired_check")
        lead["deadline_time"] = "time to be announced"
        self.assertNotEqual(review_assessment(lead, self.TODAY, now=after)["review_priority"],
                            "expired_check")
        lead["deadline_time"] = "9:00 AM"
        naive = dt.datetime(2026, 10, 29, 14, 37)
        self.assertNotEqual(review_assessment(lead, self.TODAY, now=naive)["review_priority"],
                            "expired_check")

    def test_closed_or_awarded_status_overrides_future_deadline(self):
        lead = {"category": "Tree removal", "lead_type": "individual county bid candidate",
                "deadline": "2026-11-13", "status": "unverified",
                "open_status": "detail_listed_awarded"}
        result = review_assessment(lead, self.TODAY)
        self.assertEqual(result["review_priority"], "expired_check")
        self.assertEqual(result["review_score"], 0)
        self.assertIn("closed/awarded/cancelled", result["review_factors"][-1])

    def test_unrelated_owego_demolition_cannot_be_ranked_by_metadata(self):
        # Historical exclusion regression, not a live or seeded opportunity.
        owego = {
            "category": None, "lead_type": "individual county bid candidate",
            "deadline": "2026-11-19", "deadline_time": "2:00 PM",
            "scope": "Demolition only; tree removal by others",
            "open_status": "detail_listed_open", "location": "Owego, NY",
            "status": "unverified",
        }
        result = review_assessment(owego, self.TODAY)
        self.assertEqual(result["review_score"], 0)
        self.assertEqual(result["review_priority"], "excluded")
        self.assertIn("no supported tree/clearing/site-prep category",
                      result["review_factors"])
        self.assertEqual(owego["status"], "unverified")

    def test_related_site_prep_remains_eligible_for_separate_review(self):
        lead = {
            "category": "Related site prep", "lead_type": "individual county bid candidate",
            "deadline": "2026-11-19", "deadline_time": "2:00 PM",
            "scope": "Site grading and excavation",
            "location": "Chemung County, NY", "status": "unverified",
        }
        result = review_assessment(lead, self.TODAY)
        self.assertGreater(result["review_score"], 0)
        self.assertNotEqual(result["review_priority"], "excluded")
        self.assertEqual(lead["status"], "unverified")

    def test_invalid_dates_and_unknown_categories_are_safe(self):
        lead = {"category": "Unrelated", "lead_type": "unknown", "deadline": "not-a-date"}
        self.assertEqual(review_assessment(lead, self.TODAY)["review_score"], 0)


if __name__ == "__main__":
    unittest.main()
