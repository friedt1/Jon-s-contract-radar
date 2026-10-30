"""Synthetic adjacent site-prep classification tests; never seed live bids."""
import datetime as dt
import unittest
from unittest.mock import patch

import opportunity_triage
import scan


class RelatedSitePrepTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(
            scan, "NOW", dt.datetime(2026, 10, 30, 16, tzinfo=dt.timezone.utc)
        )
        clock.start()
        self.addCleanup(clock.stop)

    def test_explicit_sitework_is_separate_and_lower_priority(self):
        for scope in (
            "Site preparation RFP",
            "Site prep contract",
            "Site grading bid",
            "Earthwork and grading proposal",
            "Grading and grubbing contract",
        ):
            with self.subTest(scope=scope):
                self.assertEqual(scan.category(scope), "Related site prep")
                self.assertTrue(scan.eligible(scope, today=dt.date(2026, 10, 30)))
        self.assertEqual(
            opportunity_triage.review_assessment({
                "category": "Related site prep",
                "lead_type": "direct detail candidate",
                "deadline": "",
            }, today=dt.date(2026, 10, 30))["review_priority"],
            "low",
        )

    def test_tree_and_land_clearing_still_take_precedence(self):
        self.assertEqual(
            scan.category("Tree removal and site preparation RFP"), "Tree removal"
        )
        self.assertEqual(
            scan.category("Land clearing and site grading bid"), "Land clearing"
        )

    def test_demolition_only_owego_and_unrelated_terms_excluded(self):
        for scope in (
            "Owego demolition and site restoration rebid",
            "Owego building demolition and site preparation bid",
            "Website preparation services RFP",
            "Parking lot resurfacing bid",
        ):
            with self.subTest(scope=scope):
                self.assertIsNone(scan.category(scope))
                self.assertFalse(scan.eligible(scope, today=dt.date(2026, 10, 30)))

    def test_expired_and_out_of_region_site_prep_are_not_candidates(self):
        self.assertFalse(scan.eligible(
            "Site preparation bid due 10/28/2026",
            today=dt.date(2026, 10, 30),
        ))
        self.assertFalse(scan.eligible(
            "Harrisburg site preparation RFP", source="PA procurement opportunities",
            today=dt.date(2026, 10, 30),
        ))
        self.assertTrue(scan.eligible(
            "Bradford County site preparation RFP", source="PA procurement opportunities",
            today=dt.date(2026, 10, 30),
        ))

    def test_related_site_prep_is_unverified_not_a_live_bid(self):
        found = {}
        scan.add_lead(
            found, "Synthetic County",
            "Site preparation RFP",
            "https://county.example/bid/999",
            "Site grading; deadline not confirmed",
            kind="direct detail candidate",
        )
        self.assertEqual(len(found), 1)
        item = next(iter(found.values()))
        self.assertEqual(item["category"], "Related site prep")
        self.assertEqual(item["status"], "unverified")
        self.assertNotEqual(item.get("open_status"), "verified_open")


if __name__ == "__main__":
    unittest.main()
