"""Synthetic bid-deadline fixtures only; never assert a live solicitation."""
import datetime as dt
import unittest

from submission_deadlines import eastern_deadline_timezone
from regional_rank import classify, build
from opportunity_triage import review_assessment


class EasternDeadlineEvidenceTests(unittest.TestCase):
    TODAY = dt.date(2026, 10, 29)
    AFTER_NINE_EDT = dt.datetime(2026, 10, 29, 14, tzinfo=dt.timezone.utc)

    def test_explicit_eastern_labels_and_existing_local_assumption(self):
        for label in (None, "", "ET", "EST", "EDT", "Eastern",
                      "Eastern Time", "Eastern Standard Time",
                      "Eastern Daylight Time", "US/Eastern",
                      "America/New_York",
                      "America/New_York (NY/PA agency-local assumption)"):
            with self.subTest(label=label):
                self.assertTrue(eastern_deadline_timezone(label))

    def test_negated_or_non_eastern_labels_never_trigger_eastern_cutoff(self):
        for label in ("Pacific", "America/Los_Angeles", "Central",
                      "Not Eastern", "not America/New_York",
                      "Eastern? not confirmed", "UTC", 42, False):
            with self.subTest(label=label):
                self.assertFalse(eastern_deadline_timezone(label))

    def test_regional_erie_style_notice_expiry_requires_eastern_evidence(self):
        # Erie-style tree/stump fixture is historical, not a sourced live bid.
        notice = {
            "title": "Tree and stump removal",
            "url": "https://county.example/bids/erie-regression",
            "deadline": "2026-10-29",
            "deadline_time": "9:00 AM",
        }
        self.assertIsNone(classify(
            dict(notice, deadline_timezone="EDT"),
            today=self.TODAY, now=self.AFTER_NINE_EDT))
        for label in ("Pacific", "Not Eastern", "UTC"):
            with self.subTest(label=label):
                candidate = classify(dict(notice, deadline_timezone=label),
                                     today=self.TODAY, now=self.AFTER_NINE_EDT)
                self.assertIsNotNone(candidate)
                self.assertEqual(candidate["status"], "review required")
                self.assertEqual(candidate["deadline_status"], "stated_unverified")

    def test_local_triage_uses_same_conservative_timezone_gate(self):
        lead = {
            "category": "Tree removal",
            "lead_type": "individual county bid candidate",
            "deadline": "2026-10-29",
            "deadline_time": "9:00 AM",
            "status": "unverified",
        }
        self.assertEqual(
            review_assessment(dict(lead, deadline_timezone="America/New_York"),
                              self.TODAY, now=self.AFTER_NINE_EDT)["review_priority"],
            "expired_check")
        for label in ("America/Los_Angeles", "Not Eastern", "UTC"):
            with self.subTest(label=label):
                assessment = review_assessment(
                    dict(lead, deadline_timezone=label),
                    self.TODAY, now=self.AFTER_NINE_EDT)
                self.assertNotEqual(assessment["review_priority"], "expired_check")

    def test_unrelated_owego_demolition_remains_out_of_tree_feed(self):
        owego = {"title": "67 Central Avenue Demolition Rebid",
                 "summary": "Building demolition and site restoration",
                 "url": "https://county.example/bids/owego-regression",
                 "deadline": "2026-11-13"}
        self.assertEqual(build([owego], today=self.TODAY,
                               now=self.AFTER_NINE_EDT)["opportunities"], [])


if __name__ == "__main__":
    unittest.main()
