"""Offline regression cases inspired by missed Erie and Owego notices.

All hosts, identifiers, dates, and travel estimates are synthetic. These
fixtures are NOT real procurement opportunities and must never enter feeds.
"""
import datetime as dt
import unittest

import regional_rank


class ErieOwegoGuardTests(unittest.TestCase):
    def setUp(self):
        self.today = dt.date(2026, 11, 9)

    def test_owego_demolition_is_not_tree_service(self):
        notice = {
            "title": "Owego demolition contract",
            "summary": "Demolish an abandoned building and remove masonry rubble.",
            "url": "https://town.example/bids?bidID=9001",
            "deadline": "2026-12-01",
            "drive_hours": 0.5,
            "travel_verified": True,
        }
        self.assertIsNone(regional_rank.classify(notice, today=self.today))
        self.assertEqual(regional_rank.build([notice], today=self.today)["opportunities"], [])

    def test_erie_stump_removal_is_regional_review_not_verified_open(self):
        notice = {
            "title": "Erie tree and stump removal",
            "summary": "Remove hazardous trees and grind stumps.",
            "url": "https://county.example/bids?bidID=9002",
            "deadline": "2026-12-01",
            "drive_hours": 3.5,
            "travel_verified": True,
        }
        item = regional_rank.classify(notice, today=self.today)
        self.assertIsNotNone(item)
        self.assertEqual(item["status"], "review required")
        self.assertEqual(item["deadline_status"], "stated_unverified")
        self.assertGreater(item["drive_hours"], 2)

    def test_expired_erie_example_cannot_reappear(self):
        notice = {
            "title": "Erie tree and stump removal",
            "summary": "Remove hazardous trees and grind stumps.",
            "url": "https://county.example/bids?bidID=9003",
            "deadline": "2026-10-01",
            "drive_hours": 3.5,
            "travel_verified": True,
        }
        self.assertIsNone(regional_rank.classify(notice, today=self.today))
        self.assertEqual(regional_rank.build([notice], today=self.today)["opportunities"], [])


if __name__ == "__main__":
    unittest.main()
