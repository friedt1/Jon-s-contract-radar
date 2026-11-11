"""Keep distant city hints out of the approximately two-hour primary lane.

These tests use synthetic text only. They do not assert a road-network travel
time, a live bid, or successful extraction from an external procurement site.
"""
import unittest

from scan import local_evidence
from opportunity_triage import review_assessment


class PrimaryAreaScopeRegression(unittest.TestCase):
    def test_known_nearby_place_is_discovery_hint_only(self):
        for place in ("Elmira", "Owego", "Corning", "Wellsboro"):
            with self.subTest(place=place):
                self.assertTrue(local_evidence(place + " tree trimming bid"))

    def test_distant_city_is_not_primary_locality_hint(self):
        for place in ("Buffalo", "Niagara Falls", "Rochester"):
            with self.subTest(place=place):
                self.assertFalse(local_evidence(place + " stump removal bid"))

    def test_location_text_does_not_verify_driving_time(self):
        result = review_assessment({
            "category": "Tree removal",
            "lead_type": "individual county bid candidate",
            "location": "Owego, NY",
        })
        self.assertIn("worksite text present; two-hour drive unverified",
                      result["review_factors"])
        self.assertIn("not an open-contract or travel verification",
                      result["review_disclaimer"])


if __name__ == "__main__":
    unittest.main()
