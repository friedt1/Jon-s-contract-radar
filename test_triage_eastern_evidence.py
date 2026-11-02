"""Offline review-score regressions; all notices below are synthetic, not live bids."""
import datetime as dt
import unittest

from opportunity_triage import review_assessment


UTC = dt.timezone.utc
BASE = {
    "category": "Tree removal",
    "lead_type": "individual county bid candidate",
    "status": "unverified",
}


class EasternTriageEvidenceTests(unittest.TestCase):
    def test_aware_scan_timestamp_controls_default_eastern_today(self):
        # UTC is Dec 31; Eastern is still Dec 31. Yesterday's NY bid
        # must not get a future-deadline score from the machine's clock.
        now = dt.datetime(2030, 12, 31, 23, 30, tzinfo=UTC)
        row = dict(BASE, deadline="2030-12-30", deadline_time="9:00 PM")
        result = review_assessment(row, now=now)
        self.assertEqual(result["review_priority"], "expired_check")
        self.assertEqual(result["review_score"], 0)
        self.assertEqual(row["status"], "unverified")

    def test_utc_next_day_is_still_eastern_same_day(self):
        now = dt.datetime(2031, 1, 1, 1, 15, tzinfo=UTC)  # Dec 31, 8:15 PM ET
        row = dict(BASE, deadline="2030-12-31", deadline_time="9:00 PM")
        result = review_assessment(row, now=now)
        self.assertNotEqual(result["review_priority"], "expired_check")
        self.assertIn("submission date stated; amendments still unverified",
                      result["review_factors"])

    def test_only_parseable_eastern_clocks_receive_time_bonus(self):
        today = dt.date(2030, 12, 30)
        base = dict(BASE, deadline="2030-12-31")
        without = review_assessment(base, today=today)
        valid = review_assessment(dict(base, deadline_time="9:00 AM",
                                       deadline_timezone="ET"), today=today)
        invalid = review_assessment(dict(base, deadline_time="time to be announced"),
                                    today=today)
        other_zone = review_assessment(dict(base, deadline_time="9:00 AM",
                                            deadline_timezone="Pacific"),
                                       today=today)
        self.assertEqual(valid["review_score"], without["review_score"] + 4)
        self.assertEqual(invalid["review_score"], without["review_score"])
        self.assertEqual(other_zone["review_score"], without["review_score"])
        self.assertIn("submission time ambiguous or non-Eastern; verify with issuer",
                      invalid["review_factors"])

    def test_historical_erie_and_unrelated_owego_not_promoted(self):
        now = dt.datetime(2026, 11, 2, 13, tzinfo=UTC)
        erie = dict(BASE, title="Erie tree and stump removal",
                    deadline="2026-10-28", deadline_time="9:00 AM")
        owego = dict(BASE, category=None, title="Owego demolition",
                     deadline="2026-11-13")
        self.assertEqual(review_assessment(erie, now=now)["review_priority"],
                         "expired_check")
        self.assertEqual(review_assessment(owego, now=now)["review_priority"],
                         "excluded")


if __name__ == "__main__":
    unittest.main()
