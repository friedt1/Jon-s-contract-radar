"""Regression checks for expanded primary-area discovery hints.

These are text hints, NOT drive-time verification or proof of an open bid.
"""
import unittest

from scan import local_evidence
from opportunity_triage import review_assessment


class FourHourDiscoveryTests(unittest.TestCase):
    def test_buffalo_stump_listing_is_not_filtered_as_out_of_region(self):
        self.assertTrue(local_evidence("City of Buffalo 2027 stump removal bid"))

    def test_extended_area_places_have_discovery_hints(self):
        for city in ("Rochester", "Canandaigua", "Niagara Falls"):
            with self.subTest(city=city):
                self.assertTrue(local_evidence(city + " tree removal solicitation"))

    def test_no_automatic_drive_time_verification(self):
        lead = {
            "category": "Tree removal",
            "lead_type": "individual county bid candidate",
            "location": "Buffalo, NY",
        }
        assessment = review_assessment(lead)
        self.assertIn("worksite text present; four-hour primary drive unverified", assessment["review_factors"])
        self.assertIn("not an open-contract or travel verification", assessment["review_disclaimer"])


if __name__ == "__main__":
    unittest.main()
