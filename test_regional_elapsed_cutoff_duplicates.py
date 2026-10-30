"""Synthetic regional duplicate-cutoff regression cases; never live bids."""
import datetime as dt
import unittest

from regional_rank import build, classify


class SameDayDuplicateCutoffTests(unittest.TestCase):
    def setUp(self):
        self.today = dt.date(2026, 10, 29)
        self.now = dt.datetime(2026, 10, 29, 15, tzinfo=dt.timezone.utc)
        self.early = {
            "title": "Tree and stump removal",
            "url": "https://county.example/Bids.aspx?bidID=200",
            "deadline": "2026-10-29",
            "deadline_time": "9:00 AM",
        }

    def test_date_only_duplicate_cannot_erase_elapsed_cutoff(self):
        date_only = dict(
            self.early,
            url=self.early["url"] + "&utm_source=mail",
            deadline_time="",
        )
        self.assertIsNone(classify(self.early, today=self.today, now=self.now))
        for notices in ([self.early, date_only], [date_only, self.early]):
            with self.subTest(order=notices[0]["deadline_time"]):
                result = build(notices, today=self.today, now=self.now)["opportunities"]
                self.assertEqual(len(result), 1)
                item = result[0]
                self.assertEqual(item["status"], "review required")
                self.assertEqual(item["deadline_status"], "conflicting_unverified")
                self.assertEqual(item["deadline"], "")
                self.assertEqual(item["deadline_time"], "")
                self.assertEqual(item["deadline_timezone"], "")
                self.assertIn("9:00 am", item["deadline_conflict"])
                self.assertIn("later cutoff not independently confirmed",
                              item["deadline_conflict"])
        self.assertEqual(build([self.early], today=self.today, now=self.now)["opportunities"], [])

    def test_incompatible_timezone_duplicate_does_not_revive_elapsed_cutoff(self):
        other = dict(self.early, deadline_timezone="Pacific")
        result = build([self.early, other], today=self.today, now=self.now)["opportunities"]
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["deadline_status"], "conflicting_unverified")
        self.assertEqual(result[0]["deadline_time"], "")

    def test_other_bid_and_unrelated_demolition_are_independent(self):
        other_bid = dict(self.early, url="https://county.example/Bids.aspx?bidID=201",
                         deadline_time="", deadline="2026-11-20")
        owego = {"title": "Owego demolition rebid",
                 "url": "https://county.example/Bids.aspx?bidID=202",
                 "deadline": "2026-11-13"}
        result = build([self.early, other_bid, owego], today=self.today,
                       now=self.now)["opportunities"]
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["url"], other_bid["url"])
        self.assertEqual(result[0]["deadline"], "2026-11-20")
        self.assertNotIn("deadline_conflict", result[0])


if __name__ == "__main__":
    unittest.main()
