"""Publisher status examples are synthetic, not real procurement opportunities."""
import datetime as dt
import unittest

from publisher_status import publisher_closed
from opportunity_triage import review_assessment
from regional_rank import classify


class PublisherStatusTests(unittest.TestCase):
    TODAY = dt.date(2026, 10, 29)

    def test_qualified_publisher_closures_are_detected(self):
        for state in (
            "Closed", "Awarded", "Cancelled", "Canceled", "Withdrawn", "Expired",
            "detail_listed_awarded", "listing_cancelled",
            "Awarded to vendor", "Closed - no longer accepting bids",
            "Cancelled on October 28", "Withdrawn (reissued later)",
        ):
            with self.subTest(state=state):
                self.assertTrue(publisher_closed({"status": "unverified",
                                                  "open_status": state}))

    def test_question_period_and_reopen_labels_are_not_bid_closure(self):
        for state in (
            "Open", "Reopened", "unverified", "Closed for questions",
            "Closed to inquiries", "listing_closed_for_questions",
            "Questions closed; bids remain open", "Not closed",
            "Closed - for questions", "Closed: Q&A", "Closed (questions)",
            "Closed – to inquiries", "listing_closed_-_for_questions",
            "award recommendation pending",
        ):
            with self.subTest(state=state):
                self.assertFalse(publisher_closed({"open_status": state}))
        self.assertFalse(publisher_closed(None))

    def test_local_review_excludes_award_qualifier_even_with_future_deadline(self):
        lead = {
            "category": "Tree removal",
            "lead_type": "individual county bid candidate",
            "deadline": "2026-11-13",
            "status": "unverified",
            "open_status": "Awarded to vendor",
        }
        result = review_assessment(lead, today=self.TODAY)
        self.assertEqual(result["review_priority"], "expired_check")
        self.assertEqual(result["review_score"], 0)
        # Questions closing is not enough evidence that bids have closed.
        lead["open_status"] = "Closed for questions"
        self.assertNotEqual(
            review_assessment(lead, today=self.TODAY)["review_priority"],
            "expired_check")

    def test_regional_erie_style_award_is_not_active_review(self):
        # Historical synthetic tree/stump example; no live bid asserted.
        erie = {"title": "Tree and stump removal",
                "url": "https://county.example/bids/erie-regression",
                "deadline": "2026-11-13", "open_status": "Awarded to vendor"}
        self.assertIsNone(classify(erie, today=self.TODAY))
        erie["open_status"] = "Closed for questions"
        result = classify(erie, today=self.TODAY)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "review required")


    def test_explicit_status_field_labels_cannot_hide_closed_bids(self):
        # Synthetic historical Erie-style tree/stump notices, never live work.
        # A publisher may retain the field name in the extracted status value.
        for state in (
            "Status: Awarded", "Bid Status: Closed",
            "Solicitation Status - Withdrawn", "Notice Status: Cancelled",
            "Current Status: Expired", "Procurement Status: Canceled",
        ):
            with self.subTest(state=state):
                notice = {"title": "Tree and stump removal",
                          "url": "https://county.example/bids?bidID=321",
                          "deadline": "2026-11-20",
                          "status": "unverified", "open_status": state}
                self.assertTrue(publisher_closed(notice))
                self.assertEqual(review_assessment(
                    dict(notice, category="Tree removal",
                         lead_type="individual county bid candidate"),
                    today=self.TODAY)["review_priority"], "expired_check")
                self.assertIsNone(classify(notice, today=self.TODAY))
        # Q&A closure does not close bidding; unrelated Owego demolition
        # remains excluded from the tree-work review feed.
        self.assertFalse(publisher_closed(
            {"open_status": "Bid Status: Closed for questions"}))
        self.assertFalse(publisher_closed(
            {"open_status": "Notice Status: Open"}))
        self.assertIsNone(classify({
            "title": "Owego demolition rebid", "summary": "Building demolition",
            "url": "https://county.example/bids?bidID=322",
            "deadline": "2026-11-20", "open_status": "Notice Status: Open"
        }, today=self.TODAY))

    def test_owego_demolition_still_excluded_as_unrelated(self):
        owego = {"title": "67 Central Avenue Demolition Rebid",
                 "summary": "Building demolition and site restoration",
                 "url": "https://county.example/bids/owego-regression",
                 "deadline": "2026-11-13", "open_status": "Open"}
        self.assertIsNone(classify(owego, today=self.TODAY))


if __name__ == "__main__":
    unittest.main()
